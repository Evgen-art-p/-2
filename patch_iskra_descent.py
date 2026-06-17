# -*- coding: utf-8 -*-
# patch_iskra_descent.py
# ─────────────────────────────────────────────────────────────
# ПРОВОДКА ИСКРЫ v2 — СПУСК ПО ЛЕСЕНКЕ ТФ (Способ 1: штангенциркуль)
# Спринт 45 · 2026-06-17
#
# ЧТО ДЕЛАЕТ (на пальцах):
#   Учит iskra_live спускаться по лесенке таймфреймов, неся компас
#   старшего этажа в руке. Слепая геометрия (код, без LLM) находит
#   точку B/D/B в сторону компаса — и только потом просыпается живая
#   Искра ОДНИМ вызовом, чтобы озвучить найденное.
#
#   Старт этажа: из feed_config.json (watchlist по symbol), фоллбэк —
#   на timeframe из аргумента run_iskra.
#
#   Компас = СВЯЗКА: дивер засчитывается только с горбом-царём и
#   пересечением нуля после него (голый дивер ложен — §1d).
#
#   Спуск ЛЕНИВЫЙ: на идеале сверху (B/D/B уже совпал с компасом)
#   не стартует вовсе. Шоры: на младших этажах берём только bdb_*,
#   дивер/якорь младшего ТФ игнорируем — компас уже в руке.
#
#   Крик — минимум 4 поля в trading_state["iskra"]:
#     trend_direction · zero_point · found_timeframe · t1_status
#
# БЕЗОПАСНОСТЬ:
#   · идемпотентный (маркер _DESCENT_MARKER — повторный запуск не тронет)
#   · бэкап iskra_live.py.bak перед правкой
#   · регэкспы с re.DOTALL (Windows CRLF)
#   · НИЧЕГО не удаляет из существующего кода — только вставляет
# ─────────────────────────────────────────────────────────────

import re
import sys
import shutil
from pathlib import Path

# ── Путь к цели ──────────────────────────────────────────────
TARGET = Path("studio/modules/trading/iskra_live.py")

_DESCENT_MARKER = "# ISKRA_V2_DESCENT"   # маркер идемпотентности


