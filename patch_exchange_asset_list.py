#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: СПИСОК АКТИВОВ на БИРЖЕ (полка историй + клик-активация)
# Маркер: EXCHANGE_ASSET_LIST_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# ЗАМЫСЕЛ (Шеф): «список активов под загрузчиком, голый тикер·тф·дата,
# клик по активу его активирует (НЕ запускает), РЫНОК гонит активного».
#
# Идёт ПОВЕРХ зарядки+тумблера (в main). Вбирает в себя и фикс:
#   · словесные ТФ MT5 (Daily/Weekly/Monthly/Hourly) — EURUSDDaily→D1
#   · гашение висючки аплоадера (reset) — под загрузчиком только список
# Поэтому отдельный patch_exchange_load_fix НЕ нужен (растворён здесь).
#
# ЧТО МЕНЯЕТ:
#   1. state: loaded_history(одна) → loaded_assets[](список) + active_asset(индекс).
#   2. handle_upload: ДОБАВЛЯЕТ актив в список (не затирает), словесные ТФ,
#      reset аплоадера, делает новый актив активным.
#   3. update_files_display: рисует кликабельный СПИСОК строк
#      «тикер · ТФ · дата». Активный подсвечен. Клик → set_active(i).
#   4. set_active(i): помечает активный, перерисовывает.
#   5. clear_files: чистит список.
#   6. run_tester_session: гонит АКТИВНЫЙ актив (не последний).
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_asset_list.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_ASSET_LIST_V1"
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
        _fail("Нужна зарядка EXCHANGE_HISTORY_LOAD_V1 в файле — её нет.")
    if "EXCHANGE_TESTER_TOGGLE_V1" not in src:
        _fail("Нужен тумблер EXCHANGE_TESTER_TOGGLE_V1 в файле — его нет.")


# ── 1. state: список + активный индекс ──
OLD_STATE = '        "loaded_history": None,    # паспорт заряженной истории (тикер/тф/период)  # EXCHANGE_HISTORY_LOAD_V1\n'
NEW_STATE = (
    '        "loaded_assets": [],       # полка заряженных активов (список паспортов)  # ' + MARKER + '\n'
    '        "active_asset": None,      # индекс активного актива в loaded_assets\n'
)

# ── 2. парсер: словесные ТФ + коды ──
OLD_PARSER = '''    def _parse_symbol_tf(filename: str):
        """EURUSDH1.csv → ('EURUSD','H1'). Код ТФ ищем в хвосте имени
        (длинные раньше: H12≠H1, MN1≠M1). Остаток спереди — тикер."""
        stem = filename.rsplit(".", 1)[0].upper().strip()
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"'''

NEW_PARSER = '''    _WORD_TFS = {"MONTHLY": "MN1", "WEEKLY": "W1", "DAILY": "D1", "HOURLY": "H1"}  # ''' + MARKER + '''

    def _parse_symbol_tf(filename: str):
        """EURUSDDaily.csv→('EURUSD','D1'); EURUSDH1.csv→('EURUSD','H1').
        MT5 пишет период СЛОВОМ (Daily/Weekly/Monthly/Hourly) ИЛИ кодом."""
        stem = filename.rsplit(".", 1)[0].upper().strip()
        for word, tf in sorted(_WORD_TFS.items(), key=lambda x: -len(x[0])):
            if stem.endswith(word):
                return stem[:-len(word)].rstrip("_- "), tf
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"'''

