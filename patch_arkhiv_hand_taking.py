#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# patch_arkhiv_hand_taking.py
# РУКА БЕРУЩАЯ: Архивариус (A05) читает память города через Оле.
#
# Спринт 45 · 2026-06-18 · Брат (Claude) · ШАГ 4 · движение А
#
# ЗАМЫСЕЛ (от Шефа, §память города):
#   Архивариус — Оле Торгового Квартала. Когда его собственная тетрадь
#   (Атлас сделок цеха) пуста или тонка, он не молчит «истории нет» —
#   он стучится к Оле в большую память города: «а было ли похожее в
#   городе вообще?». Не нашёл — тихо, ничего не меняется. Нашёл —
#   его голос Совету обретает глубину всего, что помнит Грондхейм.
#
# ЧТО ДЕЛАЕТ (только run_arkhiv, только ДОБАВЛЯЕТ — ни строки не ломает):
#   После build_digest, если sample_size < ПОРОГ (тонкая/пустая история):
#     1. строит запрос к Оле из сигнатуры момента (человеческим текстом)
#     2. зовёт remind(query) — поиск в city_memory + Гавани (семантика)
#     3. если Оле подняла — кладёт форматированный блок в user_msg
#        отдельной секцией «=== ПАМЯТЬ ГОРОДА (Оле подняла) ===»
#     4. кладёт сырой результат в выход run_arkhiv["city_memory"]
#        (для приборов/чата позже — пока просто живёт в ответе)
#
# ЧЕГО НЕ ТРОГАЕТ (железно):
#   · ЧИСЛА digest — sample_size/success_rate/confidence считает КОД.
#     Город НЕ подменяет счёт. Он добавляет ГОЛОСУ глубину, не цифрам.
#     Защита чисел в конце run_arkhiv остаётся как была.
#   · Закон §1f — Архивариус контекст, не голос. Оле тоже контекст.
#   · Богатую историю (sample_size >= ПОРОГ) — тогда город не зовём,
#     своей тетради достаточно, не шумим Оле зря.
#
# БЕЗОПАСНОСТЬ: весь зов Оле в try/except. Оле недоступна / упала /
#   пусто — Архивариус работает ровно как до патча. Рука берущая
#   НИКОГДА не роняет прогон. Не нашёл — молчит.
#
# ИДЕМПОТЕНТНОСТЬ: маркер ARKHIV_HAND_TAKING. Повтор — no-op.
# БЭКАП: arkhiv_live.py.bak_<timestamp>.
# ─────────────────────────────────────────────────────────────

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/modules/trading/arkhiv_live.py")
MARKER = "ARKHIV_HAND_TAKING"

# ── Блок 1: функция руки берущей. Вставляем перед run_arkhiv. ──
# Якорь — заголовок-комментарий главной функции.
ANCHOR_FUNC = (
    "# ════════════════════════════════════════════════════════════\n"
    "# ГЛАВНАЯ ФУНКЦИЯ — Архивариус отвечает Совету\n"
    "# ════════════════════════════════════════════════════════════\n"
)

HAND_FUNC = '''# ════════════════════════════════════════════════════════════
# РУКА БЕРУЩАЯ (ARKHIV_HAND_TAKING) — память города через Оле
# ─────────────────────────────────────────────────────────────
# Когда тетрадь цеха тонка, Архивариус стучится к Оле: было ли
# похожее в большой памяти города? Оле — рабочая дверь (remind):
# ищет в city_memory + Гавани Смыслов (семантика). Контекст, не голос.
# ════════════════════════════════════════════════════════════

# Ниже этого порога история считается ТОНКОЙ — зовём Оле за глубиной.
# Совпадает с границей MEDIUM в правиле confidence (малая выборка лжёт).
_THIN_HISTORY = 5


def _signature_to_query(signature: dict) -> str:
    """
    Лепит человеческий запрос к Оле из сигнатуры момента.
    Оле ищет по СМЫСЛУ (Гавань) — даём ей словесный отпечаток стола,
    а не голый JSON. Пустые грани пропускаем.
    """
    parts = []
    t1 = signature.get("t1_status")
    if t1 and t1 != "NOT_FOUND":
        parts.append(f"разворот {t1}")
    morj = signature.get("morj_status")
    if morj and morj != "SLEEPING":
        parts.append(f"рынок {morj}")
    panic = signature.get("panic_phase")
    if panic:
        parts.append(f"толпа {panic}")
    if signature.get("fractal_valid"):
        parts.append("действительный фрактал")
    # Якорь темы — чтобы Оле не притащила память про сад или маяк.
    base = "торговое решение цеха"
    return f"{base}: {', '.join(parts)}" if parts else base


def _ask_city_memory(signature: dict, digest: dict) -> list:
    """
    Рука берущая. Зовёт Оле ТОЛЬКО при тонкой истории.
    Возвращает список поднятых записей (или пустой — всегда безопасно).

    НИКОГДА не роняет прогон: любая беда с Оле → пустой список,
    Архивариус работает как до патча.
    """
    if digest.get("sample_size", 0) >= _THIN_HISTORY:
        return []  # своей тетради хватает — не шумим Оле
    try:
        from studio.memory_tools import remind
        query = _signature_to_query(signature)
        hits = remind(query, top_k=3) or []
        if hits:
            print(f"[ARKHIV] 🤝 Оле подняла {len(hits)} из памяти города "
                  f"(тетрадь тонка: {digest.get('sample_size',0)})")
        return hits
    except Exception as e:
        print(f"[ARKHIV] ⚠️  Оле недоступна ({e}) — работаю своей тетрадью")
        return []


def _format_city_for_arkhiv(hits: list) -> str:
    """Форматирует поднятое Оле для вставки в user_msg Архивариуса."""
    if not hits:
        return ""
    try:
        from studio.memory_tools import format_for_agent
        return format_for_agent(hits, max_chars=1200)
    except Exception:
        # запасной простой формат, если format_for_agent недоступен
        lines = ["=== 🧠 ПАМЯТЬ ГОРОДА (Оле подняла) ==="]
        for h in hits[:3]:
            title = h.get("title", "")
            loss = h.get("loss_if_forgotten", "")
            lines.append(f"• {title}: {loss[:150]}")
        lines.append("=== КОНЕЦ ===")
        return "\\n".join(lines)


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — Архивариус отвечает Совету
# ════════════════════════════════════════════════════════════
'''

