#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fix_exchange_feed_indent.py
# ─────────────────────────────────────────────────────────────
# ПОЧИНКА: IndentationError в ui_exchange.py (строка ~551).
#
# Патч TESTER_TRADE_FEED_V1 воткнул ветку trade и лишний return
# криво — внутри ветки verdict, с битым отступом, а ветка progress
# уехала вниз и стала недостижимой. Студия не стартует.
#
# Этот скрипт находит покорёженный блок и заменяет его на ПРАВИЛЬНЫЙ,
# где три ветки идут ровно и по очереди:
#   verdict → trade → progress, каждая со своим return.
#
# БЕЗОПАСНО: бэкап рядом. Идемпотентен (если уже починено — выйдет).
# Запуск из корня репы:  python fix_exchange_feed_indent.py
# ─────────────────────────────────────────────────────────────

import sys
import shutil
from pathlib import Path
from datetime import datetime

EXCHANGE = Path("studio/economy/ui_exchange.py")


def _die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def main():
    if not EXCHANGE.exists():
        _die(f"не найден {EXCHANGE} — запусти из корня репы (-2/).")
    src = EXCHANGE.read_text(encoding="utf-8")

    # Битый блок — ровно как сейчас в файле (verdict без return, внутрь
    # вложился trade, потом print, потом висячий return, потом progress).
    broken = (
        '            # \u2500\u2500 \u0420\u0410\u0417\u0412\u0418\u041b\u041a\u0410 (TESTER_TO_CABINET_V1) \u2192 \u0436\u0438\u0440\u043d\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "verdict":\n'
        '                txt = msg.get("text", "")\n'
        '                hint = msg.get("hint", "")\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u0420\u0410\u0417\u0412\u0418\u041b\u041a\u0410",\n'
        '                    "content": f"\U0001f4ca {txt}\\n\u2192 {hint}"})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                # \u2500\u2500 TESTER_TRADE_FEED_V1: \u043b\u0435\u043d\u0442\u0430 \u0441\u0434\u0435\u043b\u043e\u043a \u2192 \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "trade":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u0421\u0414\u0415\u041b\u041a\u0410",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            print(f"[EXCHANGE\u00b7TESTER] {msg}")\n'
        '                return\n'
        '            # \u2500\u2500 \u041f\u0420\u041e\u0413\u0420\u0415\u0421\u0421 \u043f\u0435\u0440\u0435\u0431\u043e\u0440\u0430 (TESTER_TO_CABINET_V1) \u2192 \u043b\u0451\u0433\u043a\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "progress":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u00b7\u00b7\u00b7",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            print(f"[EXCHANGE\u00b7TESTER] {msg}")\n'
    )

    fixed = (
        '            # \u2500\u2500 \u0420\u0410\u0417\u0412\u0418\u041b\u041a\u0410 (TESTER_TO_CABINET_V1) \u2192 \u0436\u0438\u0440\u043d\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "verdict":\n'
        '                txt = msg.get("text", "")\n'
        '                hint = msg.get("hint", "")\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u0420\u0410\u0417\u0412\u0418\u041b\u041a\u0410",\n'
        '                    "content": f"\U0001f4ca {txt}\\n\u2192 {hint}"})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            # \u2500\u2500 TESTER_TRADE_FEED_V1: \u043b\u0435\u043d\u0442\u0430 \u0441\u0434\u0435\u043b\u043e\u043a \u2192 \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "trade":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u0421\u0414\u0415\u041b\u041a\u0410",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            # \u2500\u2500 \u041f\u0420\u041e\u0413\u0420\u0415\u0421\u0421 \u043f\u0435\u0440\u0435\u0431\u043e\u0440\u0430 (TESTER_TO_CABINET_V1) \u2192 \u043b\u0451\u0433\u043a\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 \u0447\u0430\u0442 \u2500\u2500\n'
        '            if isinstance(msg, dict) and msg.get("type") == "progress":\n'
        '                state["chat_history"].append({\n'
        '                    "role": "assistant", "agent": "\u00b7\u00b7\u00b7",\n'
        '                    "content": msg.get("text", "")})\n'
        '                try:\n'
        '                    update_chat_display()\n'
        '                except Exception:\n'
        '                    pass\n'
        '                return\n'
        '            print(f"[EXCHANGE\u00b7TESTER] {msg}")\n'
    )

    if broken not in src:
        # уже починено или блок другой
        if fixed in src:
            print("✅ блок уже починен — выхожу.")
            return
        _die("битый блок не найден в точности. Возможно, файл уже правился "
             "вручную. Покажи строки 535-560 ui_exchange.py — подскажу точечно.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = EXCHANGE.with_name(f"{EXCHANGE.stem}.bak_fix_{stamp}{EXCHANGE.suffix}")
    shutil.copy2(EXCHANGE, backup)
    print(f"💾 бэкап: {backup.name}")

    src = src.replace(broken, fixed, 1)
    EXCHANGE.write_text(src, encoding="utf-8")

    # проверим, что файл теперь парсится
    import ast
    try:
        ast.parse(src)
        print("✅ ui_exchange.py починен — синтаксис валиден, студия запустится.")
        print("   три ветки (verdict/trade/progress) идут ровно, каждая со своим return.")
    except SyntaxError as e:
        print(f"⚠️ заменил, но синтаксис всё ещё ругается: {e}")
        print(f"   откати: cp {backup.name} {EXCHANGE.name}")


if __name__ == "__main__":
    main()
