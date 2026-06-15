"""
patch_main_bridge_v4.py — переписывает _scan() в main.py.

БЫЛО: каждый бар оценивается независимо.
  squat = есть приседающий в окне (срабатывает на каждом баре)
  confirmed = AO пересёк ноль (срабатывает часто)
  → весь график в символах

СТАЛО: машина состояний между барами.
  NOT_FOUND → DIVER_SEEN → SQUAT_ON_BOTTOM → CONFIRMED → NOT_FOUND

  NOT_FOUND:      ищем бычью дивергенцию AO (divergence_ao=True, AO<0)
  DIVER_SEEN:     нашли дивергенцию → ждём приседающего бара НА ДНЕ
                  (squat + AO всё ещё < 0 + аллигатор не спит)
  SQUAT_ON_BOTTOM: нашли squat → ждём пересечения AO нуля снизу вверх
  CONFIRMED:      AO пересёк ноль вверх → это CONFIRMED, рисуем звезду
                  → сбрасываемся в NOT_FOUND

  Сброс в NOT_FOUND если:
  — AO ушёл глубоко в минус ещё раз (новый импульс вниз)
  — exit_bell = True (тренд сменился)
  — прошло более MAX_BARS_WAIT баров без подтверждения

Поля в сигнале:
  divergence          — бычья дивергенция (кружок Искры)
  squat               — squat на дне после дивергенции (ромб Искры)
  confirmed           — AO пересёк ноль после squat (звезда Искры)
  alligator_sleeping  — без изменений
  alligator_wake      — аллигатор только что проснулся (был sleeping, стал нет)
  fractal_outside_jaw — последний нижний фрактал ниже Jaw
  panic_phase         — FOMO/LIQUIDATION/DISBELIEF/NEUTRAL по MFI
  exit_bell           — медвежья дивергенция (конец импульса)
"""

from pathlib import Path
import re, shutil, ast
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"

if not TARGET.exists():
    print("[!] main.py не найден рядом со скриптом")
    raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

# ── Старый _scan ─────────────────────────────────────────────────────────
OLD_SCAN = '''        def _scan(bars, symbol, timeframe):
            point = get_point(symbol)
            signals = []
            for i in range(40, len(bars)):
                window = bars[max(0, i-199):i+1]
                import io, sys as _sys
                _old = _sys.stdout
                _sys.stdout = io.StringIO()
                try:
                    md = build_market_data(window, symbol=symbol, timeframe=timeframe, point=point)
                finally:
                    _sys.stdout = _old
                if not md:
                    continue
                has_div  = bool(md.get("divergence_ao"))
                has_bell = bool(md.get("exit_bell"))
                has_sq   = bool(md.get("squat", {}).get("last_squat"))
                sleeping = bool(md.get("alligator", {}).get("sleeping"))
                if not (has_div or has_bell or has_sq):
                    continue
                entry_price = None
                stop_price  = None
                if has_div and not sleeping:
                    sq = md.get("squat", {}).get("last_squat")
                    if sq:
                        entry_price = round(sq["high"] + point, 6)
                        if i >= 1:
                            stop_price = round(bars[i-1]["low"] - point, 6)
                signals.append({
                    "date":               bars[i]["date"],
                    "bar_index":          i,
                    "divergence":         has_div,
                    "exit_bell":          has_bell,
                    "squat":              has_sq,
                    "alligator_sleeping": sleeping,
                    "ao_confirmed":       bool(md.get("ao", {}).get("crossed_zero")),
                    "entry_price":        entry_price,
                    "stop_price":         stop_price,
                })
            return signals'''

