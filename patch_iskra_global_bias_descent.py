#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_iskra_global_bias_descent.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ISKRA_GLOBAL_BIAS_DESCENT_V1  ·  маркер: шесть·проверено·до·корня
#
# ЧТО ЧИНИТ (Совет молчит на золоте: компас=None, найдено 0 из 5):
#
#   Спуск Искры стартует ТОЛЬКО при дивер-компасе (_compass_from:
#   дивергенция AO + горб-царь + пересечение нуля). Это редкая связка
#   (~3-4/год). На золоте её не сложилось → компас=None → спуск даже
#   не запускается → ворота Совета закрыты → Совет молчит.
#
#   А global_bias (синяя линия Jaw, compute_global_bias) УЖЕ посчитан
#   и лежит в каждом md — живой, всегда на столе, переживает развороты.
#   Но спуск его НЕ спрашивает. Двухконтурность из мастера задумана,
#   но второй контур (синяя) к спуску не подключён.
#
# КАК ЧИНИТ (Вариант А — фоллбэк с честной маркировкой):
#
#   Когда дивер-компас молчит (None), берём global_bias из синей как
#   ФОЛЛБЭК и ВСЁ РАВНО запускаем спуск. Но точку при фоллбэке ищем
#   мягче: не bdb_strong (Точка Ноль, требует дивергенцию — её-то и
#   нет), а bdb_candidate (обычный B/D/B бар: lower_low+upper_close)
#   В СТОРОНУ синей. Это реальная геометрия разворота по фону, слабее
#   Точки Ноль, но не выдумка.
#
#   ЧЕСТНОСТЬ: точка по фоллбэку помечается compass_source="global_bias"
#   (против "divergence" у точного). Искра в signal несёт это поле,
#   Совет видит — сигнал ФОНОВЫЙ, не дивергентный, трейдеры судят строже.
#
#   Приоритет сохранён: дивер-компас (точный, редкий) идёт первым;
#   синяя — только когда дивер молчит. Точный контур не сломан.
#
# КАК (по коду iskra_live.py):
#   1. _descend получает флаг strict: strict=True → ищет bdb_dir (как
#      было, строгий); strict=False → ищет bdb_candidate_dir (мягкий).
#   2. _read_form_on/wave_form уже дают bdb_dir (strong). Для мягкого
#      нужен bdb_candidate_dir — добавляем его в чтение формы через
#      divergent_bar.bdb_candidate + direction (ядро уже считает).
#   3. run_iskra: дивер есть → _descend(strict=True), source=divergence.
#      дивер None, синяя BULL/BEAR → _descend(strict=False), source=global_bias.
#      синяя тоже NONE → как раньше, не стартуем.
#   4. signal Искры несёт compass_source.
#
# ИДЕМПОТЕНТЕН: маркер, повтор — выход. Бэкап рядом.
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