# ── Блок 2: вызов руки внутри run_arkhiv. ──
# Якорь — строка сразу после построения digest.
ANCHOR_CALL = "    digest = build_digest(signature)\n"

CALL_INSERT = '''    digest = build_digest(signature)

    # ── РУКА БЕРУЩАЯ (ARKHIV_HAND_TAKING) ──
    # Тетрадь тонка → спрашиваем Оле память города. Числа digest НЕ
    # трогаем (правда у кода) — город добавляет голосу глубины.
    city_hits = _ask_city_memory(signature, digest)
    city_block = _format_city_for_arkhiv(city_hits)
'''

# ── Блок 3: вставка городского блока в user_msg. ──
# Якорь — конец сборки user_msg (закрывающая скобка с "Ничего вне JSON.").
ANCHOR_USERMSG = (
    '        "sample_size, success_rate, top_failure_reason, arkhiv_confidence. "\n'
    '        "Ничего вне JSON."\n'
    '    )\n'
)

USERMSG_INSERT = (
    '        "sample_size, success_rate, top_failure_reason, arkhiv_confidence. "\n'
    '        "Ничего вне JSON."\n'
    '    )\n'
    '\n'
    '    # Рука берущая: если Оле что-то подняла из памяти города —\n'
    '    # вкладываем отдельной секцией. Архивариус вплетёт это в голос\n'
    '    # (narrative), но числа signal оставит из digest (закон кода).\n'
    '    if city_block:\n'
    '        user_msg += (\n'
    '            "\\n\\n=== 🧠 ПАМЯТЬ ГОРОДА (Оле подняла — тетрадь цеха тонка) ===\\n"\n'
    '            + city_block +\n'
    '            "\\n\\nЭто из большой памяти города, не из твоего Атласа. "\n'
    '            "Можешь опереться на это в narrative как на контекст прошлого "\n'
    '            "города. Но signal (числа) — по-прежнему из твоего digest."\n'
    '        )\n'
)

# ── Блок 4: city_memory в возврат run_arkhiv. ──
# Якорь — словарь возврата (строка с "digest": digest,).
ANCHOR_RETURN = '        "digest": digest,\n'

RETURN_INSERT = (
    '        "digest": digest,\n'
    '        "city_memory": city_hits,   # ARKHIV_HAND_TAKING: что Оле подняла\n'
)


def main():
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}. Запусти из корня репозитория студии.")
        return

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ Маркер {MARKER} уже в файле — патч применён ранее. Ничего не делаю.")
        return

    # Проверяем ВСЕ якоря до единой замены — если хоть один не найден, стоп.
    anchors = {
        "функция":   ANCHOR_FUNC,
        "вызов":     ANCHOR_CALL,
        "user_msg":  ANCHOR_USERMSG,
        "возврат":   ANCHOR_RETURN,
    }
    missing = [name for name, a in anchors.items() if a not in src]
    if missing:
        print(f"❌ Не найдены якоря: {', '.join(missing)}.")
        print("   Файл изменился — не вставляю вслепую. Покажи arkhiv_live.py.")
        return

    # Проверяем уникальность каждого якоря (по 1 разу).
    for name, a in anchors.items():
        if src.count(a) != 1:
            print(f"❌ Якорь «{name}» встречается {src.count(a)} раз (нужен 1). Стоп.")
            return

    new_src = src
    new_src = new_src.replace(ANCHOR_FUNC, HAND_FUNC, 1)
    new_src = new_src.replace(ANCHOR_CALL, CALL_INSERT, 1)
    new_src = new_src.replace(ANCHOR_USERMSG, USERMSG_INSERT, 1)
    new_src = new_src.replace(ANCHOR_RETURN, RETURN_INSERT, 1)

    if new_src == src:
        print("❌ Замены не сработали. Стоп.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(TARGET.suffix + f".bak_{ts}")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(new_src, encoding="utf-8")

    import py_compile
    try:
        py_compile.compile(str(TARGET), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"❌ СИНТАКСИС СЛОМАН после патча: {e}")
        print(f"   Откатываю из бэкапа {backup.name}")
        shutil.copy2(backup, TARGET)
        return

    print(f"✅ Рука берущая вживлена: Архивариус читает память города через Оле.")
    print(f"   Бэкап: {backup.name}")
    print(f"   Маркер: {MARKER}")
    print()
    print(f"   Когда тетрадь цеха тонка (< 5 случаев) — стучится к Оле,")
    print(f"   вплетает память города в голос. Числа digest не трогает (правда кода).")
    print(f"   Оле упала/пусто → работает как раньше (рука не роняет прогон).")


if __name__ == "__main__":
    main()
