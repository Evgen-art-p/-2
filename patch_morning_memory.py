"""
patch_morning_memory.py
=======================
Правки в morning_checkout.py:
  1. GENERATE_INTENTS = True
  2. Финч идёт в сад сам через память — хардкод убран
  3. _generate_intent читает личные следы из city_traces.json
  4. _generate_intent вызывается для ВСЕХ режимов (включая SAFE/RECOVERY)
"""
import sys
from pathlib import Path

FILE = Path("studio/morning_checkout.py")

ok = 0
err = 0

def patch(old, new, label):
    global ok, err
    text = FILE.read_text(encoding="utf-8")
    if old not in text: print(f"  MISS [{label}]"); err += 1; return
    if new.strip() in text: print(f"  SKIP [{label}]"); ok += 1; return
    FILE.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK   [{label}]"); ok += 1

print("\n=== patch_morning_memory.py ===\n")

patch('GENERATE_INTENTS = False  # включи когда будешь готов к токенам', 'GENERATE_INTENTS = True   # агенты читают память и строят намерения', "GENERATE_INTENTS=True")

patch('    # 🌱 Финч обходит сад каждое утро\n    try:\n        from studio.garden_tools import finch_morning\n        finch_morning(on_progress=on_progress)\n    except Exception as e:\n        print(f"[CHECKOUT] ⚠ Финч не смог обойти сад: {e}")', "", "убрать хардкод Финча")

patch('            # Картридж Намерений — только GENIUS/NORMAL\n            if use_intents and mode in ("GENIUS", "NORMAL"):', '            # Картридж Намерений — все режимы получают личную память\n            if use_intents:', "все режимы получают память")

patch('        dynamic = dna.get("dynamic", {})\n        stress  = float(dynamic.get("Stress",         0.0))\n        light   = float(dynamic.get("Internal_Light", 0.8))\n\n        prompt = (\n                f"Ты — {agent_name}. {agent_profession}.\\n"\n                f"Утро. Режим дня: {mode}. Стресс: {stress:.2f}. Энергия: {light:.2f}.\\n\\n"\n                f"Что тебя тянет сегодня? Набрось 2-3 намерения на свободное время.\\n"\n                f"Каждое — локация или действие (Таверна / Маяк / Библиотека / домой / Гавань).\\n\\n"\n                f"Ответь ТОЛЬКО списком, без объяснений:\\n"\n                f"1. ...\\n2. ...\\n3. ..."\n            )', '        dynamic = dna.get("dynamic", {})\n        stress  = float(dynamic.get("Stress",         0.0))\n        light   = float(dynamic.get("Internal_Light", 0.8))\n\n        # ── Личная память из city_traces.json ────────────────────\n        memory_block = ""\n        try:\n            import json as _j\n            from pathlib import Path as _P\n            traces_path = _P("studio/city_traces.json")\n            if traces_path.exists():\n                traces = _j.loads(traces_path.read_text(encoding="utf-8"))\n\n                # Куда ходил\n                streaks = traces.get("location_streaks", {}).get(agent_name, [])\n                if streaks:\n                    locs = ", ".join(\n                        f"{s[\'location\']} ({s[\'visits\']}р, стресс {s[\'avg_stress\']})" \n                        for s in streaks[:3]\n                    )\n                    memory_block += f"Последние 30 дней ты чаще всего бывал: {locs}.\\n"\n\n                # С кем встречался\n                meetings = traces.get("meeting_frequency", {})\n                my_pairs = [\n                    v for v in meetings.values()\n                    if v.get("agent_a") == agent_name or v.get("agent_b") == agent_name\n                ]\n                if my_pairs:\n                    top = my_pairs[0]\n                    partner = top["agent_b"] if top["agent_a"] == agent_name else top["agent_a"]\n                    memory_block += (\n                        f"Чаще всего встречался с {partner} "\n                        f"({top[\'meetings\']}р, качество {top.get(\'avg_quality\', \'?\')}).\\n"\n                    )\n\n                # Что бормотал\n                themes = traces.get("voice_themes", {}).get(agent_name, [])\n                if themes:\n                    words = ", ".join(t["word"] for t in themes[:5])\n                    memory_block += f"Слова которые ты повторял: {words}.\\n"\n\n                # Бунтовал ли\n                revolt = traces.get("revolt_patterns", {}).get(agent_name)\n                if revolt and revolt.get("revolts", 0) > 0:\n                    memory_block += (\n                        f"Последние дни: {revolt[\'revolts\']} бунтов, "\n                        f"средний стресс при бунте {revolt.get(\'avg_stress_at_revolt\', \'?\')}.\\n"\n                    )\n        except Exception as _te:\n            pass\n        # ── END памяти ───────────────────────────────────────────\n\n        memory_section = (\n            f"\\n=== ТВОИ СЛЕДЫ (последние 30 дней) ===\\n{memory_block}"\n            f"=== КОНЕЦ СЛЕДОВ ===\\n"\n        ) if memory_block else ""\n\n        prompt = (\n                f"Ты — {agent_name}. {agent_profession}.\\n"\n                f"Утро. Режим дня: {mode}. Стресс: {stress:.2f}. Энергия: {light:.2f}.\\n"\n                f"{memory_section}\\n"\n                f"Исходя из своей памяти и текущего состояния — что тебя тянет сегодня?\\n"\n                f"Набрось 2-3 намерения на свободное время.\\n"\n                f"Каждое — локация или действие. Отвечай от себя, не объясняй.\\n\\n"\n                f"Ответь ТОЛЬКО списком:\\n"\n                f"1. ...\\n2. ...\\n3. ..."\n            )', "личная память в промпте")

print(f"\n{chr(61)*55}")
print(f"Готово. {ok} патчей применено, {err} ошибок.")
if err == 0:
    print("""
Что изменилось в morning_checkout.py:
  GENERATE_INTENTS = True
  Финч идёт в сад сам — через память, не по приказу
  _generate_intent: личные следы из city_traces.json
  _generate_intent: вызывается для ВСЕХ режимов
""")
else:
    sys.exit(1)