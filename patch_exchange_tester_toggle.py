#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: КАМЕНЬ 4·ШАГ 2b — ТУМБЛЕР ТЕСТЕР/РЕАЛ + СТОП на БИРЖЕ
# Маркер: EXCHANGE_TESTER_TOGGLE_V1
# Дата: 2026-06-20 · Брат (Claude) + Шеф
#
# ЗАМЫСЕЛ (Шеф): «есть кнопка рынок, а есть переключатель тестер/реал».
# Тумблер решает, ОТКУДА РЫНОК берёт время:
#   РЕАЛ   — живой бар из MT5 (как сейчас). СТОП не нужен — бар один.
#   ТЕСТЕР — заряженная история (паспорт из EXCHANGE_HISTORY_LOAD_V1)
#            перебирается бар за баром через готовый run_tester (он сам
#            ставит кран на CSV под курсором). Появляются поле «баров»
#            и кнопка СТОП — рычаги перебора. Это экспресс-жизнь.
#
# ВИДИМОСТЬ: реал → только РЫНОК. тестер → РЫНОК + поле баров + СТОП.
# Тумблер сам прячет/показывает (Шеф: «в реал и кнопка стоп не нужна»).
#
# КАК ГОНИТ ТЕСТЕР. Не дублируем круг Совета и не городим кран на бирже —
# кран живёт ВНУТРИ run_tester (TESTER_HANDLES_V1 дал ему руль). Биржа
# лишь зовёт его по заряженному CSV, прокинув:
#   on_progress → строки хода в чат биржи (агент SYSTEM)
#   should_stop → лямбда, читающая флаг state["stop_requested"]
#   n_signals   → из поля «баров» (сколько срабатываний ловить за заход)
# Тяжёлый вызов — в потоке (run_in_executor), UI не виснет.
#
# ДВА КАСАНИЯ в ui_exchange.py:
#   1. state — mode/bars_to_live/stop_requested/tester_running.
#   2. функции run_tester_session + request_stop + рендер тулбара
#      (тумблер, поле, СТОП). Кнопка РЫНОК → диспетчер: реал→run_market,
#      тестер→run_tester_session.
#
# ИДЕМПОТЕНТНО: маркер, бэкап, py_compile. Запуск из корня репы:
#   python patch_exchange_tester_toggle.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

MARKER = "EXCHANGE_TESTER_TOGGLE_V1"
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


# ── 1. state-флаги ──
STATE_ANCHOR = '        "running": False,          # идёт прогон РЫНОК\n'
STATE_INSERT = (
    '        "running": False,          # идёт прогон РЫНОК\n'
    '        "mode": "real",            # тумблер: real | tester  # ' + MARKER + '\n'
    '        "bars_to_live": 1,         # тестер: сколько срабатываний ловить за заход\n'
    '        "stop_requested": False,   # кнопка СТОП взвела флаг\n'
    '        "tester_running": False,   # идёт перебор истории\n'
)

