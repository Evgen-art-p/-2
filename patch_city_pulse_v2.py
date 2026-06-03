"""
patch_city_pulse_v2.py
======================
Подключает city_pulse.py v2.0 к городу.
Пять точек: wake / walk+voice / meeting+резиденты / weather / night+резиденты
"""
import shutil, sys
from pathlib import Path

CHECKOUT = Path("studio/morning_checkout.py")
WALKER   = Path("studio/city_walker.py")
NIGHT    = Path("studio/night_cycle.py")
PULSE_SRC = Path("/home/claude/city_pulse_v2.py") if Path("/home/claude/city_pulse_v2.py").exists() \
            else Path("studio/city_pulse.py")

ok = 0
err = 0

def patch(path, old, new, label):
    global ok, err
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  MISS [{label}]"); err += 1; return
    if new.strip() in text:
        print(f"  SKIP [{label}]"); ok += 1; return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK   [{label}]"); ok += 1

print("\n=== patch_city_pulse_v2.py ===\n")

# Копируем city_pulse.py v2.0
if PULSE_SRC.exists() and PULSE_SRC != Path("studio/city_pulse.py"):
    shutil.copy2(PULSE_SRC, "studio/city_pulse.py")
    print("  OK   studio/city_pulse.py (v2.0)\n")

# ────────────────────────────────────────────────────────────
# 1. morning_checkout.py — wake
# ────────────────────────────────────────────────────────────
print(f"{CHECKOUT.name}:")

wake_old = '\n'.join([
    '            modes[agent_key] = result',
    '            mode = result["mode"]',
    '            summary[mode] = summary.get(mode, 0) + 1',
    '            count += 1',
])

wake_add = '\n'.join([
    '',
    '            # ── ПУЛЬС: wake ──────────────────────────────────────',
    '            try:',
    '                from studio.city_pulse import log_pulse as _lp',
    '                _dyn = dna.get("dynamic", {})',
    '                _lp("wake",',
    '                    agent=agent_name, dept=dept,',
    '                    stress=round(float(_dyn.get("Stress", 0.0)), 3),',
    '                    light=round(float(_dyn.get("Internal_Light", 0.8)), 3),',
    '                    patience=round(float(_dyn.get("Patience", 1.0)), 3),',
    '                    mode=mode, streak=int(_dyn.get("streak", 0)),',
    '                    night_revolt=result.get("night_revolt", False),',
    '                )',
    '            except Exception:',
    '                pass',
    '            # ── END ПУЛЬС ──',
])

patch(CHECKOUT, wake_old, wake_old + wake_add, "wake")

# ────────────────────────────────────────────────────────────
# 2. city_walker.py — walk + agent_voice
# ────────────────────────────────────────────────────────────
print(f"\n{WALKER.name}:")

walk_anchor = "    # ── Память прогулки: единый формат · Спринт 21 ──"

walk_add = '\n'.join([
    '    # ── ПУЛЬС: walk + agent_voice ────────────────────────────────',
    '    try:',
    '        from studio.city_pulse import log_pulse as _lp',
    '        _dyn_w = dna.get("dynamic", {})',
    '        _lp("walk",',
    '            agent=name, dept=workshop,',
    '            location=chosen_location,',
    '            stress=round(float(_dyn_w.get("Stress", 0.0)), 3),',
    '            light=round(float(_dyn_w.get("Internal_Light", 0.8)), 3),',
    '            weather=city_state.get("weather", ""),',
    '            mode=city_state.get("morning_modes", {})',
    '                .get(f"{folder}_{workshop}", {}).get("mode", ""),',
    '            agent_voice=response[:150] if response else "",',
    '        )',
    '    except Exception:',
    '        pass',
    '    # ── END ПУЛЬС ──',
    '',
    walk_anchor,
])

patch(WALKER, walk_anchor, walk_add, "walk + agent_voice")

# ────────────────────────────────────────────────────────────
# 3. city_walker.py — meeting + notify_residents
# ────────────────────────────────────────────────────────────

