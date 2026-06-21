#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ЧИТАЛКА test_data при старте + список ПОД загрузчиком
# Маркер: EXCHANGE_SCAN_FOLDER_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# ТРИ БЕДЫ (Шеф):
#  1. Активы НАД загрузчиком — список (files_ref) в разметке стоит выше
#     ui.upload. Переставляем: загрузчик сверху, список ПОД ним.
#  2. При запуске активов не видно, хотя они в папке — update_files_display
#     при старте не звался (стояла статичная «Нет файлов»).
#  3. Идея Шефа: «наглая читалка» — при загрузке страницы прочитать папку
#     test_data/ и показать ВСЕ реально лежащие там CSV. Память между
#     сессиями даром: грузил раньше → активы уже на полке после рестарта.
#
# РЕШЕНИЕ:
#  · _passport_from_csv(path) — выносим сборку паспорта (чтобы и загрузка,
#    и читалка давали ОДИН формат). handle_upload зовёт её же.
#  · _scan_test_data() — сканирует studio/modules/trading/test_data/*.csv,
#    строит полку loaded_assets, активным делает первый.
#  · при построении: загрузчик ВЫШЕ списка; список рисуется читалкой
#    сразу (не статичная заглушка).
#
# Идёт поверх asset-list (loaded_assets). Идемпотентно, бэкап, py_compile.
# Запуск из корня репы:  python patch_exchange_scan_folder.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_SCAN_FOLDER_V1"
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
        _fail(f"Не вижу {EXCHANGE}. Запускай из КОРНЯ репы.")
    src = EXCHANGE.read_text(encoding="utf-8")
    if "loaded_assets" not in src:
        _fail("Нужен asset-list (loaded_assets) — его нет.")


# ── 1. Выносим сборку паспорта + читалку папки. Ставим ПЕРЕД handle_upload. ──
# Якорь — начало handle_upload (уже async).
UPLOAD_ANCHOR = '    async def handle_upload(e):   # EXCHANGE_UPLOAD_ASYNC_V1'
# на случай если async-патч не накатан:
UPLOAD_ANCHOR_ALT = '    def handle_upload(e):\n        """Сохраняет CSV на диск, читает бары, выводит паспорт истории."""'

SCAN_FUNCS = '''    # ── ЧИТАЛКА ПАПКИ: паспорт из CSV + скан test_data ──  # ''' + MARKER + '''
    _TEST_DATA_DIR = Path("studio/modules/trading/test_data")

    def _passport_from_csv(path):
        """Строит паспорт актива из CSV-файла (тикер/тф/период/баров)."""
        from studio.modules.trading.williams_core import read_mt5_csv
        p = Path(path)
        bars = read_mt5_csv(str(p))
        if not bars:
            return None
        symbol, tf = _parse_symbol_tf(p.name)
        return {
            "name":      p.name,
            "path":      str(p),
            "symbol":    symbol,
            "timeframe": tf,
            "bars":      len(bars),
            "date_from": bars[0].get("date", "?"),
            "date_to":   bars[-1].get("date", "?"),
        }

    def _scan_test_data():
        """Наглая читалка: все CSV из test_data → полка активов."""
        assets = []
        try:
            if _TEST_DATA_DIR.exists():
                for f in sorted(_TEST_DATA_DIR.glob("*.csv")):
                    try:
                        pp = _passport_from_csv(f)
                        if pp:
                            assets.append(pp)
                    except Exception as _e:
                        print(f"[EXCHANGE·SCAN] {f.name}: {_e}")
        except Exception as _e:
            print(f"[EXCHANGE·SCAN] папка: {_e}")
        state["loaded_assets"] = assets
        state["active_asset"] = 0 if assets else None

'''


def _patch_scan_funcs(src):
    if UPLOAD_ANCHOR in src:
        return src.replace(UPLOAD_ANCHOR, SCAN_FUNCS + UPLOAD_ANCHOR, 1)
    if UPLOAD_ANCHOR_ALT in src:
        return src.replace(UPLOAD_ANCHOR_ALT, SCAN_FUNCS + UPLOAD_ANCHOR_ALT, 1)
    _fail("exchange: не нашёл handle_upload — структура изменилась.")


# ── 2. Порядок в разметке: загрузчик СВЕРХУ, список ПОД ним + читалка при старте ──
OLD_LAYOUT = '''                    files_ref["element"] = ui.element("div").classes("file-list")
                    with files_ref["element"]:
                        ui.label("Нет файлов").style("color: rgba(255,255,255,0.4)")
                    files_ref["uploader"] = ui.upload(   # EXCHANGE_LOAD_FIX_V1
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")'''

NEW_LAYOUT = '''                    # Загрузчик СВЕРХУ.  # ''' + MARKER + '''
                    files_ref["uploader"] = ui.upload(   # EXCHANGE_LOAD_FIX_V1
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")
                    # Список активов ПОД загрузчиком.  # ''' + MARKER + '''
                    files_ref["element"] = ui.element("div").classes("file-list")
                    # Наглая читалка при старте: показать всё из test_data.
                    _scan_test_data()
                    update_files_display()'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (scan-folder) — пропускаю.")
        return False

    src = _patch_scan_funcs(src)

    if OLD_LAYOUT not in src:
        _fail("exchange: не нашёл блок разметки загрузчика — структура изменилась.")
    src = src.replace(OLD_LAYOUT, NEW_LAYOUT, 1)

    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: читалка папки + список под загрузчиком.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  ЧИТАЛКА test_data + список ПОД загрузчиком  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО.")
        print("   · Загрузчик сверху, список активов ПОД ним.")
        print("   · При старте папка test_data читается — активы уже на полке.")
        print("   · Грузил раньше → после рестарта они на месте, кликай и гони.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
