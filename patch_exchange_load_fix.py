#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ФИКС ЗАРЯДКИ — словесные ТФ MT5 + гашение висючки аплоадера
# Маркер: EXCHANGE_LOAD_FIX_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# ДВЕ БЕДЫ (с экрана Шефа):
#   1. EURUSDDaily.csv → паспорт показал тикер "EURUSDDAILY", ТФ "?".
#      Парсер искал только КОДЫ (D1/H4/M15...). MT5 же именует период
#      СЛОВАМИ: Daily/Weekly/Monthly/Hourly. Добавляем словесный словарь:
#        Monthly→MN1 · Weekly→W1 · Daily→D1 · Hourly→H1 (+ коды как были).
#      EURUSDDaily → EURUSD / D1.
#   2. «Висючка под загрузчиком до обновления» — родная плашка аплоадера
#      NiceGUI (412.8KB/100%) торчит после загрузки. Гасим её reset()-ом
#      сразу после обработки: остаётся ТОЛЬКО чистая карточка-паспорт.
#
# Идёт ПОВЕРХ EXCHANGE_HISTORY_LOAD_V1 (зарядка уже в main). Правит её
# парсер _parse_symbol_tf и навешивает reset на аплоадер.
#
# ДВА КАСАНИЯ в ui_exchange.py:
#   1. _parse_symbol_tf — словесный словарь ПЕРЕД кодами.
#   2. ui.upload получает ref + handle_upload в конце зовёт upload.reset().
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_load_fix.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_LOAD_FIX_V1"
ROOT = Path.cwd()
EXCHANGE = ROOT / "studio" / "economy" / "ui_exchange.py"


def _fail(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak_{stamp}")
    shutil.copy2(path, bak)
    print(f"   💾 бэкап: {bak.name}")


def _check_root():
    if not EXCHANGE.exists():
        _fail(f"Не вижу {EXCHANGE}. Запускай из КОРНЯ репы (где папка studio/).")
    src = EXCHANGE.read_text(encoding="utf-8")
    if "EXCHANGE_HISTORY_LOAD_V1" not in src:
        _fail("Сначала нужен патч зарядки EXCHANGE_HISTORY_LOAD_V1 — его в файле нет.")


# ── 1. Расширенный парсер: словесные ТФ MT5 перед кодами ──
OLD_PARSER = '''    def _parse_symbol_tf(filename: str):
        """EURUSDH1.csv → ('EURUSD','H1'). Код ТФ ищем в хвосте имени
        (длинные раньше: H12≠H1, MN1≠M1). Остаток спереди — тикер."""
        stem = filename.rsplit(".", 1)[0].upper().strip()
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"'''

NEW_PARSER = '''    # Словесные ТФ MT5 (экспорт пишет период словом).  # ''' + MARKER + '''
    _WORD_TFS = {"MONTHLY": "MN1", "WEEKLY": "W1", "DAILY": "D1", "HOURLY": "H1"}

    def _parse_symbol_tf(filename: str):
        """EURUSDDaily.csv → ('EURUSD','D1'); EURUSDH1.csv → ('EURUSD','H1').
        MT5 именует период СЛОВОМ (Daily/Weekly/Monthly/Hourly) ИЛИ кодом
        (D1/H4/M15...). Сперва словесные (длинные раньше), потом коды
        (H12≠H1, MN1≠M1). Остаток спереди — тикер."""
        stem = filename.rsplit(".", 1)[0].upper().strip()
        # словесные — сначала (Daily не должен съесться кодом)
        for word, tf in sorted(_WORD_TFS.items(), key=lambda x: -len(x[0])):
            if stem.endswith(word):
                return stem[:-len(word)].rstrip("_- "), tf
        # числовые коды
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"'''

# ── 2a. Аплоадер получает ref ──
OLD_UPLOAD_WIDGET = '''                    ui.upload(
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")'''

NEW_UPLOAD_WIDGET = '''                    files_ref["uploader"] = ui.upload(   # ''' + MARKER + '''
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")'''

# ── 2b. handle_upload в конце гасит висючку (uploader.reset) ──
# Якорь — финальный notify зарядки. Добавляем reset перед ним не нужно;
# добавим reset ПОСЛЕ него, в самом хвосте функции.
OLD_UPLOAD_TAIL = '''        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")'''

NEW_UPLOAD_TAIL = '''        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")
        # Гасим висючку аплоадера — остаётся только карточка-паспорт.  # ''' + MARKER + '''
        _up = files_ref.get("uploader")
        if _up:
            try:
                _up.reset()
            except Exception:
                pass'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (load-fix) — пропускаю.")
        return False

    if OLD_PARSER not in src:
        _fail("exchange: не нашёл _parse_symbol_tf зарядки — структура изменилась.")
    src = src.replace(OLD_PARSER, NEW_PARSER, 1)

    if OLD_UPLOAD_WIDGET not in src:
        _fail("exchange: не нашёл ui.upload биржи — структура изменилась.")
    src = src.replace(OLD_UPLOAD_WIDGET, NEW_UPLOAD_WIDGET, 1)

    if OLD_UPLOAD_TAIL not in src:
        _fail("exchange: не нашёл хвост handle_upload (notify Заряжено) — структура изменилась.")
    src = src.replace(OLD_UPLOAD_TAIL, NEW_UPLOAD_TAIL, 1)

    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: словесные ТФ + гашение висючки.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча ui_exchange.py НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  ФИКС ЗАРЯДКИ: словесные ТФ MT5 + гашение висючки  ·", MARKER)
    print("═" * 62)
    _check_root()

    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО.")
        print("   EURUSDDaily.csv → EURUSD · D1 (а не EURUSDDAILY · ?).")
        print("   Висючка аплоадера гаснет — остаётся только паспорт.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
