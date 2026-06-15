"""
patch_mt5_bridge_v3.py — добавляет в мост поля для индикатора AI_Tribunal_v8.

Новые поля в каждом сигнале JSON:
  confirmed          — AO пересёк ноль снизу вверх на этом баре
                       (ao_prev < 0 и ao_cur >= 0) → Искра видит звезду
  alligator_wake     — аллигатор только что проснулся:
                       bars_open[i] > 0 и bars_open[i-1] == 0 → Морж
  fractal_outside_jaw — последний нижний фрактал ниже Jaw → Ганс
  panic_phase        — фаза Паникёра по MFI:
                       SQUAT  → "LIQUIDATION"  (+Vol -MFI: рынок борется)
                       GREEN  → "FOMO"         (+Vol +MFI: толпа гонит цену)
                       FADE   → "DISBELIEF"    (-Vol -MFI: рынок остывает)
                       FAKE   → "NEUTRAL"      (-Vol +MFI: движение без объёма)

Вердикты (brut_verdict / avan_verdict / cons_verdict) — это выходы LLM-агентов,
их в бэктестовый мост добавить нельзя. Индикатор v8 показывает их только
когда Совет реально прогнан (из trading_state.json / atlas_trading.jsonl).
Для бэктеста эти поля отсутствуют — стрелки Трибунала не рисуются. Это честно.

Запуск:
  python patch_mt5_bridge_v3.py
"""

from pathlib import Path
import re, shutil, ast
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ROOT  = Path(__file__).resolve().parent
SKIP  = {"venv", ".venv", "__pycache__", ".git", "site-packages"}


# ── ищем файл моста ──────────────────────────────────────────────────────
def find_bridge():
    for p in ROOT.rglob("*.py"):
        if any(s in p.parts for s in SKIP): continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "mt5_signals" in txt and ("bars" in txt or "market_data" in txt):
            return p, txt
    return None, None

bridge_path, bridge_txt = find_bridge()
if not bridge_path:
    print("[!] Мост не найден. Убедись что файл с mt5_signals.json в корне студии.")
    raise SystemExit(1)
print(f"[+] Мост: {bridge_path.relative_to(ROOT)}")


# ── старый блок сборки сигнала ────────────────────────────────────────────
# ищем место где формируется словарь сигнала (signal = {...})
# и вставляем новые поля

# Паттерн: строка где пишется divergence или exit_bell в словарь сигнала
# Вид в текущем моste примерно такой:
#   signal = {
#       "date": ...,
#       "bar_index": ...,
#       "divergence": md.get("divergence_ao", False),
#       "exit_bell":  md.get("exit_bell", False),
#       "squat":      md.get("squat", {}).get("last_squat") is not None,
#       "alligator_sleeping": md.get("alligator", {}).get("sleeping", True),
#       ...
#   }
# Мы вставляем после "alligator_sleeping" строку новых полей.

OLD_SIGNAL_FIELD = '"alligator_sleeping": md.get("alligator", {}).get("sleeping", True),'
NEW_SIGNAL_FIELD = '''"alligator_sleeping": md.get("alligator", {}).get("sleeping", True),
            # ── v8: новые поля для AI_Tribunal_v8 ──────────────────
            "confirmed":           (
                md.get("ao", {}).get("crossed_zero", False)
                and md.get("ao", {}).get("zero_dir") == "UP"
            ),
            "alligator_wake": (
                md.get("alligator", {}).get("bars_open", 0) > 0
                and prev_bars_open == 0
            ),
            "fractal_outside_jaw": _fractal_outside_jaw(md),
            "panic_phase":         _mfi_to_panic(md.get("mfi", {}).get("type", "")),'''

# Мост может иметь разные имена переменных. Ищем по частичному совпадению.
if OLD_SIGNAL_FIELD not in bridge_txt:
    # Попробуем найти по более гибкому паттерну
    m = re.search(r'"alligator_sleeping"\s*:\s*md\.get\([^,]+,\s*True\)\s*,', bridge_txt)
    if m:
        OLD_SIGNAL_FIELD = m.group(0)
        NEW_SIGNAL_FIELD = NEW_SIGNAL_FIELD.replace(
            '"alligator_sleeping": md.get("alligator", {}).get("sleeping", True),',
            OLD_SIGNAL_FIELD
        )
    else:
        print("[!] Поле alligator_sleeping в моste не найдено.")
        print("    Добавь вручную в словарь сигнала:")
        print('    "confirmed": (md.get("ao",{}).get("crossed_zero") and md.get("ao",{}).get("zero_dir")=="UP"),')
        print('    "alligator_wake": (md.get("alligator",{}).get("bars_open",0) > 0 and prev_bars_open==0),')
        print('    "fractal_outside_jaw": _fractal_outside_jaw(md),')
        print('    "panic_phase": _mfi_to_panic(md.get("mfi",{}).get("type","")),')
        raise SystemExit(1)

