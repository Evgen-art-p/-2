#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 2 — ЯЗЫК ВЕДЕНИЯ (одно открытое поле, трейдер сам решает)
# Маркер: TRADER_MANAGE_LANG_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАКОН (Шеф): «никаких граней, пусть сам решает».
# Код НЕ смотрит «есть позиция или нет», чтобы понять, что трейдер
# имел в виду. Трейдер видит ВЕСЬ стол (рынок + своя позиция из камня 1
# + память + состояние) и САМ выбирает действие из полного словаря.
# Одно открытое поле решения. Код берёт действие как есть и проносит
# в табло для Исполнителя (камень 3 — рука исполнит). Решает трейдер.
#
# СЛОВАРЬ ДЕЙСТВИЙ (канон Котина/Вильямса, полный — вход и ведение вместе):
#   ENTER      — войти в рынок (сторона, цена входа, стоп, лот)
#   WAIT       — ничего не делать, ждать (нет входа / нет повода трогать)
#   HOLD       — держать открытую позицию как есть
#   MOVE_STOP  — подтянуть стоп (трейлинг за Аллигатором) → new_stop
#   ADD        — долить к позиции (пирамида на новом фрактале) → add_lot
#   CLOSE      — закрыть позицию своей волей (не по стопу) — весь объём
#
# Трейдер сам складывает стол и выбирает ОДНО. В рынке он или нет —
# его разбор, не флаг кода. Может держать, может долить, может увидеть
# второй вход и сделать ENTER при живой позиции — это его право.
#
# ТРИ КАСАНИЯ × 3 движка (brut/avan/cons), симметрично:
#   1. ПРОМТ (A06/A07/A08/forge/prompt.md) — даём полный язык в ЕГО голосе,
#      добавляем поле action в схему ответа. Старые поля входа сохраняются
#      (ENTER их и заполняет), плюс поля ведения.
#   2. САНИТАР (_sanitize) — проверяет, что action из словаря и числа
#      ведения не битые. НЕ решает за трейдера — только гасит брак.
#   3. ТАБЛО (_save_verdict_to_table) — проносит action + числа ведения
#      в шину для Исполнителя.
#
# ВАЖНО: обратная совместимость. Если трейдер (старый промт ещё в кеше
# или сбой) не дал action — выводим его из verdict: APPROVED→ENTER,
# REJECTED→WAIT. Камень 3 и Исполнитель поймут оба языка.
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_trader_manage_lang.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "TRADER_MANAGE_LANG_V1"
ROOT = Path.cwd()
TRADING = ROOT / "studio" / "modules" / "trading"

# key: (движок, промт, префикс полей сигнала, ключ в табло)
SPECS = {
    "brut": (TRADING / "brut_live.py", TRADING / "A06" / "forge" / "prompt.md", "brut", "brut"),
    "avan": (TRADING / "avan_live.py", TRADING / "A07" / "forge" / "prompt.md", "avan", "avan"),
    "cons": (TRADING / "cons_live.py", TRADING / "A08" / "forge" / "prompt.md", "cons", "cons"),
}

ACTIONS = ("ENTER", "WAIT", "HOLD", "MOVE_STOP", "ADD", "CLOSE")


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not TRADING.exists():
        _fail(f"Не вижу {TRADING}. Запускай из КОРНЯ репы (где папка studio/).")
    for key, (eng, pr, _, _) in SPECS.items():
        if not eng.exists():
            _fail(f"Не найден движок: {eng}")
        if not pr.exists():
            _fail(f"Не найден промт: {pr}")


# ════════════════════════════════════════════════════════════
# КАСАНИЕ В ДВИЖКЕ: санитар ведения + табло ведения
# ════════════════════════════════════════════════════════════