# ════════════════════════════════════════════════════════════
# БЛОК 1 — новые функции спуска (вставляются перед run_iskra)
# ════════════════════════════════════════════════════════════
_DESCENT_FUNCS = '''# ════════════════════════════════════════════════════════════
# ISKRA_V2_DESCENT — СПУСК ПО ЛЕСЕНКЕ ТФ (Способ 1: штангенциркуль)
# ─────────────────────────────────────────────────────────────
# Слепая геометрия. Ни одного LLM-вызова. Код несёт компас старшего
# этажа в руке и ищет точку B/D/B вниз по лесенке. Живая Искра
# просыпается ПОЗЖE, одним вызовом, чтобы озвучить найденное.
# Закон §1d: сенсор мерит, не судит. Спуск — измерение резкости.
# ════════════════════════════════════════════════════════════

def _start_timeframe(symbol: str, fallback: str) -> str:
    """
    Стартовый (макро) этаж = абсолютная истина для актива.
    Приоритет: feed_config.json (watchlist по symbol). Фоллбэк:
    аргумент вызова (новый актив, которого нет в конфиге).
    Конфиг задаёт реальность — кнопка РЫНОК остаётся гибкой.
    """
    try:
        import json
        cfg_path = STATE_DIR / "feed_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            for item in cfg.get("watchlist", []):
                if item.get("symbol") == symbol:
                    tf = item.get("timeframe")
                    if tf:
                        return tf
    except Exception as e:
        print(f"[ISKRA] ℹ️  feed_config не прочитан ({e}) — старт от аргумента")
    return fallback


def _read_form_on(symbol: str, tf: str) -> dict:
    """
    Разовый замер одного этажа: pull_bars → ядро → wave_form.
    Чистый штангенциркуль — пришёл, померил, ушёл. Терминал не дал
    баров → пустая форма (этаж слепой, спуск это поймёт).
    """
    from studio.modules.trading.mt5_feed import pull_bars
    from studio.modules.trading.williams_core import build_market_data, _empty_wave_form

    bars, point = pull_bars(symbol, tf)
    if not bars or point is None:
        return _empty_wave_form()
    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point)
    if not md:
        return _empty_wave_form()
    return md.get("wave_form", _empty_wave_form())


def _compass_from(form: dict):
    """
    КОМПАС = СВЯЗКА (§1d). Дивер засчитывается ТОЛЬКО с якорем-царём
    и пересечением нуля после него. Голый дивер ложен — их полно.
      BULL: divergence_dir=BULL + есть anchor_ao_max + zero_cross_after_max
      BEAR: divergence_dir=BEAR + есть anchor_ao_min + zero_cross_after_min
    Возвращает "BULL" / "BEAR" / None.
    """
    d = form.get("divergence_dir")
    if d == "BULL":
        if form.get("anchor_ao_max") is not None and form.get("zero_cross_after_max"):
            return "BULL"
    elif d == "BEAR":
        if form.get("anchor_ao_min") is not None and form.get("zero_cross_after_min"):
            return "BEAR"
    return None


def _descend(symbol: str, start_tf: str, compass: str, top_form: dict) -> dict:
    """
    Спуск по лесенке с компасом в руке. ШОРЫ: на каждом этаже берём
    ТОЛЬКО bdb_dir/bdb_price; дивер и якорь младшего ТФ игнорируем —
    компас уже зажат на старшем (§1d, "снайпер с откалиброванным
    компасом"). Ищем B/D/B строго В СТОРОНУ компаса.

    start_tf — этаж, на котором компас УЖЕ взят.
    top_form — УЖЕ снятый слепок старшего этажа (из run_iskra). Старший
    этаж НЕ перемеряем — проверяем точку прямо по нему (идеал сверху),
    в терминал стучимся только начиная со ВТОРОГО этажа. Минус один
    вызов MT5 на каждый прогон.

    Возвращает:
      {"found": bool, "timeframe": str|None, "zero_point": float|None}
    found=False → дошли до дна M5 без точки (или этажи ослепли).
    """
    from studio.modules.trading.mt5_feed import step_down

    tf   = start_tf
    form = top_form          # старший этаж — по готовому слепку, без стука
    visited = 0
    while tf is not None and visited < 12:   # 12 = страховка от бесконечного цикла
        bdb_dir = form.get("bdb_dir")
        if bdb_dir == compass:
            return {"found": True, "timeframe": tf,
                    "zero_point": form.get("bdb_price")}
        nxt = step_down(tf)
        if nxt is None:        # дно M5 — глубже кислорода нет
            break
        tf = nxt
        form = _read_form_on(symbol, tf)   # второй этаж и ниже — стучимся
        visited += 1
    return {"found": False, "timeframe": None, "zero_point": None}


'''


# ════════════════════════════════════════════════════════════
# БЛОК 2 — вставка вызова спуска внутрь run_iskra
# ─────────────────────────────────────────────────────────────
# Встаёт между «посчитать market_data ядром» и «собрать контекст».
# Перезаписывает СТАРТОВЫЙ ТФ из конфига, гоняет спуск ДО вдоха
# Искры, кладёт итог в md["v2_descent"] (его прочитает сборка user_msg).
# ════════════════════════════════════════════════════════════
_DESCENT_CALL = '''
    # ── 2b. СПУСК ПО ЛЕСЕНКЕ (Искра v2, штангенциркуль) ──────  # ISKRA_V2_DESCENT
    # Слепая геометрия ДО вдоха Искры. Старт этажа из конфига
    # (фоллбэк — аргумент timeframe). Компас связкой (дивер+якорь).
    # Спуск ленивый: на идеале сверху не шагаем вниз вовсе.
    _start_tf = _start_timeframe(symbol, timeframe)
    _top_form = _read_form_on(symbol, _start_tf)
    _compass  = _compass_from(_top_form)
    if _compass is None:
        # Нет компаса (нет дивера-с-якорем) — Искре нечего ловить.
        _descent = {"found": False, "timeframe": None,
                    "zero_point": None, "compass": None, "start_tf": _start_tf}
    else:
        _res = _descend(symbol, _start_tf, _compass, _top_form)
        _descent = {"found": _res["found"], "timeframe": _res["timeframe"],
                    "zero_point": _res["zero_point"], "compass": _compass,
                    "start_tf": _start_tf}
    md["v2_descent"] = _descent
    print(f"[ISKRA] 🪜 Спуск: компас={_descent['compass']} "
          f"старт={_descent['start_tf']} "
          f"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}")

'''


