#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_exchange_panikyor.py — кнопка РЫНОК будит Паникёра после Моржа

ЧТО ЧИНИТ:
  Паникёр оживлён (мотор panikyor_live.py + промт + контракт), но кнопка
  РЫНОК его НЕ зовёт — в ui_exchange он только иконка в хедере. Цепочка
  Искра → Морж обрывается, Паникёр не запускается.

ЧТО ДЕЛАЕТ:
  После успешного прогона Моржа (внутри затвора t1 in DETECTED/CONFIRMED)
  зовёт run_panikyor, кладёт его сигнал в state, пишет в чат. Цепочка
  становится Искра → Морж → Паникёр. Тот же затвор: Паникёр будится только
  при сигнале Искры (он часть блока Моржа).

  Паникёр наследует этаж Искры сам (внутри run_panikyor), как Морж.

БЕЗОПАСНОСТЬ: идемпотентен (маркер), бэкап .bak, якорный replace, CRLF-safe.
ПУТЬ: ui_exchange.py лежит в studio/economy/ (не economy/).
"""
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/economy/ui_exchange.py")
MARKER = "EXCHANGE_PANIKYOR"

# Якорь — конец блока Моржа (его «смолчал»), перед подсветкой пузырьков.
OLD = '''            else:
                ui.notify("🦭 Морж смолчал (нет данных или сбой)", type="warning")

    # ── Подсветка активного пузырька ─────────────────────────'''

NEW = '''            else:
                ui.notify("🦭 Морж смолчал (нет данных или сбой)", type="warning")

            # ── ''' + MARKER + ''': Паникёр после Моржа (та же цепочка/затвор) ──
            # Паникёр чует толпу структурой (окна MFI). Наследует этаж Искры сам.
            ui.notify("😱 Бужу Паникёра — мерит толпу...", type="info")
            try:
                from studio.modules.trading.panikyor_live import run_panikyor
                pr = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_panikyor(symbol="XAUUSD", timeframe="H4"))
            except Exception as e:
                ui.notify(f"Паникёр не проснулся: {e}", type="negative")
                pr = {"ok": False}

            if pr.get("ok"):
                psig = pr.get("signal", {})
                state["reports"]["A03"] = pr.get("narrative", "") or pr.get("raw", "")
                state["panic_signal"] = psig
                state["panic_stats"]  = pr.get("stats", {})
                state["panic_market"] = pr.get("market", {})
                state["panic_last_run"] = {
                    "narrative": pr.get("narrative", ""),
                    "signal":    psig,
                    "market":    pr.get("market", {}),
                }
                state["chat_history"].append({
                    "role": "assistant", "agent": "A03",
                    "content": (f"😱 Толпа: {psig.get('panic_phase','—')}. "
                                f"{psig.get('crowd_sentiment','')} Отчёт справа.")})
                update_chat_display()
                update_avatar_states()
                ui.notify(f"😱 Паникёр: {psig.get('panic_phase','—')}", type="positive")
            else:
                ui.notify("😱 Паникёр смолчал (нет данных или сбой)", type="warning")

    # ── Подсветка активного пузырька ─────────────────────────'''


def main():
    if not TARGET.exists():
        print(f"❌ Не найден файл: {TARGET}")
        print("   Проверь путь: studio/economy/ui_exchange.py")
        return
    src = TARGET.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"✅ Уже пропатчено (маркер {MARKER}) — ничего не делаю.")
        return

    if OLD in src:
        new_src = src.replace(OLD, NEW, 1)
    else:
        old_cr = OLD.replace("\n", "\r\n")
        if old_cr in src:
            new_src = src.replace(old_cr, NEW.replace("\n", "\r\n"), 1)
        else:
            print("❌ Якорь не найден (конец блока Моржа).")
            print("   Возможно ui_exchange менялся. Покажи блок вокруг 'Морж смолчал' — поправлю.")
            return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(TARGET.suffix + f".bak_{stamp}")
    shutil.copy2(TARGET, bak)
    print(f"💾 Бэкап: {bak.name}")
    TARGET.write_text(new_src, encoding="utf-8")
    print("✅ Кнопка РЫНОК теперь будит Паникёра после Моржа.")
    print("   Цепочка: Искра → Морж → Паникёр (при сигнале Искры).")


if __name__ == "__main__":
    main()
