#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ПАТЧ: patch_traders_button.py
# Совет садится за стол — три трейдера в живой кнопке РЫНОК
# Версия: 1.0 · 2026-06-19 · Брат (Claude) + Шеф
#
# ЧТО ДЕЛАЕТ (идемпотентно, маркер + авто-бэкап):
#   Чинит хвост из мастер-дока: кнопка РЫНОК будила цепочку до Архивариуса
#   и обрывалась. Теперь после Архивариуса за стол садятся ТРОЕ трейдеров
#   (Брут A06 + Авантюрист A07 + Консерватор A08) — Совет оживает вживую,
#   не только в тестере.
#
#   ВРЕЗКА 1 (кнопка): после Архивариуса зовём run_brut/run_avan/run_cons,
#     кладём вердикты в отчёт + чат. Молчание (REJECTED) — норма (§1f).
#   ВРЕЗКА 2 (чат-пузырьки): A06/A07/A08 в диспетчере чата получают
#     chat_with_brut/avan/cons — пузырьки трейдеров заговорили.
#
# Файл правится: studio/economy/ui_exchange.py
# Требует, чтобы avan_live.py / cons_live.py уже лежали (patch_avan_cons).
# Запуск из КОРНЯ репы:  python patch_traders_button.py
# ─────────────────────────────────────────────────────────────
import shutil, sys, py_compile
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
UI = ROOT / "studio" / "economy" / "ui_exchange.py"

BTN_ANCHOR = '            else:\n                ui.notify("📚 Архивариус смолчал (нет данных или сбой)", type="warning")\n'

BTN_INJECT = '\n            # ═══════════════════════════════════════════════════\n            # СОВЕТ САДИТСЯ ЗА СТОЛ — три трейдера (A06/A07/A08)\n            # [TRADERS врезаны патчем patch_traders_button]\n            # ───────────────────────────────────────────────────\n            # Стол накрыт (пять сенсоров записали факты в trading_state).\n            # Трейдеры читают шину САМИ (_read_table в своих движках) —\n            # UI ничего не передаёт. Зовём по очереди, кладём вердикт в\n            # отчёт + чат. Молчание (REJECTED) — норма, каждый ждёт свою\n            # станцию (§1f, Закон Дежурства). Не гасим прогон молчанием.\n            for tr in (\n                {"id": "A06", "icon": "🪨", "name": "Брут",\n                 "run": "run_brut", "mod": "brut_live", "pre": "brut",\n                 "last": "brut_last_run"},\n                {"id": "A07", "icon": "🎲", "name": "Авантюрист",\n                 "run": "run_avan", "mod": "avan_live", "pre": "avan",\n                 "last": "avan_last_run"},\n                {"id": "A08", "icon": "⚖️", "name": "Консерватор",\n                 "run": "run_cons", "mod": "cons_live", "pre": "cons",\n                 "last": "cons_last_run"},\n            ):\n                ui.notify(f"{tr[\'icon\']} Бужу — {tr[\'name\']} садится за стол...",\n                          type="info")\n                try:\n                    import importlib\n                    _mod = importlib.import_module(\n                        f"studio.modules.trading.{tr[\'mod\']}")\n                    _run = getattr(_mod, tr["run"])\n                    rt = await asyncio.get_event_loop().run_in_executor(\n                        None, lambda _r=_run: _r(symbol="XAUUSD", timeframe="H4"))\n                except Exception as e:\n                    ui.notify(f"{tr[\'icon\']} {tr[\'name\']} не сел: {e}",\n                              type="negative")\n                    continue\n\n                if not rt.get("ok"):\n                    ui.notify(f"{tr[\'icon\']} {tr[\'name\']}: "\n                              f"{rt.get(\'error\',\'сбой\')}", type="warning")\n                    continue\n\n                tsig = rt.get("signal", {})\n                pre  = tr["pre"]\n                state["reports"][tr["id"]] = (\n                    rt.get("narrative", "") or rt.get("raw", ""))\n                state[f"{pre}_signal"] = tsig\n                state[f"{pre}_stats"]  = rt.get("stats", {})\n                state[tr["last"]] = {\n                    "narrative": rt.get("narrative", ""),\n                    "signal":    tsig,\n                    "market":    rt.get("market", {}),\n                }\n                verdict = tsig.get(f"{pre}_verdict", "—")\n                if verdict == "APPROVED":\n                    line = (f"{tr[\'icon\']} {tr[\'name\']}: ВХОД "\n                            f"{tsig.get(f\'{pre}_direction\',\'\')} · "\n                            f"вход {tsig.get(f\'{pre}_entry\',\'—\')} · "\n                            f"стоп {tsig.get(f\'{pre}_stop\',\'—\')} · "\n                            f"лот {tsig.get(f\'{pre}_lot\',\'—\')}. Отчёт справа.")\n                    ui.notify(f"{tr[\'icon\']} {tr[\'name\']}: ВХОД "\n                              f"{tsig.get(f\'{pre}_direction\',\'\')}", type="positive")\n                else:\n                    line = (f"{tr[\'icon\']} {tr[\'name\']}: пас "\n                            f"({tsig.get(f\'{pre}_reason\',\'—\')}). Отчёт справа.")\n                    ui.notify(f"{tr[\'icon\']} {tr[\'name\']}: пас", type="info")\n                state["chat_history"].append({\n                    "role": "assistant", "agent": tr["id"], "content": line})\n                update_chat_display()\n                update_avatar_states()\n'

