#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: ЗАГРУЗЧИК БИРЖИ → ASYNC (список появляется)
# Маркер: EXCHANGE_UPLOAD_ASYNC_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# БЕДА (Шеф): загрузил актив — под загрузчиком ПУСТО. Список не рисуется.
# А в других местах студии загрузчик работает.
#
# ПРИЧИНА (сравнил с рабочими загрузчиками кабинета): все рабочие
# on_upload-обработчики студии — ASYNC def (handle_library_upload_book,
# handle_upload в кабинете). Биржевой же — обычный def. В NiceGUI
# обработчик upload, который читает e.content.read() и затем обновляет
# UI (update_files_display), должен быть async — иначе перерисовка DOM
# из синхронного колбэка не применяется: данные в state легли, а список
# на экране пуст. Ровно «пусто» у Шефа.
#
# РЕШЕНИЕ: делаем handle_upload async — как все рабочие в студии.
# Тело не трогаем (оно верное: читает, кладёт в loaded_assets, зовёт
# update_files_display). Только сигнатура def → async def.
#
# ОДНО КАСАНИЕ: ui_exchange.py — сигнатура handle_upload.
# Идемпотентно, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_upload_async.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_UPLOAD_ASYNC_V1"
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


# Сигнатура с докстрингом — якорь точный, чтобы не задеть другие def.
OLD = '''    def handle_upload(e):
        """Сохраняет CSV на диск, читает бары, выводит паспорт истории."""'''
NEW = '''    async def handle_upload(e):   # ''' + MARKER + ''' — async как рабочие загрузчики студии
        """Сохраняет CSV на диск, читает бары, выводит паспорт истории."""'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (upload-async) — пропускаю.")
        return False
    if OLD not in src:
        # может, уже async по другой причине?
        if "async def handle_upload(e):" in src:
            print("✅ handle_upload уже async — ничего не нужно.")
            return False
        _fail("exchange: не нашёл 'def handle_upload(e):' с докстрингом — структура изменилась.")
    src = src.replace(OLD, NEW, 1)
    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: handle_upload → async.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  ЗАГРУЗЧИК БИРЖИ → ASYNC (список появляется)  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. handle_upload теперь async — как рабочие загрузчики студии.")
        print("   Загрузи актив → список под загрузчиком появится.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено / уже async.")


if __name__ == "__main__":
    main()
