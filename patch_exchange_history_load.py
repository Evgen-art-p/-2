#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 4 · ШАГ 1 — ЗАРЯДКА ИСТОРИИ (паспорт под загрузчиком)
# Маркер: EXCHANGE_HISTORY_LOAD_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАМЫСЕЛ (Шеф): «загрузил актив, его считали, вывели под загрузчик
# тикер, период, тф». Загрузчик биржи (/exchange) перестаёт просто
# писать имя файла — он ЧИТАЕТ CSV и показывает паспорт заряженной
# истории: тикер · ТФ · период (первая→последняя дата) · число баров.
# Это фундамент экспресс-жизни: курсор-часы (след. шаг) погонят
# ИМЕННО эту заряженную историю через Совет.
#
# КАК ЧИТАЕТ:
#   · NiceGUI upload даёт байты → сохраняем CSV на диск в test_data/
#     (read_mt5_csv хочет путь; файл и так нужен на диске для курсора).
#   · read_mt5_csv (ядро) парсит бары (utf-16-le, поле date в каждом).
#   · тикер/ТФ из имени: EURUSDH1.csv → EURUSD / H1. Парсер ищет код
#     ТФ в ХВОСТЕ имени (длинные коды раньше: H12 не путать с H1, MN1
#     с M1). Что осталось спереди — тикер.
#   · период = date первого → date последнего бара; баров = len.
#
# ЧТО НЕ ДЕЛАЕТ (следующими шагами камня 4):
#   · тумблер тестер/реал · курсор-часы (проживание бар за баром)
#   · пауза/разгул. Здесь ТОЛЬКО зарядка и паспорт.
#
# ДВА КАСАНИЯ в ui_exchange.py:
#   1. state — поле loaded_history (паспорт заряженного куска).
#   2. handle_upload — читает CSV, наполняет паспорт; update_files_display
#      рисует карточку под загрузчиком.
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_history_load.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_HISTORY_LOAD_V1"
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


# ── 1. Поле паспорта в state ──
STATE_ANCHOR = '        "uploaded_files": [],      # загрузчик слева\n'
STATE_INSERT = (
    '        "uploaded_files": [],      # загрузчик слева\n'
    '        "loaded_history": None,    # паспорт заряженной истории (тикер/тф/период)  # ' + MARKER + '\n'
)

# ── 2. Новый handle_upload + парсер + рендер карточки ──
# Заменяем старый handle_upload целиком (он только имя писал).
OLD_UPLOAD = '''    def handle_upload(e):
        # Пока просто фиксируем имя файла в списке — без обработки.
        # Реальный разбор истории для тестера придёт позже.
        state["uploaded_files"].append({"name": e.name})
        update_files_display()
        ui.notify(f"Загружен: {e.name} (обработка — позже)", type="info")'''

NEW_UPLOAD = '''    # ── ЗАРЯДКА ИСТОРИИ (читаем CSV → паспорт под загрузчиком) ──  # ''' + MARKER + '''
    _HISTORY_TFS = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1",
                    "M30", "M15", "M10", "M5", "M1"]

    def _parse_symbol_tf(filename: str):
        """EURUSDH1.csv → ('EURUSD','H1'). Код ТФ ищем в хвосте имени
        (длинные раньше: H12≠H1, MN1≠M1). Остаток спереди — тикер."""
        stem = filename.rsplit(".", 1)[0].upper().strip()
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"

    def handle_upload(e):
        """Сохраняет CSV на диск, читает бары, выводит паспорт истории."""
        name = e.name
        try:
            content = e.content.read() if hasattr(e.content, "read") else e.content
        except Exception as _ce:
            ui.notify(f"Не прочитать файл: {_ce}", type="negative")
            return

        if not name.lower().endswith(".csv"):
            ui.notify("Нужен CSV экспорта MT5", type="warning")
            return

        # Сохраняем на диск — read_mt5_csv хочет путь, и курсору нужен файл.
        dest_dir = Path("studio/modules/trading/test_data")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        try:
            dest.write_bytes(content)
        except Exception as _we:
            ui.notify(f"Не сохранить файл: {_we}", type="negative")
            return

        # Читаем бары ядром (utf-16-le, поле date в каждом баре).
        try:
            from studio.modules.trading.williams_core import read_mt5_csv
            bars = read_mt5_csv(str(dest))
        except Exception as _re:
            ui.notify(f"Ядро не прочло CSV: {_re}", type="negative")
            return

        if not bars:
            ui.notify(f"{name}: пусто или не формат MT5", type="warning")
            return

        symbol, tf = _parse_symbol_tf(name)
        passport = {
            "name":       name,
            "path":       str(dest),
            "symbol":     symbol,
            "timeframe":  tf,
            "bars":       len(bars),
            "date_from":  bars[0].get("date", "?"),
            "date_to":    bars[-1].get("date", "?"),
        }
        state["loaded_history"] = passport
        # в список тоже кладём (совместимость со старым отображением)
        state["uploaded_files"] = [{"name": name}]
        update_files_display()
        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")'''

