#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: СПИСОК АКТИВОВ на БИРЖЕ v2 (поверх фикса)
# Маркер: EXCHANGE_ASSET_LIST_V1
# Дата: 2026-06-21 · Брат (Claude) + Шеф
#
# Версия для main, где УЖЕ накатан EXCHANGE_LOAD_FIX_V1 (словесные ТФ +
# reset аплоадера на месте). Поэтому парсер и upload-widget НЕ трогаем —
# только превращаем одну историю в кликабельный СПИСОК:
#   loaded_history(одна) → loaded_assets[](полка) + active_asset(индекс).
#   Клик по строке активирует (НЕ запускает). РЫНОК гонит активного.
#   Загрузка добавляет в полку (не затирает); дубль по пути — обновляет.
#
# ПЯТЬ КАСАНИЙ в ui_exchange.py:
#   1. state: loaded_assets[] + active_asset
#   2. update_files_display: кликабельный список строк
#   3. handle_upload (хвост): добавить в полку, новый — активный
#   4. clear_files: чистит полку
#   5. run_tester_session: гонит активного
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_asset_list_v2.py
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
        _fail(f"Не вижу {EXCHANGE}. Запускай из КОРНЯ репы.")


# 1. state
OLD_STATE = '        "loaded_history": None,    # паспорт заряженной истории (тикер/тф/период)  # EXCHANGE_HISTORY_LOAD_V1\n'
NEW_STATE = (
    '        "loaded_assets": [],       # полка заряженных активов  # ' + MARKER + '\n'
    '        "active_asset": None,      # индекс активного актива\n'
)

# 2. update_files_display — целиком тело
OLD_DISPLAY = '''        if not files_ref["element"]:
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

NEW_DISPLAY = '''        if not files_ref["element"]:
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

# set_active — добавим ПЕРЕД def update_files_display
OLD_DISPLAY_DEF = "    def update_files_display():\n"
NEW_DISPLAY_DEF = (
    '    def set_active(i):\n'
    '        """Клик по активу — активировать (НЕ запускать)."""  # ' + MARKER + '\n'
    '        assets = state.get("loaded_assets", [])\n'
    '        if 0 <= i < len(assets):\n'
    '            state["active_asset"] = i\n'
    '            update_files_display()\n'
    '            a = assets[i]\n'
    '            ui.notify(f"Активен: {a[\'symbol\']} {a[\'timeframe\']}", type="info")\n'
    '\n'
    '    def update_files_display():\n'
)

# 3. handle_upload хвост
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
            state["active_asset"] = len(assets) - 1
        update_files_display()
        ui.notify(
            f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")'''

# 4. clear_files
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

# 5. run_tester_session
OLD_TESTER = '''        hist = state.get("loaded_history")
        if not hist:
            ui.notify("Сначала загрузи историю в загрузчик слева", type="warning")
            return'''

NEW_TESTER = '''        # Гоним АКТИВНЫЙ актив из полки (клик его выбрал).  # ''' + MARKER + '''
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
        (OLD_DISPLAY_DEF, NEW_DISPLAY_DEF, "def update_files_display (set_active)"),
        (OLD_DISPLAY, NEW_DISPLAY, "тело update_files_display"),
        (OLD_UPLOAD_TAIL, NEW_UPLOAD_TAIL, "хвост handle_upload"),
        (OLD_CLEAR, NEW_CLEAR, "clear_files"),
        (OLD_TESTER, NEW_TESTER, "run_tester_session"),
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
        _fail(f"После патча НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  СПИСОК АКТИВОВ на БИРЖЕ v2 (поверх фикса)  ·", MARKER)
    print("═" * 62)
    _check_root()
    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Полка активов: тикер·ТФ·дата. Клик активирует.")
        print("   РЫНОК (тестер) гонит активного. Загрузка добавляет в полку.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее.")


if __name__ == "__main__":
    main()