def _engine_helper(pfx: str) -> str:
    """Общий блок для движка: словарь действий + санитар ведения + проброс в табло."""
    return f'''
# ════════════════════════════════════════════════════════════
# КАМЕНЬ 2: ЯЗЫК ВЕДЕНИЯ — одно открытое поле action.  # {MARKER}
# Трейдер сам выбрал действие из словаря, глядя на весь стол.
# Код не решает за него — только проверяет, что не брак, и проносит.
# ════════════════════════════════════════════════════════════

_MANAGE_ACTIONS = ("ENTER", "WAIT", "HOLD", "MOVE_STOP", "ADD", "CLOSE")


def _derive_action(signal: dict) -> str:
    """
    Действие трейдера. Приоритет — явное поле {pfx}_action (новый язык).
    Фоллбэк на старый verdict (обратная совместимость): APPROVED→ENTER,
    REJECTED→WAIT. Так камень 2 не ломает старые ответы.
    """
    a = (signal.get("{pfx}_action") or "").upper().strip()
    if a in _MANAGE_ACTIONS:
        return a
    v = signal.get("{pfx}_verdict")
    if v == "APPROVED":
        return "ENTER"
    return "WAIT"


def _sanitize_manage(signal: dict) -> dict:
    """
    Санитар ведения. Гасит брак в полях ведения — НЕ решает за трейдера.
      MOVE_STOP без new_stop → брак → WAIT (стоп не трогаем)
      ADD без add_lot       → брак → HOLD (держим как есть)
      ENTER чистит {pfx}_verdict под себя (совместимость с камнем 3)
    """
    action = _derive_action(signal)

    if action == "MOVE_STOP":
        ns = signal.get("{pfx}_new_stop")
        if ns is None:
            action = "WAIT"
            signal["{pfx}_reason"] = (signal.get("{pfx}_reason", "") +
                                      " [гашу MOVE_STOP без new_stop]").strip()
    elif action == "ADD":
        al = signal.get("{pfx}_add_lot")
        if al is None:
            action = "HOLD"
            signal["{pfx}_reason"] = (signal.get("{pfx}_reason", "") +
                                      " [гашу ADD без add_lot]").strip()

    signal["{pfx}_action"] = action
    # держим verdict в согласии для старого пути Исполнителя:
    # ENTER → APPROVED, всё остальное (вход не открывается) → как есть
    if action == "ENTER":
        signal["{pfx}_verdict"] = "APPROVED"
    elif action == "WAIT":
        signal["{pfx}_verdict"] = "REJECTED"
    # HOLD/MOVE_STOP/ADD/CLOSE — ведение, к открытию входа не относятся;
    # verdict не навязываем (камень 3 читает action напрямую).
    return signal

'''


def patch_engine(key: str) -> bool:
    eng, _, pfx, _ = SPECS[key]
    src = eng.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {eng.name} (движок) уже пропатчен — пропускаю.")
        return False

    # 1) Вставить helper перед def _save_verdict_to_table
    anchor_fn = "def _save_verdict_to_table(signal: dict):"
    if anchor_fn not in src:
        _fail(f"{eng.name}: не нашёл '_save_verdict_to_table' — структура изменилась.")
    src = src.replace(anchor_fn, _engine_helper(pfx).lstrip("\n") + "\n" + anchor_fn, 1)

    # 2) В табло добавить проброс action + чисел ведения.
    #    Якорь — последняя строка записи lot перед save_trading_state.
    anchor_lot = f't["{pfx}"]["lot"]       = signal.get("{pfx}_lot")\n'
    if anchor_lot not in src:
        _fail(f"{eng.name}: не нашёл строку записи lot в табло — структура изменилась.")
    insert_lot = (
        f't["{pfx}"]["lot"]       = signal.get("{pfx}_lot")\n'
        f'    # КАМЕНЬ 2: язык ведения — действие + числа ведения в шину.  # {MARKER}\n'
        f'    t["{pfx}"]["action"]    = signal.get("{pfx}_action")\n'
        f'    t["{pfx}"]["new_stop"]  = signal.get("{pfx}_new_stop")\n'
        f'    t["{pfx}"]["add_lot"]   = signal.get("{pfx}_add_lot")\n'
    )
    src = src.replace(anchor_lot, insert_lot, 1)

    # 3) Вызвать _sanitize_manage сразу после _sanitize(signal).
    #    У троих вызов вида: signal = _sanitize(signal)
    anchor_san = "signal = _sanitize(signal)"
    if anchor_san not in src:
        _fail(f"{eng.name}: не нашёл вызов _sanitize(signal) — структура изменилась.")
    insert_san = (
        "signal = _sanitize(signal)\n"
        f"    signal = _sanitize_manage(signal)   # {MARKER}: язык ведения"
    )
    src = src.replace(anchor_san, insert_san, 1)

    _backup(eng)
    eng.write_text(src, encoding="utf-8")
    print(f"✅ {eng.name} (движок) пропатчен: словарь + санитар ведения + табло.")
    return True


# ════════════════════════════════════════════════════════════
# КАСАНИЕ В ПРОМТЕ: полный язык в голосе трейдера + поле в схеме
# ════════════════════════════════════════════════════════════