# ── 3. update_files_display — рисует карточку-паспорт ──
OLD_FILES_DISPLAY = '''    def update_files_display():
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            if not state["uploaded_files"]:
                ui.label("Нет файлов").style("color: rgba(255,255,255,0.4)")
            else:
                for f in state["uploaded_files"]:
                    ui.label(f["name"]).style(
                        "color: rgba(255,255,255,0.8); font-size: 11px;")'''

NEW_FILES_DISPLAY = '''    def update_files_display():
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            hist = state.get("loaded_history")  # ''' + MARKER + '''
            if hist:
                # Карточка-паспорт заряженной истории под загрузчиком.
                ui.html(f\'\'\'
                <div style="padding:10px 12px; font-family:\\'JetBrains Mono\\',monospace;
                            border:1px solid rgba(0,255,136,0.25); border-radius:8px;
                            background:rgba(0,255,136,0.04); margin:4px 0;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="color:#00ff88; font-size:13px; font-weight:700;">{hist["symbol"]}</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:12px; font-weight:700;">{hist["timeframe"]}</span>
                  </div>
                  <div style="color:rgba(255,255,255,0.55); font-size:10px; margin-bottom:3px;">
                    период
                  </div>
                  <div style="color:rgba(255,255,255,0.85); font-size:10px; margin-bottom:6px;">
                    {hist["date_from"]} → {hist["date_to"]}
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:6px;
                              color:rgba(255,255,255,0.5); font-size:10px;">
                    {hist["bars"]} баров · {hist["name"]}
                  </div>
                </div>
                \'\'\')
            elif not state["uploaded_files"]:
                ui.label("Нет файлов").style("color: rgba(255,255,255,0.4)")
            else:
                for f in state["uploaded_files"]:
                    ui.label(f["name"]).style(
                        "color: rgba(255,255,255,0.8); font-size: 11px;")'''

# clear_files тоже чистит паспорт
OLD_CLEAR = '''    def clear_files():
        state["uploaded_files"] = []
        update_files_display()
        ui.notify("Очищено", type="info")'''

NEW_CLEAR = '''    def clear_files():
        state["uploaded_files"] = []
        state["loaded_history"] = None   # ''' + MARKER + '''
        update_files_display()
        ui.notify("Очищено", type="info")'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен — пропускаю.")
        return False

    # 1) state
    if STATE_ANCHOR not in src:
        _fail("exchange: не нашёл 'uploaded_files' в state — структура изменилась.")
    src = src.replace(STATE_ANCHOR, STATE_INSERT, 1)

    # 2) handle_upload
    if OLD_UPLOAD not in src:
        _fail("exchange: не нашёл старый handle_upload — структура изменилась.")
    src = src.replace(OLD_UPLOAD, NEW_UPLOAD, 1)

    # 3) update_files_display
    if OLD_FILES_DISPLAY not in src:
        _fail("exchange: не нашёл старый update_files_display — структура изменилась.")
    src = src.replace(OLD_FILES_DISPLAY, NEW_FILES_DISPLAY, 1)

    # 4) clear_files
    if OLD_CLEAR not in src:
        _fail("exchange: не нашёл старый clear_files — структура изменилась.")
    src = src.replace(OLD_CLEAR, NEW_CLEAR, 1)

    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: зарядка истории + карточка-паспорт.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча ui_exchange.py НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  КАМЕНЬ 4·ШАГ 1: ЗАРЯДКА ИСТОРИИ (паспорт)  ·", MARKER)
    print("═" * 62)
    _check_root()

    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Загрузил CSV → под загрузчиком паспорт:")
        print("   тикер · ТФ · период · число баров.")
        print("   Дальше: тумблер тестер/реал + курсор-часы (камень 4 шаг 2).")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
