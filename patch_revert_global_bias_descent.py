#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_revert_global_bias_descent.py
# ─────────────────────────────────────────────────────────────
# ОТКАТ: снимает ISKRA_GLOBAL_BIAS_DESCENT_V1 (фоллбэк-компас на синюю)
# маркер отката: шесть·проверено·до·корня
#
# ПОЧЕМУ ОТКАТ:
#   Фоллбэк-компас (синяя global_bias будит спуск, когда дивер молчит)
#   на H1 дал кашу: дивер и синяя дают РАЗНЫЕ стороны на каждом баре
#   (компас=BEAR при кандидате BULL и наоборот), компасы дерутся,
#   результат мечется. Книга Котина (§6) говорит: вход по ДИВЕРГЕНЦИИ
#   AO, синяя — фильтр направления (§7), не компас входа. Фоллбэк на
#   синюю — не каноничный костыль. Возвращаем чистый дивер-компас.
#
# ЧТО ДЕЛАЕТ:
#   Восстанавливает run_iskra/_descend/_read_form_on к состоянию ДО
#   фоллбэк-патча: спуск идёт ТОЛЬКО по дивер-компасу (_compass_from),
#   strict=True всегда, никакой синей. Совет собирается реже, но на
#   чистых дивер-сигналах — по книге.
#
#   Если ISKRA_GLOBAL_BIAS_DESCENT_V1 в файле нет — значит откатывать
#   нечего (или уже откатили), выходим.
#
# БЕЗОПАСНО: бэкап рядом. Идемпотентен (повтор видит, что фоллбэка нет).
#
# АЛЬТЕРНАТИВА: если у тебя сохранён бэкап от установки фоллбэка
# (iskra_live.bak_ВРЕМЯ.py), можно просто:
#   cp studio/modules/trading/iskra_live.bak_ВРЕМЯ.py \
#      studio/modules/trading/iskra_live.py
# Этот скрипт делает то же, но не зависит от имени бэкапа.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