# ════════════════════════════════════════════════════════════
# БЛОК 3 — итог спуска в user_msg + крик минимума в память
# ════════════════════════════════════════════════════════════
_DESCENT_CTX = '''        "=== СПУСК ПО ЛЕСЕНКЕ (Искра v2 — слепая геометрия уже отработала) ===\\n"
        f"Компас (старший этаж {md.get('v2_descent',{}).get('start_tf','?')}): "
        f"{md.get('v2_descent',{}).get('compass') or 'нет дивера-с-якорем'}\\n"
        f"Точка найдена: "
        f"{('ДА на ' + str(md['v2_descent']['timeframe']) + ', цена ' + str(md['v2_descent']['zero_point'])) if md.get('v2_descent',{}).get('found') else 'нет — молчи (NOT_FOUND)'}\\n"
        "Это РЕЗУЛЬТАТ твоего спуска. Если точка найдена — твой signal "
        "t1_status=DETECTED, trend_direction=компас, zero_point_price=цена. "
        "Если не найдена — t1_status=NOT_FOUND. Озвучь это своим голосом.\\n\\n"
'''


def _apply():
    if not TARGET.exists():
        print(f"❌ Не найден файл: {TARGET}")
        print("   Запусти патч из КОРНЯ проекта (там, где папка studio/).")
        return False

    src = TARGET.read_text(encoding="utf-8")

    if _DESCENT_MARKER in src:
        print("✅ Патч уже применён (маркер ISKRA_V2_DESCENT найден). Ничего не делаю.")
        return True

    # ── Бэкап ────────────────────────────────────────────────
    backup = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    original = src

    # ── ВСТАВКА 1: функции спуска перед def run_iskra ─────────
    # Якорь: строка определения run_iskra (с возможным CRLF).
    m1 = re.search(r"\ndef run_iskra\(", src)
    if not m1:
        print("❌ Не нашёл 'def run_iskra(' — структура файла изменилась. Откат.")
        shutil.copy2(backup, TARGET)
        return False
    src = src[:m1.start()] + "\n" + _DESCENT_FUNCS + src[m1.start()+1:]

    # ── ВСТАВКА 2: вызов спуска после сборки market_data ─────
    # Якорь: строка, где md собран и проверен (после блока «if not md»).
    # Ищем конкретный комментарий шага 3, вставляем ПЕРЕД ним.
    m2 = re.search(r"\n    # ── 3\. Собрать контекст для Искры", src, re.DOTALL)
    if not m2:
        print("❌ Не нашёл якорь '# ── 3. Собрать контекст' — откат.")
        shutil.copy2(backup, TARGET)
        return False
    src = src[:m2.start()] + "\n" + _DESCENT_CALL + src[m2.start()+1:]

    # ── ВСТАВКА 3: итог спуска в user_msg ────────────────────
    # Якорь: первая строка user_msg ("=== ТВОЯ РАБОЧАЯ ПАМЯТЬ").
    m3 = re.search(r'(    user_msg = \(\n)(        "=== ТВОЯ РАБОЧАЯ ПАМЯТЬ)', src, re.DOTALL)
    if not m3:
        print("❌ Не нашёл якорь user_msg '=== ТВОЯ РАБОЧАЯ ПАМЯТЬ' — откат.")
        shutil.copy2(backup, TARGET)
        return False
    src = src[:m3.start()] + m3.group(1) + _DESCENT_CTX + m3.group(2) + src[m3.end():]

    if src == original:
        print("⚠️  Ничего не изменилось — якоря не сработали. Откат.")
        shutil.copy2(backup, TARGET)
        return False

    TARGET.write_text(src, encoding="utf-8")
    print("✅ Патч применён. Проводка спуска вшита в iskra_live.")
    print("   Новое: _start_timeframe · _read_form_on · _compass_from · _descend")
    print("   run_iskra: спуск отрабатывает ДО вдоха Искры, итог в md['v2_descent'].")
    return True


if __name__ == "__main__":
    ok = _apply()
    sys.exit(0 if ok else 1)