# ── 2. Функции тумблера/перебора/стопа — перед `async def run_market` ──
SESSION_FUNCS = '''    # ════════════════════════════════════════════════════════
    # ТУМБЛЕР ТЕСТЕР/РЕАЛ + ПЕРЕБОР ИСТОРИИ + СТОП.  # ''' + MARKER + '''
    # ════════════════════════════════════════════════════════

    def _tester_refs():
        """Ссылки на поле баров и кнопку СТОП — для показа/скрытия."""
        return toolbar_refs

    def set_mode(mode: str):
        """Переключить тестер/реал. Прячет/показывает поле баров и СТОП."""
        state["mode"] = mode
        is_tester = (mode == "tester")
        # видимость рычагов тестера
        for key in ("bars_input", "stop_btn", "bars_label"):
            el = toolbar_refs.get(key)
            if el:
                el.style(f"display: {'flex' if is_tester else 'none'}")
        # подсветка кнопок режима
        for key, m in (("mode_real", "real"), ("mode_tester", "tester")):
            el = toolbar_refs.get(key)
            if el:
                active = (m == mode)
                el.style(
                    "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                    "cursor:pointer;" + (
                        "background:rgba(0,255,136,0.15);color:#00ff88;"
                        "border:1px solid rgba(0,255,136,0.4);"
                        if active else
                        "background:rgba(255,255,255,0.03);color:rgba(255,255,255,0.45);"
                        "border:1px solid rgba(255,255,255,0.08);"
                    )
                )
        ui.notify(f"Режим: {'ТЕСТЕР (история)' if is_tester else 'РЕАЛ (живой рынок)'}",
                  type="info")

    def request_stop():
        """Кнопка СТОП — взводит флаг, перебор увидит его на след. кандидате."""
        if not state.get("tester_running"):
            ui.notify("Перебор не идёт", type="warning")
            return
        state["stop_requested"] = True
        ui.notify("⏸ СТОП — останавливаю на следующем кандидате...", type="info")

    async def run_tester_session():
        """
        Режим ТЕСТЕР: гонит ЗАРЯЖЕННУЮ историю через готовый run_tester.
        Кран и круг Совета — внутри него. Биржа даёт путь, репорт и стоп.
        """
        hist = state.get("loaded_history")
        if not hist:
            ui.notify("Сначала загрузи историю в загрузчик слева", type="warning")
            return
        if state.get("tester_running"):
            ui.notify("Перебор уже идёт...", type="warning")
            return

        state["tester_running"] = True
        state["stop_requested"] = False
        symbol = hist.get("symbol", "XAUUSD")
        tf     = hist.get("timeframe", "H4")
        path   = hist.get("path", "")
        n      = int(state.get("bars_to_live", 1) or 1)

        state["chat_history"].append({
            "role": "assistant", "agent": "SYSTEM",
            "content": f"▶ ТЕСТЕР: гоню {symbol} {tf} · ловлю {n} срабатываний. "
                       f"СТОП — прервать."})
        update_chat_display()
        ui.notify(f"▶ Тестер: {symbol} {tf}", type="info")

        # callbacks: ход в чат, стоп из флага
        def _on_progress(msg):
            # лёгкий репорт — не плодим тяжёлый UI на каждый бар
            print(f"[EXCHANGE·TESTER] {msg}")

        def _should_stop():
            return state.get("stop_requested", False)

        try:
            from studio.modules.trading.tester_express import run_tester
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_tester(
                    csv_path=path, symbol=symbol, timeframe=tf,
                    n_signals=n, on_progress=_on_progress,
                    should_stop=_should_stop,
                )
            )
        except Exception as e:
            ui.notify(f"Тестер упал: {e}", type="negative")
            state["chat_history"].append({
                "role": "assistant", "agent": "SYSTEM",
                "content": f"⚠️ Тестер упал: {e}"})
            update_chat_display()
        finally:
            state["tester_running"] = False
            stopped = state.get("stop_requested", False)
            state["stop_requested"] = False

        tail = "⏸ остановлен по СТОП" if stopped else "✓ заход прожит"
        state["chat_history"].append({
            "role": "assistant", "agent": "SYSTEM",
            "content": f"{tail}. Совет отработал историю — отчёт в консоли/файле. "
                       f"Можешь уйти разгулять агентов в кабинет и вернуться."})
        update_chat_display()
        # обновим картину агентов после перебора
        update_avatar_states()
        ui.notify(tail, type="positive" if not stopped else "warning")

    async def market_dispatch():
        """Кнопка РЫНОК → по тумблеру: реал=живой бар, тестер=перебор истории."""
        if state.get("mode") == "tester":
            await run_tester_session()
        else:
            await run_market()

'''

SESSION_ANCHOR = "    async def run_market():\n"

# ── 3. Тулбар: тумблер + поле баров + СТОП; РЫНОК → market_dispatch ──
OLD_TOOLBAR = '''                with ui.element("div").classes("stage-toolbar").style("flex-shrink:0;"):
                    with ui.element("div").style("display:flex; gap:6px; align-items:center;"):
                        ui.button("📡 РЫНОК", on_click=run_market).props("flat").style(\'\'\'
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10)) !important;
                            border: 1px solid rgba(0,255,136,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        \'\'\')'''