# ── вспомогательные функции для вставки в мост ───────────────────────────
HELPER_FUNCS = '''
# ── AI_Tribunal_v8: вспомогательные функции ──────────────────────────────
def _fractal_outside_jaw(md: dict) -> bool:
    """Последний нижний фрактал ниже Jaw Аллигатора → сигнал для Ганса."""
    jaw = md.get("alligator", {}).get("jaw")
    frac = md.get("fractals", {}).get("last_down")
    if jaw is None or frac is None:
        return False
    return frac.get("price", 0) < jaw


def _mfi_to_panic(mfi_type: str) -> str:
    """Переводит тип BWMFI в фазу Паникёра."""
    # SQUAT  = +Vol -MFI: рынок борется, готовится к взрыву
    #          контрарный сигнал: толпа продаёт → смотрим на покупку
    if mfi_type == "SQUAT":   return "LIQUIDATION"
    # GREEN  = +Vol +MFI: настоящее движение, толпа гонит цену (FOMO)
    if mfi_type == "GREEN":   return "FOMO"
    # FADE   = -Vol -MFI: рынок остывает, неверие
    if mfi_type == "FADE":    return "DISBELIEF"
    # FAKE   = -Vol +MFI: движение без объёма → нейтрально
    return "NEUTRAL"
# ── END AI_Tribunal_v8 helpers ───────────────────────────────────────────

'''

# Вставляем хелперы перед главным циклом (перед def main / перед первым for bar)
# Ищем место вставки — перед строкой с "for bar" или "for i, bar"
MARKER_BEFORE = "if __name__"
if MARKER_BEFORE not in bridge_txt:
    # Запасной вариант — вставим в самый конец файла перед последней строкой
    MARKER_BEFORE = None

# Проверяем: хелперы уже есть?
if "_mfi_to_panic" in bridge_txt:
    print("    Хелперы уже добавлены (пропускаю вставку функций)")
    new_txt = bridge_txt.replace(OLD_SIGNAL_FIELD, NEW_SIGNAL_FIELD, 1)
else:
    if MARKER_BEFORE and MARKER_BEFORE in bridge_txt:
        new_txt = bridge_txt.replace(
            MARKER_BEFORE,
            HELPER_FUNCS + MARKER_BEFORE,
            1
        )
    else:
        new_txt = bridge_txt + "\n" + HELPER_FUNCS
    new_txt = new_txt.replace(OLD_SIGNAL_FIELD, NEW_SIGNAL_FIELD, 1)

# Проверяем что prev_bars_open используется — нужно его инициализировать
# Ищем место где bars = read_mt5_csv или аналог
if "prev_bars_open" in NEW_SIGNAL_FIELD and "prev_bars_open" not in new_txt:
    # Добавим инициализацию перед циклом по барам
    # Ищем: "for i in range" или "for bar in bars"
    m = re.search(r'(for\s+\w+\s+in\s+(?:range|bars|enumerate))', new_txt)
    if m:
        insert_at = m.start()
        new_txt = new_txt[:insert_at] + "prev_bars_open = 0\n    " + new_txt[insert_at:]

# ── синтаксис ────────────────────────────────────────────────────────────
try:
    ast.parse(new_txt)
    print("    синтаксис: OK")
except SyntaxError as e:
    print(f"[!] Синтаксис сломан: {e}")
    print("    Откатываю.")
    raise SystemExit(1)

# ── бэкап + запись ───────────────────────────────────────────────────────
bak = bridge_path.with_name(bridge_path.name + f".bak_{STAMP}")
shutil.copy2(bridge_path, bak)
bridge_path.write_text(new_txt, encoding="utf-8")
print(f"    бэкап: {bak.name}")
print(f"    ✓ {bridge_path.name} обновлён")

print()
print("─" * 64)
print(" ГОТОВО. Новые поля в каждом сигнале JSON:")
print()
print("  confirmed          — AO пересёк ноль снизу вверх (★ Искра)")
print("  alligator_wake     — аллигатор только что проснулся (▲ Морж)")
print("  fractal_outside_jaw — фрактал ниже Jaw (◆ Ганс)")
print("  panic_phase        — FOMO / LIQUIDATION / DISBELIEF (Паникёр)")
print()
print(" Вердикты трейдеров (brut/avan/cons) — только из живого Совета.")
print(" В бэктесте стрелки Трибунала не рисуются. Это честно.")
print()
print(" Дальше:")
print("   1. Перезапусти мост → новый mt5_signals.json")
print("   2. Скопируй AI_Tribunal_v8.mq5 в MQL5\\Indicators\\")
print("   3. MetaEditor → F7 → накинь на график")
print("─" * 64)
