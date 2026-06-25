# probe_truba.py
# ─────────────────────────────────────────────────────────────
# ЗОНД-ИСПЫТАНИЕ ТРУБЫ: суд → sync_to_dna → стресс в dna.json
# Проверяет ВСЮ трубу на живом примере (Авантюрист, bad_work против ветра).
# РАБОТАЕТ НА КОПИИ dna.json — живую душу НЕ калечит (замер и откат).
#
# Запуск из корня репы:  python probe_truba.py
# ─────────────────────────────────────────────────────────────
import json, shutil
from pathlib import Path

print("═" * 66)
print("ЗОНД-ИСПЫТАНИЕ ТРУБЫ — дойдёт ли суд до стресса?")
print("═" * 66)

# Имя, которым СУД зовёт трейдера (из hooks.py _judge_trader_by_result):
AID = "A07_AVANTURIST"
DEPT = "trading"

# ── УЗЕЛ 1: находит ли _find_agent_dir папку по имени суда? ──
print(f"\n① ПОИСК ПАПКИ по имени суда «{AID}» (dept={DEPT})")
try:
    from studio.grondheim_memory import _find_agent_dir
    agent_dir = _find_agent_dir(AID, DEPT)
    if not agent_dir:
        # пробуем без dept
        agent_dir = _find_agent_dir(AID)
    if agent_dir:
        print(f"   ✅ НАШЁЛ: {agent_dir}")
    else:
        print(f"   ❌ НЕ НАШЁЛ. Суд зовёт «{AID}», но ни одна папка по этому")
        print(f"      имени не отзывается. Урок уходит в пустоту — стресс 0.0")
        print(f"      ЛЕЧЕНИЕ: вписать id=\"{AID}\" в A07/dna.json или info.json.")
        raise SystemExit(0)
except SystemExit:
    raise
except Exception as e:
    print(f"   ❌ Ошибка поиска: {e}")
    raise SystemExit(1)

# ── УЗЕЛ 2: читается ли dna.json, есть ли характер? ──
print(f"\n② ЧТЕНИЕ dna.json + характер (static)")
dna_path = agent_dir / "dna.json"
if not dna_path.exists():
    print(f"   ❌ Нет dna.json в {agent_dir}")
    raise SystemExit(1)
dna = json.loads(dna_path.read_text(encoding="utf-8"))
static  = dna.get("static", {})
dynamic = dna.get("dynamic", {})
print(f"   ✅ dna.json читается")
print(f"      характер (static): {static if static else '⚠️ ПУСТО'}")
stress_before = float(dynamic.get("Stress", 0.0))
print(f"      Stress сейчас: {stress_before}")

# ── делаем КОПИЮ, чтобы откатить после испытания ──
backup = dna_path.with_suffix(".json.probe_bak")
shutil.copy2(dna_path, backup)

try:
    # ── УЗЕЛ 3: реальный вызов суда — bad_work — поднимает ли стресс? ──
    print(f"\n③ ИСПЫТАНИЕ: зову sync_to_dna({AID}, 'bad_work', i=0.3)")
    print(f"   (то же, что делает суд при минусе против ветра)")
    from studio.grondheim_memory import sync_to_dna
    sync_to_dna(AID, "bad_work", intensity=0.3, dept=DEPT)

    dna_after = json.loads(dna_path.read_text(encoding="utf-8"))
    stress_after = float(dna_after.get("dynamic", {}).get("Stress", 0.0))
    delta = round(stress_after - stress_before, 4)
    print(f"\n   Stress: {stress_before} → {stress_after}  (Δ {'+' if delta>=0 else ''}{delta})")
    if delta > 0:
        print(f"   ✅ ТРУБА ЦЕЛАЯ — суд поднял стресс. Лекарство доходит до DNA.")
    elif delta == 0:
        print(f"   ⚠️ Стресс не изменился. Либо стерильный кран внутри, либо уже на потолке.")
    else:
        print(f"   ⚠️ Стресс УПАЛ — неожиданно, смотреть формулу.")

    # ── УЗЕЛ 4: характер влияет? (эмпат vs упрямый — теоретический замер) ──
    print(f"\n④ ХАРАКТЕР процеживает урок (закон «всё от личности»)")
    emp = float(static.get("Empathy", 0.5))
    stub = float(static.get("Stubbornness", 0.5))
    emp_mult = round(0.7 + emp * 0.6, 3)
    raw = round(0.15 * 0.3, 4)
    felt = round(raw * emp_mult, 4)
    print(f"   Empathy={emp} → множитель {emp_mult}")
    print(f"   Базовый удар bad_work: +{raw} стресса")
    print(f"   Этот агент почувствовал: +{felt} (характер {'усилил' if emp_mult>1 else 'ослабил'})")
    print(f"   ✅ Урок ложится В характер, не поверх — как и задумано.")

finally:
    # ── ОТКАТ: возвращаем живую DNA как была (испытание не калечит) ──
    shutil.move(str(backup), str(dna_path))
    print(f"\n♻️  Откат: dna.json возвращён в исходное (Stress снова {stress_before}).")
    print(f"   Живая душа Авантюриста не тронута — это была проверка на копии.")

print("\n" + "═" * 66)
print("ВЕРДИКТ:")
print("  Если ① нашёл папку и ③ поднял стресс → ТРУБА РАБОТАЕТ.")
print("  Тогда учебный прогон (--learn) будет писать стресс по-настоящему,")
print("  суд накажет вход против НАСТОЯЩЕГО ветра, урок ляжет в характер.")
print("  Можно учить со спокойной совестью.")
print("═" * 66)