CHAT_ANCHOR = '        if agent_id != "A01":\n            state["chat_history"].append({\n'

CHAT_INJECT = '        # [TRADERS CHAT врезаны патчем patch_traders_button]\n        if agent_id in ("A06", "A07", "A08"):\n            _tmap = {\n                "A06": ("brut_live", "chat_with_brut", "brut_last_run", "🪨", "Брут"),\n                "A07": ("avan_live", "chat_with_avan", "avan_last_run", "🎲", "Авантюрист"),\n                "A08": ("cons_live", "chat_with_cons", "cons_last_run", "⚖️", "Консерватор"),\n            }\n            _mod_name, _fn_name, _last_key, _ic, _nm = _tmap[agent_id]\n            ui.notify(f"{_ic} {_nm} думает...", type="info")\n            try:\n                import importlib\n                _m = importlib.import_module(\n                    f"studio.modules.trading.{_mod_name}")\n                _chat = getattr(_m, _fn_name)\n                dialog = [m for m in state["chat_history"]\n                          if m.get("role") in ("user", "assistant") and m.get("content")]\n                reply = await asyncio.get_event_loop().run_in_executor(\n                    None, lambda: _chat(msg, state.get(_last_key), dialog))\n            except Exception as e:\n                reply = f"⚠️ {_nm} не смог ответить: {e}"\n            state["chat_history"].append({\n                "role": "assistant", "agent": agent_id, "content": reply})\n            update_chat_display()\n            return\n\n'


def backup(p):
    b = p.with_suffix(p.suffix + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(p, b); print("  📦 бэкап:", b.relative_to(ROOT))

def check():
    if not UI.exists():
        print("✗ Не вижу studio/economy/ui_exchange.py — запусти из КОРНЯ репы."); sys.exit(1)
    trading = ROOT / "studio" / "modules" / "trading"
    for m in ("brut_live.py", "avan_live.py", "cons_live.py"):
        if not (trading / m).exists():
            print(f"✗ Нет {m} — сначала примени patch_avan_cons.py."); sys.exit(1)

BTN_MARKER  = "[TRADERS врезаны патчем patch_traders_button]"
CHAT_MARKER = "[TRADERS CHAT врезаны патчем patch_traders_button]"

def main():
    print("─" * 60)
    print("ПАТЧ: Совет садится за стол — трейдеры в кнопке РЫНОК")
    print("─" * 60)
    check()
    src = UI.read_text(encoding="utf-8")

    done_btn  = BTN_MARKER in src
    done_chat = CHAT_MARKER in src
    if done_btn and done_chat:
        print("  ✓ обе врезки уже на месте — патч применён ранее."); return

    changed = False
    print("\n[1/2] Врезка в кнопку РЫНОК (после Архивариуса)…")
    if done_btn:
        print("  ✓ уже врезано.")
    elif BTN_ANCHOR not in src:
        print("  ⚠️  якорь Архивариуса не найден — врезку кнопки пропускаю."); 
    else:
        if not changed: backup(UI); changed = True
        src = src.replace(BTN_ANCHOR, BTN_ANCHOR + BTN_INJECT, 1)
        print("  ✍️  трейдеры сядут за стол после Архивариуса.")

    print("\n[2/2] Врезка чат-пузырьков трейдеров…")
    if done_chat:
        print("  ✓ уже врезано.")
    elif CHAT_ANCHOR not in src:
        print("  ⚠️  якорь заглушки чата не найден — врезку чата пропускаю.")
    else:
        if not changed: backup(UI); changed = True
        src = src.replace(CHAT_ANCHOR, CHAT_INJECT + CHAT_ANCHOR, 1)
        print("  ✍️  пузырьки A06/A07/A08 заговорили.")

    if changed:
        UI.write_text(src, encoding="utf-8")

    print("\n[проверка] Компиляция ui_exchange.py…")
    try:
        py_compile.compile(str(UI), doraise=True)
        print("  ✓ ui_exchange.py компилируется")
        print("\n✅ ГОТОВО. Кнопка РЫНОК ведёт цепочку до трёх трейдеров.")
    except py_compile.PyCompileError as e:
        print("  ✗ ОШИБКА компиляции:", e)
        print("  ⚠️  откати из .bak и позови меня — врезка не легла.")

if __name__ == "__main__":
    main()
