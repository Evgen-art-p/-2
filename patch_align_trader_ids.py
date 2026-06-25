# patch_align_trader_ids.py
# ─────────────────────────────────────────────────────────────
# ПАТЧ: выравнивание id трейдеров под зов суда
# Маркер: TRADER_ID_ALIGN_V1
#
# КОРЕНЬ: суд (hooks.py) зовёт трейдеров "A06_BRUT"/"A07_AVANTURIST"/
# "A08_KONSERVATOR", а в dna.json у них старый реестровый id
# (156_BRUT/157_AVANTURIST/158_KONSERVATOR). Имена не совпадают →
# _find_agent_dir не находит → sync_to_dna молчит → стресс 0.0.
# У Искры (A01_ISKRA) id уже правильный — она образец.
#
# ЛЕЧЕНИЕ: меняем ТОЛЬКО поле "id". Всё остальное (характер, резонанс,
# баланс, role) не трогаем. role остаётся как метка, добавляем
# registry_id со старым номером — чтобы город не потерял реестровую связь.
#
# Идемпотентно: если id уже правильный — пропускает.
# Бэкап: рядом кладёт .json.bak_TRADER_ID_ALIGN перед правкой.
#
# Запуск из корня репы:  python patch_align_trader_ids.py
# ─────────────────────────────────────────────────────────────
import json, shutil
from pathlib import Path

TRADING = Path("studio/modules/trading")

# папка → правильный id (как зовёт суд) · старый реестровый номер сохраняем
FIXES = {
    "A06": "A06_BRUT",
    "A07": "A07_AVANTURIST",
    "A08": "A08_KONSERVATOR",
}

print("═" * 64)
print("ПАТЧ TRADER_ID_ALIGN_V1 — выравниваю id трейдеров под зов суда")
print("═" * 64)

if not TRADING.exists():
    print(f"❌ Не вижу {TRADING}. Запусти из КОРНЯ репы.")
    raise SystemExit(1)

changed, skipped, missing = [], [], []

for folder, correct_id in FIXES.items():
    dna_path = TRADING / folder / "dna.json"
    if not dna_path.exists():
        missing.append(folder)
        print(f"\n⚪ {folder}/dna.json — нет файла, пропускаю")
        continue

    dna = json.loads(dna_path.read_text(encoding="utf-8"))
    old_id = dna.get("id", "")

    if old_id == correct_id:
        skipped.append(folder)
        print(f"\n✅ {folder}: id уже «{correct_id}» — ничего не делаю (идемпотентно)")
        continue

    # бэкап перед правкой
    backup = dna_path.with_suffix(".json.bak_TRADER_ID_ALIGN")
    if not backup.exists():
        shutil.copy2(dna_path, backup)

    # сохраняем старый реестровый номер, чтоб город не потерял связь
    if old_id and "registry_id" not in dna:
        dna["registry_id"] = old_id

    dna["id"] = correct_id

    # пишем обратно, порядок ключей сохраняем максимально близко
    dna_path.write_text(
        json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")

    changed.append(folder)
    print(f"\n🔧 {folder}: id «{old_id}» → «{correct_id}»")
    print(f"      (старый номер сохранён в registry_id={old_id})")
    print(f"      бэкап: {backup.name}")

print("\n" + "─" * 64)
print(f"Изменено: {len(changed)} · уже верных: {len(skipped)} · нет: {len(missing)}")

# ── ПРОВЕРКА: теперь суд находит каждого? ──
print("\n🔍 Проверяю, что суд теперь находит трейдеров...")
import sys
sys.path.insert(0, str(Path(".").resolve()))
try:
    from studio.grondheim_memory import _find_agent_dir
    all_ok = True
    for folder, correct_id in FIXES.items():
        d = _find_agent_dir(correct_id, "trading") or _find_agent_dir(correct_id)
        mark = "✅" if d else "❌"
        if not d:
            all_ok = False
        print(f"   {mark} «{correct_id}» → {d if d else 'НЕ НАЙДЕН'}")
    print()
    if all_ok:
        print("═" * 64)
        print("ГОТОВО. Суд теперь находит всех троих трейдеров.")
        print("Следующий шаг: probe_truba.py — увидеть живой стресс,")
        print("потом учебный прогон РЫНОК с обучением.")
        print("═" * 64)
    else:
        print("⚠️ Кто-то всё ещё не находится — смотри ❌ выше.")
except Exception as e:
    print(f"   ⚠️ Проверку не удалось выполнить: {e}")
    print(f"   (id всё равно изменён — проверь зондом probe_truba.py)")