# Строим якорь аккуратно — без вложенных кавычек в строке
q = "'"  # одинарная кавычка
meeting_line1 = "    if meeting:"
meeting_line2 = "        print(f\"[CITY] \U0001f4ac {name} встретил {meeting[" + q + "met" + q + "]} в {meeting[" + q + "location" + q + "]}\")"
meeting_old = meeting_line1 + "\n" + meeting_line2

meeting_new = '\n'.join([
    meeting_line1,
    meeting_line2,
    "        # ── ПУЛЬС: meeting + голоса резидентов ──────────────────",
    "        try:",
    "            from studio.city_pulse import log_pulse as _lpm, notify_residents as _nr",
    '            _dyn_m = dna.get("dynamic", {})',
    "            _ed = dict(",
    '                agent_a=name, agent_b=meeting["met"],',
    '                dept_a=workshop, location=meeting["location"],',
    '                type=meeting.get("type", ""),',
    "                quality=round(float(meeting.get(\"quality\", 0.0)), 3),",
    '                stress_a=round(float(_dyn_m.get("Stress", 0.0)), 3),',
    '                known=meeting.get("known", False),',
    '                silent=meeting.get("silent", False),',
    "            )",
    '            _eid = _lpm("meeting", **_ed)',
    "            import threading as _th",
    '            _th.Thread(target=_nr, args=("meeting", _eid, _ed), daemon=True).start()',
    "        except Exception:",
    "            pass",
    "        # ── END ПУЛЬС ──",
])

patch(WALKER, meeting_old, meeting_new, "meeting + notify_residents")

# ────────────────────────────────────────────────────────────
# 4. city_walker.py — weather
# ────────────────────────────────────────────────────────────

weather_line = "        print(f\"[CITY] \U0001f324 Погода: avg_stress={avg_stress:.2f} \u2192 {state[" + q + "weather" + q + "]}\")"

weather_new = '\n'.join([
    weather_line,
    "        # ── ПУЛЬС: weather ───────────────────────────────────────",
    "        try:",
    "            from studio.city_pulse import log_pulse as _lpw",
    '            _lpw("weather", weather=state["weather"], avg_stress=round(avg_stress, 3))',
    "        except Exception:",
    "            pass",
    "        # ── END ПУЛЬС ──",
])

patch(WALKER, weather_line, weather_new, "weather")

# ────────────────────────────────────────────────────────────
# 5. night_cycle.py — night + notify_residents
# ────────────────────────────────────────────────────────────
print(f"\n{NIGHT.name}:")

night_old = '\n'.join([
    '            # Хроника бунта',
    '            if decision == "REVOLT":',
])

night_new = '\n'.join([
    '            # ── ПУЛЬС: night + голоса резидентов ────────────────',
    '            try:',
    '                from studio.city_pulse import log_pulse as _lpn, notify_residents as _nr',
    '                _dyn_n = dna.get("dynamic", {})',
    '                _ed_n = dict(',
    '                    agent=agent_name, dept=dept, decision=decision,',
    '                    revolt_score=round(float(night.get("revolt_score", 0.0)), 3),',
    '                    stress=round(float(_dyn_n.get("Stress", 0.0)), 3),',
    '                    light=round(float(_dyn_n.get("Internal_Light", 0.8)), 3),',
    '                    resentment=round(float(night.get("resentment", 0.0)), 3),',
    '                )',
    '                _eid_n = _lpn("night", **_ed_n)',
    '                if decision in ("REVOLT", "RESTLESS"):',
    '                    import threading as _th',
    '                    _th.Thread(',
    '                        target=_nr, args=("night", _eid_n, _ed_n), daemon=True',
    '                    ).start()',
    '            except Exception:',
    '                pass',
    '            # ── END ПУЛЬС ──',
    '',
    night_old,
])

patch(NIGHT, night_old, night_new, "night + notify_residents")

# ────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"Готово. {ok} патчей применено, {err} ошибок.")
if err == 0:
    print("""
Что изменилось:
  studio/city_pulse.py  ← v2.0
  morning_checkout.py   ← wake
  city_walker.py        ← walk + agent_voice
  city_walker.py        ← meeting + голоса резидентов
  city_walker.py        ← weather
  night_cycle.py        ← night + голоса резидентов

Commit:
  feat: city_pulse v2.0 — пульс города с голосами резидентов
""")
else:
    sys.exit(1)