MARKER = "ISKRA_GLOBAL_BIAS_DESCENT_V1"
ISKRA = Path("studio/modules/trading/iskra_live.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def main():
    if not ISKRA.exists():
        _die(f"не найден {ISKRA} — запусти из корня репы (-2/).")
    src = ISKRA.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ {MARKER} уже стоит — патч идемпотентен, выхожу.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ISKRA.with_name(f"{ISKRA.stem}.bak_{stamp}{ISKRA.suffix}")
    shutil.copy2(ISKRA, backup)
    print(f"💾 бэкап: {backup.name}")

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 1 — _read_form_on отдаёт ещё и candidate-направление.
    # wave_form даёт bdb_dir (strong). Нам нужен мягкий bdb_candidate_dir.
    # Достаём его из divergent_bar ядра (build_market_data уже считает).
    # ═════════════════════════════════════════════════════════
    anchor_read = (
        "    bars, point = pull_bars(symbol, tf)\n"
        "    if not bars or point is None:\n"
        "        return _empty_wave_form()\n"
        "    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point)\n"
        "    if not md:\n"
        "        return _empty_wave_form()\n"
        "    return md.get(\"wave_form\", _empty_wave_form())\n"
    )
    if anchor_read not in src:
        _die("якорь _read_form_on не найден — файл изменился.")
    src = src.replace(
        anchor_read,
        "    bars, point = pull_bars(symbol, tf)\n"
        "    if not bars or point is None:\n"
        "        return _empty_wave_form()\n"
        "    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point)\n"
        "    if not md:\n"
        "        return _empty_wave_form()\n"
        "    form = dict(md.get(\"wave_form\", _empty_wave_form()))\n"
        "    # " + MARKER + ": мягкая точка (candidate) для фоллбэк-компаса.\n"
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
        "    return form\n",
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 2 — _descend получает strict. strict=False ищет candidate.
    # ═════════════════════════════════════════════════════════
    anchor_descend_sig = (
        "def _descend(symbol: str, start_tf: str, compass: str, top_form: dict) -> dict:\n"
    )
    if anchor_descend_sig not in src:
        _die("якорь сигнатуры _descend не найден.")
    src = src.replace(
        anchor_descend_sig,
        "def _descend(symbol: str, start_tf: str, compass: str, top_form: dict,\n"
        "             strict: bool = True) -> dict:   # " + MARKER + "\n",
        1,
    )

    # тело _descend: выбор поля по strict
    anchor_descend_body = (
        "    tf   = start_tf\n"
        "    form = top_form          # старший этаж — по готовому слепку, без стука\n"
        "    visited = 0\n"
        "    while tf is not None and visited < 12:   # 12 = страховка от бесконечного цикла\n"
        "        bdb_dir = form.get(\"bdb_dir\")\n"
        "        if bdb_dir == compass:\n"
        "            return {\"found\": True, \"timeframe\": tf,\n"
        "                    \"zero_point\": form.get(\"bdb_price\")}\n"
    )
    if anchor_descend_body not in src:
        _die("якорь тела _descend (цикл) не найден.")
    src = src.replace(
        anchor_descend_body,
        "    tf   = start_tf\n"
        "    form = top_form          # старший этаж — по готовому слепку, без стука\n"
        "    visited = 0\n"
        "    # " + MARKER + ": strict=True → строгая Точка Ноль (bdb_dir);\n"
        "    # strict=False → мягкая точка по фону (bdb_candidate_dir).\n"
        "    _field = \"bdb_dir\" if strict else \"bdb_candidate_dir\"\n"
        "    while tf is not None and visited < 12:   # 12 = страховка от бесконечного цикла\n"
        "        bdb_dir = form.get(_field)\n"
        "        if bdb_dir == compass:\n"
        "            return {\"found\": True, \"timeframe\": tf,\n"
        "                    \"zero_point\": form.get(\"bdb_price\")\n"
        "                    or form.get(\"bdb_candidate_price\")}\n",
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 3 — run_iskra: фоллбэк на global_bias когда дивер молчит.
    # ═════════════════════════════════════════════════════════
    anchor_run = (
        "    _start_tf = _start_timeframe(symbol, timeframe)\n"
        "    _top_form = _read_form_on(symbol, _start_tf)\n"
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
    if anchor_run not in src:
        _die("якорь блока спуска в run_iskra не найден.")
    src = src.replace(
        anchor_run,
        "    _start_tf = _start_timeframe(symbol, timeframe)\n"
        "    _top_form = _read_form_on(symbol, _start_tf)\n"
        "    _compass  = _compass_from(_top_form)\n"
        "    _compass_source = None   # " + MARKER + "\n"
        "    if _compass is not None:\n"
        "        # ── КОНТУР 1: точный дивер-компас (приоритет, редкий) ──\n"
        "        _compass_source = \"divergence\"\n"
        "        _res = _descend(symbol, _start_tf, _compass, _top_form, strict=True)\n"
        "        _descent = {\"found\": _res[\"found\"], \"timeframe\": _res[\"timeframe\"],\n"
        "                    \"zero_point\": _res[\"zero_point\"], \"compass\": _compass,\n"
        "                    \"start_tf\": _start_tf, \"compass_source\": \"divergence\"}\n"
        "    else:\n"
        "        # ── КОНТУР 2: фоллбэк на синюю (global_bias), мягкая точка ──\n"
        "        # " + MARKER + ": дивер молчит — берём синюю линию (Jaw).\n"
        "        # Она всегда на столе, переживает развороты. Точку ищем по\n"
        "        # candidate-бару в сторону фона (strict=False). Сигнал слабее\n"
        "        # Точки Ноль и ЧЕСТНО помечен compass_source=global_bias.\n"
        "        _gb = md.get(\"global_bias\")\n"
        "        if _gb in (\"BULL\", \"BEAR\"):\n"
        "            _compass_source = \"global_bias\"\n"
        "            _res = _descend(symbol, _start_tf, _gb, _top_form, strict=False)\n"
        "            _descent = {\"found\": _res[\"found\"], \"timeframe\": _res[\"timeframe\"],\n"
        "                        \"zero_point\": _res[\"zero_point\"], \"compass\": _gb,\n"
        "                        \"start_tf\": _start_tf, \"compass_source\": \"global_bias\"}\n"
        "        else:\n"
        "            # и синяя в переходной зоне (NONE) — ловить нечего\n"
        "            _descent = {\"found\": False, \"timeframe\": None, \"zero_point\": None,\n"
        "                        \"compass\": None, \"start_tf\": _start_tf,\n"
        "                        \"compass_source\": None}\n",
        1,
    )

    # ═════════════════════════════════════════════════════════
    # ПРАВКА 4 — лог спуска показывает источник компаса.
    # ═════════════════════════════════════════════════════════
    anchor_log = (
        "    print(f\"[ISKRA] 🪜 Спуск: компас={_descent['compass']} \"\n"
        "          f\"старт={_descent['start_tf']} \"\n"
        "          f\"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}\")\n"
    )
    if anchor_log not in src:
        _die("якорь лога спуска не найден.")
    src = src.replace(
        anchor_log,
        "    _src_tag = _descent.get('compass_source')\n"
        "    _src_str = (' (синяя)' if _src_tag == 'global_bias'\n"
        "                else ' (дивер)' if _src_tag == 'divergence' else '')\n"
        "    print(f\"[ISKRA] 🪜 Спуск: компас={_descent['compass']}{_src_str} \"\n"
        "          f\"старт={_descent['start_tf']} \"\n"
        "          f\"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}\")\n",
        1,
    )

    # маркер в шапку
    src = src.replace(
        "from studio.llm import chat\n",
        "from studio.llm import chat\n"
        "# " + MARKER + " · синяя (global_bias) будит спуск, когда дивер молчит\n",
        1,
    )

    ISKRA.write_text(src, encoding="utf-8")
    print(f"✅ {MARKER} применён к iskra_live.py")
    print("   · дивер молчит → спуск идёт по синей (global_bias)")
    print("   · фоллбэк-точка ищется по candidate-бару (мягче Точки Ноль)")
    print("   · точка честно помечена compass_source=global_bias")
    print("   · приоритет дивер-компаса сохранён (контур 1 первый)")
    print("   · лог показывает (синяя)/(дивер)")
    print(f"\n   откат: cp {backup.name} {ISKRA.name}")


if __name__ == "__main__":
    main()