NEW_SCAN = '''        def _mfi_to_panic(mfi_type):
            if mfi_type == "SQUAT":  return "LIQUIDATION"
            if mfi_type == "GREEN":  return "FOMO"
            if mfi_type == "FADE":   return "DISBELIEF"
            return "NEUTRAL"

        def _fractal_outside_jaw(md):
            jaw  = md.get("alligator", {}).get("jaw")
            frac = md.get("fractals",  {}).get("last_down")
            if jaw is None or frac is None: return False
            return frac.get("price", 0) < jaw

        def _suppress(fn, *a, **kw):
            """Вызывает fn без вывода в stdout."""
            import io, sys as _s
            old = _s.stdout; _s.stdout = io.StringIO()
            try:    return fn(*a, **kw)
            finally: _s.stdout = old

        def _scan(bars, symbol, timeframe):
            point = get_point(symbol)
            signals   = []

            # ── Машина состояний Искры ────────────────────────────────
            # NOT_FOUND → DIVER_SEEN → SQUAT_ON_BOTTOM → CONFIRMED
            STATE_NONE  = 0
            STATE_DIVER = 1   # увидели дивергенцию
            STATE_SQUAT = 2   # увидели squat после дивергенции
            MAX_WAIT    = 30  # баров до сброса если нет подтверждения

            state       = STATE_NONE
            state_since = 0          # бар на котором вошли в состояние
            prev_sleeping = True

            for i in range(40, len(bars)):
                window = bars[max(0, i-199):i+1]
                md = _suppress(build_market_data, window,
                               symbol=symbol, timeframe=timeframe, point=point)
                if not md:
                    continue

                # ── Базовые флаги ─────────────────────────────────────
                has_div  = bool(md.get("divergence_ao"))
                has_bell = bool(md.get("exit_bell"))
                sleeping = bool(md.get("alligator", {}).get("sleeping"))
                ao_val   = md.get("ao", {}).get("value") or 0
                ao_cross = bool(md.get("ao", {}).get("crossed_zero"))
                ao_dir   = md.get("ao", {}).get("zero_dir") or ""
                sq_block = md.get("squat", {}).get("last_squat")
                has_sq   = sq_block is not None

                # Squat именно на текущем баре (last_squat.date == bars[i].date)
                sq_now = (has_sq and
                          sq_block.get("date", "") == bars[i]["date"])

                # ── Флаги для индикатора ──────────────────────────────
                flag_diver   = False
                flag_squat   = False
                flag_conf    = False
                flag_wake    = (not sleeping and prev_sleeping)   # Морж
                flag_frac    = _fractal_outside_jaw(md)           # Ганс
                panic_phase  = _mfi_to_panic(
                    md.get("mfi", {}).get("type", ""))

                # ── Переходы машины состояний ─────────────────────────
                # Сброс при exit_bell или слишком долгом ожидании
                if has_bell or (state != STATE_NONE and
                                i - state_since > MAX_WAIT):
                    state = STATE_NONE

                if state == STATE_NONE:
                    if has_div and not sleeping and ao_val < 0:
                        state       = STATE_DIVER
                        state_since = i
                        flag_diver  = True          # кружок

                elif state == STATE_DIVER:
                    # Ещё раз видим дивергенцию — обновляем (дивергенция углубилась)
                    if has_div and ao_val < 0:
                        flag_diver  = True
                        state_since = i             # продлеваем окно ожидания
                    # Squat после дивергенции (на дне, AO ещё под нулём)
                    if sq_now and not sleeping and ao_val < 0:
                        state       = STATE_SQUAT
                        state_since = i
                        flag_squat  = True          # ромб

                elif state == STATE_SQUAT:
                    # AO пересёк ноль снизу вверх — CONFIRMED
                    if ao_cross and ao_dir == "UP":
                        flag_conf = True            # звезда
                        state     = STATE_NONE      # цикл замкнулся
                    # Повторный squat пока ждём — обновляем
                    elif sq_now and ao_val < 0:
                        flag_squat  = True
                        state_since = i

                # Сброс если AO резко ушёл вниз (новый импульс)
                if ao_val < -50 and state != STATE_NONE:
                    state = STATE_NONE

                prev_sleeping = sleeping

                # ── Пишем в сигналы только значимые бары ─────────────
                any_flag = (flag_diver or flag_squat or flag_conf
                            or flag_wake or flag_frac or has_bell
                            or panic_phase in ("FOMO", "LIQUIDATION"))
                if not any_flag:
                    continue

                # Цены входа (только при подтверждённом squat)
                entry_price = None
                stop_price  = None
                if flag_squat and sq_block:
                    entry_price = round(sq_block["high"] + point, 6)
                    if i >= 1:
                        stop_price = round(bars[i-1]["low"] - point, 6)

                signals.append({
                    "date":                bars[i]["date"],
                    "bar_index":           i,
                    "divergence":          flag_diver,
                    "squat":               flag_squat,
                    "confirmed":           flag_conf,
                    "exit_bell":           has_bell,
                    "alligator_sleeping":  sleeping,
                    "alligator_wake":      flag_wake,
                    "fractal_outside_jaw": flag_frac,
                    "panic_phase":         panic_phase,
                    "entry_price":         entry_price,
                    "stop_price":          stop_price,
                })
            return signals'''

if OLD_SCAN not in txt:
    print("[!] Старый _scan не найден точно.")
    print("    Проверяю по сигнатуре...")
    if "ao_confirmed" in txt and "_scan" in txt:
        print("    Сигнатура найдена (ao_confirmed). Пробую regex-замену.")
        pattern = re.compile(
            r'def _scan\(bars, symbol, timeframe\):.+?return signals',
            re.DOTALL
        )
        m = pattern.search(txt)
        if m:
            # Извлекаем отступ
            line_start = txt.rfind('\n', 0, m.start()) + 1
            indent = len(txt[line_start:m.start()])
            new_txt = txt[:m.start()] + NEW_SCAN.lstrip() + txt[m.end():]
        else:
            print("[!] regex тоже не нашёл. Правь вручную.")
            raise SystemExit(1)
    else:
        print("[!] _scan не найден вообще. Файл другой?")
        raise SystemExit(1)
else:
    new_txt = txt.replace(OLD_SCAN, NEW_SCAN, 1)

# синтаксис
try:
    ast.parse(new_txt)
    print("синтаксис: OK")
except SyntaxError as e:
    print(f"[!] Синтаксис сломан: {e}")
    raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(new_txt, encoding="utf-8")
print(f"бэкап: {bak.name}")
print(f"✓ main.py обновлён")
print()
print("─" * 64)
print(" Машина состояний Искры:")
print("  NOT_FOUND → (дивергенция) → DIVER_SEEN")
print("           → (squat на дне) → SQUAT_ON_BOTTOM")
print("           → (AO пересёк 0) → CONFIRMED → NOT_FOUND")
print()
print(" В JSON теперь попадают только значимые бары:")
print("  divergence=true    — кружок (вход в DIVER_SEEN)")
print("  squat=true         — ромб   (squat ПОСЛЕ дивергенции)")
print("  confirmed=true     — звезда (AO пересёк 0 ПОСЛЕ squat)")
print("  alligator_wake     — Морж: аллигатор только что проснулся")
print("  fractal_outside_jaw — Ганс: фрактал ниже Jaw")
print("  panic_phase        — Паникёр: только FOMO/LIQUIDATION рисуются")
print()
print(" Дальше: перезапусти studio (python main.py)")
print(" Мост пересчитает все бары с новой логикой.")
print(" Перегрузи AI_Tribunal_v8 в MT5.")
print("─" * 64)