# Текст-врезка в секцию решения (после "## ДАЛЬШЕ — ТЫ ... Поступи.").
# Голос держим нейтральным — у троих свой тон, но смысл один.
PROMPT_BLOCK = '''

---

## ЕСЛИ ТЫ УЖЕ В РЫНКЕ

На столе может лежать **твоя открытая позиция** — её положили перед тобой
как факт: сторона, вход, стоп, сколько баров живёт, как плавает (в R).
Тогда вопрос к тебе другой — не «входить ли», а что делать с тем, что
открыто. Никто не подскажет. Числа на столе — фракталы, Зубы, колокол,
твой плавающий R. Сложи их сам и реши сам.

Ты можешь:
- **держать** — пусть дышит, ты веришь в неё (HOLD);
- **подтянуть стоп** — посчитай новый уровень сам из чисел стола (MOVE_STOP);
- **долить** — добавить объём на новом фрактале по тренду (ADD);
- **закрыть** — выйти всем объёмом своей волей, не дожидаясь стопа (CLOSE).

А можешь увидеть на том же столе **новый вход** при живой позиции — тогда
входи (ENTER), это твоё право. Нет позиции — обычное дело: входишь (ENTER)
или ждёшь (WAIT). Один взгляд, одно решение. Ты сам складываешь весь стол
и выбираешь ОДНО действие. # ''' + MARKER + '''

'''

# Врезка поля action в JSON-схему сигнала (после строки {pfx}_verdict).
def _prompt_schema_insert(pfx: str) -> tuple[str, str]:
    anchor = f'    "{pfx}_verdict": "APPROVED | REJECTED",\n'
    insert = (
        f'    "{pfx}_action": "ENTER | WAIT | HOLD | MOVE_STOP | ADD | CLOSE",\n'
        f'    "{pfx}_verdict": "APPROVED | REJECTED",\n'
    )
    return anchor, insert


# Врезка полей ведения в схему (после строки {pfx}_lot).
def _prompt_fields_insert(pfx: str) -> tuple[str, str]:
    anchor = f'    "{pfx}_lot": null\n'
    insert = (
        f'    "{pfx}_lot": null,\n'
        f'    "{pfx}_new_stop": null,\n'
        f'    "{pfx}_add_lot": null\n'
    )
    return anchor, insert


def patch_prompt(key: str) -> bool:
    _, pr, pfx, _ = SPECS[key]
    src = pr.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {pr.name} ({key} промт) уже пропатчен — пропускаю.")
        return False

    # 1) Врезать языковой блок перед секцией "## КАК ТЫ ОТВЕЧАЕШЬ"
    anchor_sec = "## КАК ТЫ ОТВЕЧАЕШЬ"
    if anchor_sec not in src:
        _fail(f"{pr.name}: не нашёл '## КАК ТЫ ОТВЕЧАЕШЬ' — структура промта изменилась.")
    src = src.replace(anchor_sec, PROMPT_BLOCK.strip("\n") + "\n\n" + anchor_sec, 1)

    # 2) Добавить action в JSON-схему
    a_sch, i_sch = _prompt_schema_insert(pfx)
    if a_sch not in src:
        _fail(f"{pr.name}: не нашёл '{pfx}_verdict' в схеме — структура изменилась.")
    src = src.replace(a_sch, i_sch, 1)

    # 3) Добавить поля ведения (new_stop, add_lot) в схему
    a_fld, i_fld = _prompt_fields_insert(pfx)
    if a_fld not in src:
        _fail(f"{pr.name}: не нашёл '{pfx}_lot' в схеме — структура изменилась.")
    src = src.replace(a_fld, i_fld, 1)

    _backup(pr)
    pr.write_text(src, encoding="utf-8")
    print(f"✅ {pr.name} ({key} промт) пропатчен: язык ведения + поля схемы.")
    return True


def _verify_compiles():
    for key, (eng, _, _, _) in SPECS.items():
        try:
            py_compile.compile(str(eng), doraise=True)
        except py_compile.PyCompileError as e:
            _fail(f"После патча {eng.name} НЕ компилируется:\n{e}")
    print("🧪 Песочница: все три движка компилируются.")


def main():
    print("═" * 62)
    print("  КАМЕНЬ 2: ЯЗЫК ВЕДЕНИЯ (одно поле, трейдер сам решает)  ·", MARKER)
    print("═" * 62)
    _check_root()

    changed = False
    for key in ("brut", "avan", "cons"):
        changed |= patch_engine(key)
        changed |= patch_prompt(key)

    if changed:
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. У троих — полный язык: ENTER/WAIT/HOLD/MOVE_STOP/ADD/CLOSE.")
        print("   Одно открытое поле action. Трейдер сам складывает стол")
        print("   и выбирает ОДНО действие — в рынке он или нет, решает он.")
        print("   Код проносит решение в табло. Рука Исполнителя — камень 3.")
    else:
        print("─" * 62)
        print("ℹ️  Всё уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