# ── 3. update_files_display: кликабельный список ──
OLD_DISPLAY = '''    def update_files_display():
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            hist = state.get("loaded_history")  # EXCHANGE_HISTORY_LOAD_V1
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

NEW_DISPLAY = '''    def set_active(i):
        """Клик по активу — активировать (НЕ запускать). Подсветить, перерисовать."""  # ''' + MARKER + '''
        assets = state.get("loaded_assets", [])
        if 0 <= i < len(assets):
            state["active_asset"] = i
            update_files_display()
            a = assets[i]
            ui.notify(f"Активен: {a['symbol']} {a['timeframe']}", type="info")

    def update_files_display():
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            assets = state.get("loaded_assets", [])  # ''' + MARKER + '''
            if not assets:
                ui.label("Нет активов").style("color: rgba(255,255,255,0.4); font-size:11px;")
            else:
                active = state.get("active_asset")
                for i, a in enumerate(assets):
                    is_active = (i == active)
                    row = ui.element("div").style(
                        "padding:7px 10px; margin:3px 0; border-radius:7px; cursor:pointer; "
                        "font-family:'JetBrains Mono',monospace; "
                        + ("background:rgba(0,255,136,0.10); border:1px solid rgba(0,255,136,0.45);"
                           if is_active else
                           "background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.07);"))
                    row.on("click", lambda _, idx=i: set_active(idx))
                    with row:
                        ui.html(
                            f\'\'\'<div style="display:flex;justify-content:space-between;align-items:center;">
                              <span style="color:{'#00ff88' if is_active else 'rgba(255,255,255,0.85)'};
                                           font-size:12px;font-weight:700;">{a["symbol"]}</span>
                              <span style="color:rgba(0,204,255,0.9);font-size:11px;font-weight:700;">{a["timeframe"]}</span>
                            </div>
                            <div style="color:rgba(255,255,255,0.5);font-size:9px;margin-top:2px;">
                              {a["date_from"]} → {a["date_to"]} · {a["bars"]}
                            </div>\'\'\')'''

# ── 4. handle_upload: добавляет в список + reset ──
OLD_UPLOAD_TAIL = '''        state["loaded_history"] = passport
        # в список тоже кладём (совместимость со старым отображением)
        state["uploaded_files"] = [{"name": name}]
        update_files_display()
        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")'''

NEW_UPLOAD_TAIL = '''        # ДОБАВЛЯЕМ в полку (не затираем). Дубль по пути — обновляем.  # ''' + MARKER + '''
        assets = state.setdefault("loaded_assets", [])
        existing = next((k for k, x in enumerate(assets)
                         if x.get("path") == passport["path"]), None)
        if existing is not None:
            assets[existing] = passport
            state["active_asset"] = existing
        else:
            assets.append(passport)
            state["active_asset"] = len(assets) - 1   # новый сразу активен
        update_files_display()
        # Гасим висючку аплоадера — под загрузчиком только список.  # ''' + MARKER + '''
        _up = files_ref.get("uploader")
        if _up:
            try:
                _up.reset()
            except Exception:
                pass
        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")'''

# ── 5. clear_files ──
OLD_CLEAR = '''    def clear_files():
        state["uploaded_files"] = []
        state["loaded_history"] = None   # EXCHANGE_HISTORY_LOAD_V1
        update_files_display()
        ui.notify("Очищено", type="info")'''

NEW_CLEAR = '''    def clear_files():
        state["uploaded_files"] = []
        state["loaded_assets"] = []      # ''' + MARKER + '''
        state["active_asset"] = None
        update_files_display()
        ui.notify("Очищено", type="info")'''

# ── 6. аплоадер получает ref (для reset) ──
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

# ── 7. run_tester_session: гонит АКТИВНЫЙ актив ──
OLD_TESTER_HIST = '''        hist = state.get("loaded_history")
        if not hist:
            ui.notify("Сначала загрузи историю в загрузчик слева", type="warning")
            return'''

NEW_TESTER_HIST = '''        # Гоним АКТИВНЫЙ актив из полки (клик его выбрал).  # ''' + MARKER + '''
        assets = state.get("loaded_assets", [])
        ai = state.get("active_asset")
        hist = assets[ai] if (assets and ai is not None and 0 <= ai < len(assets)) else None
        if not hist:
            ui.notify("Загрузи актив и кликни по нему в списке слева", type="warning")
            return'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (asset-list) — пропускаю.")
        return False

    pairs = [
        (OLD_STATE, NEW_STATE, "state"),
        (OLD_PARSER, NEW_PARSER, "парсер"),
        (OLD_DISPLAY, NEW_DISPLAY, "update_files_display"),
        (OLD_UPLOAD_TAIL, NEW_UPLOAD_TAIL, "хвост handle_upload"),
        (OLD_CLEAR, NEW_CLEAR, "clear_files"),
        (OLD_UPLOAD_WIDGET, NEW_UPLOAD_WIDGET, "ui.upload"),
        (OLD_TESTER_HIST, NEW_TESTER_HIST, "run_tester_session"),
    ]
    for old, new, label in pairs:
        if old not in src:
            _fail(f"exchange: не нашёл блок '{label}' — структура изменилась.")
        src = src.replace(old, new, 1)

    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: список активов + клик-активация.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча ui_exchange.py НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  СПИСОК АКТИВОВ на БИРЖЕ (полка + клик)  ·", MARKER)
    print("═" * 62)
    _check_root()

    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Под загрузчиком — список активов:")
        print("   тикер · ТФ · дата. Клик активирует (подсветка), НЕ гонит.")
        print("   РЫНОК (тестер) гонит АКТИВНЫЙ. Висючка гаснет. EURUSDDaily→D1.")
        print("   Загрузка добавляет в полку, не затирает.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
