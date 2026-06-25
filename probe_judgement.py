# probe_judgement.py
# ─────────────────────────────────────────────────────────────
# ЗОНД СУДА — доходит ли суд трейдера до DNA?
# Только ЧИТАЕТ. Ничего не пишет, не меняет, не лечит.
# Запуск из корня репы:  python probe_judgement.py
# ─────────────────────────────────────────────────────────────
import json
from pathlib import Path

PNL    = Path("economy/data/trading_pnl.jsonl")
ATLAS  = Path("economy/data/atlas_trading.jsonl")
STATE  = Path("studio/modules/trading/state/trading_state.json")

def read_jsonl(p):
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out

print("═" * 64)
print("ЗОНД СУДА — читаю три тетради цеха")
print("═" * 64)

# ── 1. ЗАКРЫТЫЕ СДЕЛКИ (журнал PnL) ──────────────────────────
pnl = read_jsonl(PNL)
print(f"\n📒 trading_pnl.jsonl: {len(pnl)} закрытых сделок")
total_r = 0.0
for r in pnl:
    pr = r.get("pnl_r")
    if pr is not None:
        total_r += pr
    print(f"   {r.get('closed_at','?'):20} {str(r.get('trader','?')):12} "
          f"{str(r.get('pnl_r','?')):>9}R  {r.get('close_reason','?')}")
print(f"   ── СУММАРНО: {round(total_r,4)}R ──")

# ── 2. АТЛАС — что записал суд (POSITION_CLOSED) ─────────────
atlas = read_jsonl(ATLAS)
closed_ev = [a for a in atlas
             if (a.get("entry", a) or {}).get("event") == "POSITION_CLOSED"]
print(f"\n📝 atlas_trading.jsonl: {len(atlas)} записей, "
      f"из них POSITION_CLOSED: {len(closed_ev)}")

# ── 3. ГЛАВНОЕ: было ли в позициях поле entry_bias? ─────────
# Журнал PnL не хранит entry_bias/direction напрямую — суд читал их
# из позиции в памяти. Косвенная улика: совпало ли направление с минусом.
# Прямую улику даёт DNA трейдеров (стресс). Читаем dynamic DNA.
print("\n🧬 СТРЕСС В DNA ТРЕЙДЕРОВ (доказательство, что суд дошёл):")
TRADERS = {
    "A07_AVANTURIST": ["studio/modules/trading", "studio/modules/residents"],
    "A06_BRUT":       ["studio/modules/trading", "studio/modules/residents"],
    "A08_KONSERVATOR":["studio/modules/trading", "studio/modules/residents"],
}

def find_dna(aid):
    """Ищет dna.json трейдера в вероятных местах."""
    short = aid.split("_", 1)[-1].lower()       # avanturist / brut / konservator
    roots = [Path("studio/modules/trading"),
             Path("studio/modules/residents"),
             Path("studio/modules")]
    for root in roots:
        if not root.exists():
            continue
        for dna in root.rglob("dna.json"):
            txt = dna.read_text(encoding="utf-8", errors="ignore").lower()
            if short in str(dna).lower() or short in txt[:400]:
                return dna
    return None

for aid in TRADERS:
    dna_path = find_dna(aid)
    if not dna_path:
        print(f"   {aid:16} — dna.json НЕ НАЙДЕН (укажи путь вручную)")
        continue
    try:
        dna = json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"   {aid:16} — не читается ({e})")
        continue
    dyn = dna.get("dynamic", {}) or dna.get("state", {}) or {}
    stress = dyn.get("Stress", dyn.get("stress", "—"))
    streak = dyn.get("streak", dyn.get("Streak", "—"))
    print(f"   {aid:16} → Stress={stress}  streak={streak}")
    print(f"        ({dna_path})")

print("\n" + "═" * 64)
print("ЧИТАЙ ТАК:")
print("  · Stress > 0.0 у Авантюриста → суд ДОШЁЛ, лекарство работает.")
print("  · Stress = 0.0 при минусах против ветра → канал МОЛЧИТ, чиним.")
print("  · entry_bias живёт в позиции в памяти — если стресс 0, проверим,")
print("    доезжает ли global_bias до _persist_trading_state живым.")
print("═" * 64)