FALLBACK_MARKER = "ISKRA_GLOBAL_BIAS_DESCENT_V1"
ISKRA = Path("studio/modules/trading/iskra_live.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def main():
    if not ISKRA.exists():
        _die(f"не найден {ISKRA} — запусти из корня репы (-2/).")
    src = ISKRA.read_text(encoding="utf-8")
    if FALLBACK_MARKER not in src:
        print(f"✅ фоллбэк-компас ({FALLBACK_MARKER}) в файле не найден — "
              f"откатывать нечего (или уже откатили). Выхожу.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ISKRA.with_name(f"{ISKRA.stem}.bak_revert_{stamp}{ISKRA.suffix}")
    shutil.copy2(ISKRA, backup)
    print(f"💾 бэкап: {backup.name}")

    # ── 1. вернуть run_iskra к чистому диверу ──
    # Ищем блок фоллбэка (контур 1 + контур 2) и заменяем на оригинал.
    fallback_block_start = "    _compass  = _compass_from(_top_form)\n    _compass_source = None"
    if fallback_block_start not in src:
        _die("блок фоллбэка в run_iskra не найден — файл изменён вручную? "
             "Откати из бэкапа установки фоллбэка вручную (cp).")

    # Находим начало и конец блока, который вставил фоллбэк-патч.
    # Начало: строка с _compass_from + _compass_source = None
    # Конец: перед "    md[\"v2_descent\"] = _descent"
    start_idx = src.index("    _compass  = _compass_from(_top_form)\n    _compass_source = None")
    end_marker = "    md[\"v2_descent\"] = _descent"
    end_idx = src.index(end_marker, start_idx)

    original_block = (
        "    _compass  = _compass_from(_top_form)\n"
        "    if _compass is None:\n"
        "        # Нет компаса (нет дивера-с-якорем) — Искре нечего ловить.\n"
        "        _descent = {\"found\": False, \"timeframe\": None,\n"
        "                    \"zero_point\": None, \"compass\": None, \"start_tf\": _start_tf}\n"
        "    else:\n"
        "        _res = _descend(symbol, _start_tf, _compass, _top_form)\n"
        "        _descent = {\"found\": _res[\"found\"], \"timeframe\": _res[\"timeframe\"],\n"
        "                    \"zero_point\": _res[\"zero_point\"], \"compass\": _compass,\n"
        "                    \"start_tf\": _start_tf}\n"
    )
    src = src[:start_idx] + original_block + src[end_idx:]

    # ── 2. вернуть лог спуска к простому виду ──
    new_log = (
        "    _src_tag = _descent.get('compass_source')\n"
        "    _src_str = (' (синяя)' if _src_tag == 'global_bias'\n"
        "                else ' (дивер)' if _src_tag == 'divergence' else '')\n"
        "    print(f\"[ISKRA] 🪜 Спуск: компас={_descent['compass']}{_src_str} \"\n"
        "          f\"старт={_descent['start_tf']} \"\n"
        "          f\"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}\")\n"
    )
    orig_log = (
        "    print(f\"[ISKRA] 🪜 Спуск: компас={_descent['compass']} \"\n"
        "          f\"старт={_descent['start_tf']} \"\n"
        "          f\"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}\")\n"
    )
    if new_log in src:
        src = src.replace(new_log, orig_log, 1)

    # ── 3. вернуть _descend к оригиналу (убрать strict) ──
    new_sig = (
        "def _descend(symbol: str, start_tf: str, compass: str, top_form: dict,\n"
        "             strict: bool = True) -> dict:   # " + FALLBACK_MARKER + "\n"
    )
    orig_sig = "def _descend(symbol: str, start_tf: str, compass: str, top_form: dict) -> dict:\n"
    if new_sig in src:
        src = src.replace(new_sig, orig_sig, 1)

    new_body = (
        "    visited = 0\n"
        "    # " + FALLBACK_MARKER + ": strict=True → строгая Точка Ноль (bdb_dir);\n"
        "    # strict=False → мягкая точка по фону (bdb_candidate_dir).\n"
        "    _field = \"bdb_dir\" if strict else \"bdb_candidate_dir\"\n"
        "    while tf is not None and visited < 12:   # 12 = страховка от бесконечного цикла\n"
        "        bdb_dir = form.get(_field)\n"
        "        if bdb_dir == compass:\n"
        "            return {\"found\": True, \"timeframe\": tf,\n"
        "                    \"zero_point\": form.get(\"bdb_price\")\n"
        "                    or form.get(\"bdb_candidate_price\")}\n"
    )
    orig_body = (
        "    visited = 0\n"
        "    while tf is not None and visited < 12:   # 12 = страховка от бесконечного цикла\n"
        "        bdb_dir = form.get(\"bdb_dir\")\n"
        "        if bdb_dir == compass:\n"
        "            return {\"found\": True, \"timeframe\": tf,\n"
        "                    \"zero_point\": form.get(\"bdb_price\")}\n"
    )
    if new_body in src:
        src = src.replace(new_body, orig_body, 1)

    # ── 4. вернуть _read_form_on (убрать candidate-поля) ──
    new_read_tail = (
        "    form = dict(md.get(\"wave_form\", _empty_wave_form()))\n"
        "    # " + FALLBACK_MARKER + ": мягкая точка (candidate) для фоллбэк-компаса.\n"
        "    # Строгий bdb_dir требует дивергенцию (её при фоллбэке нет),\n"
        "    # а candidate — обычный B/D/B бар, его и ищем по синей.\n"
        "    _db = md.get(\"divergent_bar\", {}) or {}\n"
        "    _cand_dir = _db.get(\"direction\") if _db.get(\"bdb_candidate\") else None\n"
        "    form[\"bdb_candidate_dir\"] = _cand_dir\n"
        "    # цена мягкой точки: low бара для BULL, high для BEAR (как strong)\n"
        "    _px = md.get(\"price\", {}) or {}\n"
        "    if _cand_dir == \"BULL\":\n"
        "        form[\"bdb_candidate_price\"] = _px.get(\"low\")\n"
        "    elif _cand_dir == \"BEAR\":\n"
        "        form[\"bdb_candidate_price\"] = _px.get(\"high\")\n"
        "    else:\n"
        "        form[\"bdb_candidate_price\"] = None\n"
        "    return form\n"
    )
    orig_read_tail = (
        "    return md.get(\"wave_form\", _empty_wave_form())\n"
    )
    if new_read_tail in src:
        src = src.replace(new_read_tail, orig_read_tail, 1)

    # ── 5. снять маркер из шапки ──
    src = src.replace(
        "# " + FALLBACK_MARKER + " · синяя (global_bias) будит спуск, когда дивер молчит\n",
        "",
        1,
    )

    ISKRA.write_text(src, encoding="utf-8")
    print(f"✅ фоллбэк-компас откатан — спуск снова по чистому дивер-компасу")
    print("   · синяя (global_bias) к спуску больше не подключена")
    print("   · вход по дивергенции AO (§6 книги), как и должно")
    print("   · Совет собирается реже, но на чистых сигналах — без каши")
    print(f"\n   откат отката (вернуть фоллбэк): cp {backup.name} {ISKRA.name}")


if __name__ == "__main__":
    main()