NEW_TOOLBAR = '''                with ui.element("div").classes("stage-toolbar").style("flex-shrink:0;"):
                    with ui.element("div").style("display:flex; gap:6px; align-items:center;"):
                        ui.button("📡 РЫНОК", on_click=market_dispatch).props("flat").style(\'\'\'
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10)) !important;
                            border: 1px solid rgba(0,255,136,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        \'\'\')
                        # ── ТУМБЛЕР ТЕСТЕР/РЕАЛ ──  # ''' + MARKER + '''
                        toolbar_refs["mode_real"] = ui.element("div").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(0,255,136,0.15);color:#00ff88;"
                            "border:1px solid rgba(0,255,136,0.4);")
                        toolbar_refs["mode_real"].on("click", lambda: set_mode("real"))
                        with toolbar_refs["mode_real"]:
                            ui.html("РЕАЛ")
                        toolbar_refs["mode_tester"] = ui.element("div").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(255,255,255,0.03);"
                            "color:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.08);")
                        toolbar_refs["mode_tester"].on("click", lambda: set_mode("tester"))
                        with toolbar_refs["mode_tester"]:
                            ui.html("ТЕСТЕР")
                        # ── ПОЛЕ БАРОВ (только тестер) ──
                        toolbar_refs["bars_label"] = ui.element("div").style(
                            "display:none;align-items:center;gap:5px;")
                        with toolbar_refs["bars_label"]:
                            ui.label("ловить:").style(
                                "color:rgba(255,255,255,0.45);font-size:11px;")
                        toolbar_refs["bars_input"] = ui.element("div").style(
                            "display:none;align-items:center;")
                        with toolbar_refs["bars_input"]:
                            _bi = ui.number(value=1, min=1, max=999, format="%d").props(
                                "dense borderless").style(
                                "width:60px;font-family:JetBrains Mono;font-size:12px;"
                                "color:rgba(0,204,255,0.9);")
                            _bi.on("update:model-value",
                                   lambda e: state.update({"bars_to_live": int(e.args or 1)}))
                        # ── КНОПКА СТОП (только тестер) ──
                        toolbar_refs["stop_btn"] = ui.element("div").style(
                            "display:none;align-items:center;padding:6px 14px;border-radius:7px;"
                            "font-size:12px;font-weight:700;cursor:pointer;"
                            "background:rgba(255,80,80,0.12);color:#ff5050;"
                            "border:1px solid rgba(255,80,80,0.4);")
                        toolbar_refs["stop_btn"].on("click", lambda: request_stop())
                        with toolbar_refs["stop_btn"]:
                            ui.html("⏸ СТОП")'''


def patch_exchange() -> bool:
    src = EXCHANGE.read_text(encoding="utf-8")
    if MARKER in src:
        print("✅ ui_exchange.py уже пропатчен (тумблер) — пропускаю.")
        return False

    # state
    if STATE_ANCHOR not in src:
        _fail("exchange: не нашёл 'running' в state — структура изменилась.")
    src = src.replace(STATE_ANCHOR, STATE_INSERT, 1)

    # toolbar_refs объявим рядом с другими ref-словарями.
    # Якорь — строка создания первого ref-словаря.
    refs_anchor = '    chat_log_ref = {"element": None}\n'
    if refs_anchor not in src:
        _fail("exchange: не нашёл ref-словари — структура изменилась.")
    src = src.replace(
        refs_anchor,
        refs_anchor + '    toolbar_refs = {}   # тумблер/поле/СТОП  # ' + MARKER + '\n',
        1
    )

    # функции сессии — перед run_market
    if SESSION_ANCHOR not in src:
        _fail("exchange: не нашёл 'async def run_market' — структура изменилась.")
    src = src.replace(SESSION_ANCHOR, SESSION_FUNCS + SESSION_ANCHOR, 1)

    # тулбар
    if OLD_TOOLBAR not in src:
        _fail("exchange: не нашёл тулбар с кнопкой РЫНОК — структура изменилась.")
    src = src.replace(OLD_TOOLBAR, NEW_TOOLBAR, 1)

    _backup(EXCHANGE)
    EXCHANGE.write_text(src, encoding="utf-8")
    print("✅ ui_exchange.py пропатчен: тумблер тестер/реал + поле баров + СТОП.")
    return True


def _verify_compiles():
    try:
        py_compile.compile(str(EXCHANGE), doraise=True)
    except py_compile.PyCompileError as e:
        _fail(f"После патча ui_exchange.py НЕ компилируется:\n{e}")
    print("🧪 Песочница: ui_exchange.py компилируется.")


def main():
    print("═" * 62)
    print("  КАМЕНЬ 4·ШАГ 2b: ТУМБЛЕР ТЕСТЕР/РЕАЛ + СТОП  ·", MARKER)
    print("═" * 62)
    _check_root()

    if patch_exchange():
        _verify_compiles()
        print("─" * 62)
        print("✅ ГОТОВО. Тумблер на бирже:")
        print("   РЕАЛ   → РЫНОК = живой бар (как было), СТОП скрыт.")
        print("   ТЕСТЕР → РЫНОК = перебор заряженной истории, есть поле баров + СТОП.")
        print("   Кран и круг Совета — внутри run_tester (не дублируем).")
        print("   Это сердце экспресс-жизни: прогнал кусок → СТОП → разгулял → дальше.")
    else:
        print("─" * 62)
        print("ℹ️  Уже было пропатчено ранее — ничего не менял.")


if __name__ == "__main__":
    main()
