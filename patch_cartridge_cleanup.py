# patch_cartridge_cleanup.py
# ═══════════════════════════════════════════════════════════════
# ЗАКОН КАРТРИДЖА — дочистка (Спринт 45)
#
# Три вещи которые остались после patch_cartridge_law.py:
#
# 1. slot_manager.py — инициализировал список слотов через info.json.
#    trading там не появлялся (нет info.json). Теперь через list_cartridges().
#
# 2. cartridge_manager/ui.py — страница Картриджей строила список
#    доступных модулей тоже через info.json. Та же дыра.
#    Теперь через list_cartridges().
#
# 3. workshop/ui.py — _dept_runtype() умела читать run_type из манифеста
#    любого картриджа включая trading. Мастерская — интерфейс Студии,
#    Совет там чужой. Функция теперь работает только для цехов Студии
#    из DEPT_TO_RUNTYPE; неизвестный цех получает дефолт "social"
#    (как и раньше до patch_cartridge_law.py).
#    Запуск Совета — из трейд-дашборда, не из Мастерской.
#
# Запуск:  python patch_cartridge_cleanup.py   (из корня, где main.py)
# Бэкапы:  _patch_backups/cartridge_cleanup_{дата}/
# ═══════════════════════════════════════════════════════════════
import json
import shutil
import subprocess
import sys
import py_compile
from datetime import datetime
from pathlib import Path

BACKUP_ROOT = Path("_patch_backups")

FIXES = [

    # ═══ studio/slot_manager.py ═══════════════════════════════
    dict(
        id="S1", file="studio/slot_manager.py",
        name="slot_manager: импорт list_cartridges",
        old="from studio.cartridge import CartridgeManifest, load_cartridge",
        new="from studio.cartridge import CartridgeManifest, load_cartridge\nfrom studio.modules_registry import list_cartridges",
        done="from studio.modules_registry import list_cartridges",
        requires=[],
    ),
    dict(
        id="S2", file="studio/slot_manager.py",
        name="slot_manager: _init_default_slots() через list_cartridges()",
        old='''        order = 0
        self.slots = []
        for d in sorted(MODULES_DIR.iterdir()):
            if not d.is_dir():
                continue
            info_path = d / "info.json"
            if not info_path.exists():
                continue

            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
            except Exception:
                info = {}

            module_id = d.name
            # Пропускаем residents — это не цех
            if module_id == "residents":
                continue

            self.slots.append(Slot(
                slot_id=module_id,
                module=module_id,
                label=info.get("label", module_id),
                enabled=True,
                order=info.get("priority", order * 10),
            ))
            order += 1''',
        new='''        # ЗАКОН КАРТРИДЖА: список слотов из сканера, не из info.json напрямую
        self.slots = []
        for cart in list_cartridges():
            self.slots.append(Slot(
                slot_id=cart["id"],
                module=cart["id"],
                label=cart["label"],
                enabled=True,
                order=cart["priority"],
            ))''',
        done="ЗАКОН КАРТРИДЖА: список слотов из сканера",
        requires=["S1"],
    ),
    dict(
        id="S3", file="studio/slot_manager.py",
        name="slot_manager: _load() синхронизирует slots.json с реальными картриджами",
        old='''        except Exception as e:
            print(f"[SLOTS] Ошибка загрузки slots.json: {e}")
            self._init_default_slots()''',
        new='''        except Exception as e:
            print(f"[SLOTS] Ошибка загрузки slots.json: {e}")
            self._init_default_slots()
            return

        # ЗАКОН КАРТРИДЖА: синхронизируем slots.json с реальными картриджами.
        # slots.json мог быть создан до появления нового цеха (trading и др.) —
        # добавляем недостающие, убираем исчезнувшие папки.
        known = {s.slot_id for s in self.slots}
        changed = False
        for cart in list_cartridges():
            if cart["id"] not in known:
                self.slots.append(Slot(
                    slot_id=cart["id"],
                    module=cart["id"],
                    label=cart["label"],
                    enabled=True,
                    order=cart["priority"],
                ))
                print(f"[SLOTS] + добавлен новый цех: {cart[\'id\']}")
                changed = True
        existing_ids = {cart["id"] for cart in list_cartridges()}
        before = len(self.slots)
        self.slots = [s for s in self.slots if s.slot_id in existing_ids or s.slot_id == "residents"]
        if len(self.slots) != before:
            print(f"[SLOTS] - убраны исчезнувшие цеха: {before - len(self.slots)}")
            changed = True
        if changed:
            self._save()''',
        done="ЗАКОН КАРТРИДЖА: синхронизируем slots.json",
        requires=["S1"],
    ),

    # ═══ studio/cartridge_manager/ui.py ═══════════════════════
    dict(
        id="CM1", file="studio/cartridge_manager/ui.py",
        name="cartridge_manager: список модулей через list_cartridges()",
        old='''    # Список всех доступных модулей (для кнопки «добавить»)
    available_modules = []
    if MODULES_DIR.exists():
        for d in sorted(MODULES_DIR.iterdir()):
            if d.is_dir() and d.name != "residents" and (d / "info.json").exists():
                available_modules.append(d.name)''',
        new='''    # ЗАКОН КАРТРИДЖА: список модулей через сканер, не через info.json
    from studio.modules_registry import list_cartridges as _lc
    available_modules = [c["id"] for c in _lc()]''',
        done="ЗАКОН КАРТРИДЖА: список модулей через сканер",
        requires=[],
    ),

    # ═══ studio/workshop/ui.py ════════════════════════════════
    dict(
        id="W1", file="studio/workshop/ui.py",
        name="workshop: _dept_runtype() только для цехов Студии (trading — в трейд-дашборде)",
        old='''def _dept_runtype(dept: str) -> str:
    """ЗАКОН КАРТРИДЖА: режим работы цеха.

    Сначала рабочие дефолты Шефа (словарь выше — они главнее манифеста:
    у video_long рабочий режим episode, а не full из манифеста),
    затем run_type из manifest.json картриджа — новый цех получает
    свой режим сам, без правок этого файла. Дефолт: social.
    """
    rt = DEPT_TO_RUNTYPE.get(dept)
    if rt:
        return rt
    from studio.modules_registry import get_cartridge
    cart = get_cartridge(dept)
    if cart and cart.get("run_type"):
        return cart["run_type"]
    return "social"''',
        new='''def _dept_runtype(dept: str) -> str:
    """Режим работы цеха Студии.

    Источник истины — словарь DEPT_TO_RUNTYPE выше (приоритет Шефа:
    video_long = episode, а не full из манифеста).
    Неизвестный цех → дефолт "social".
    Торговый Совет запускается из трейд-дашборда, не из Мастерской.
    """
    return DEPT_TO_RUNTYPE.get(dept, "social")''',
        done='Торговый Совет запускается из трейд-дашборда',
        requires=[],
    ),
]

SMOKE_TEST = r'''
import sys, pathlib
sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from studio.slot_manager import SlotManager
sm = SlotManager()
ids = [s.slot_id for s in sm.slots]
print(f"  SlotManager slots: {len(ids)}")
print("  ids:", ", ".join(ids))
assert "trading" in ids, "trading missing from SlotManager!"
t = next(s for s in sm.slots if s.slot_id == "trading")
print(f"  trading: label={t.label!r}, order={t.order}")

from studio.modules_registry import list_cartridges
cart_ids = [c["id"] for c in list_cartridges()]
assert "trading" in cart_ids, "trading not in list_cartridges!"
print(f"  cartridge_manager sees: {', '.join(cart_ids)}")

src = pathlib.Path("studio/workshop/ui.py").read_text(encoding="utf-8")
assert "trading-dashboard" in src or "dept_runtype" in src
print("  _dept_runtype: OK")

print()
print("Clean.")
'''


def main():
    if not Path("main.py").exists() or not Path("studio").exists():
        print("❌ Запускай из корня проекта (там где main.py).")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"cartridge_cleanup_{stamp}"

    texts: dict[str, str] = {}
    for fx in FIXES:
        f = fx["file"]
        if f in texts:
            continue
        p = Path(f)
        if not p.exists():
            print(f"❌ Файл не найден: {f}")
            return
        texts[f] = p.read_text(encoding="utf-8")

    status: dict[str, str] = {}
    applied, skipped, problems = [], [], []

    print("═" * 60)
    print("🧹 ЗАКОН КАРТРИДЖА — дочистка")
    print("═" * 60)

    for fx in FIXES:
        fid, f, name = fx["id"], fx["file"], fx["name"]
        t = texts[f]

        deps_ok = all(status.get(r) in ("applied", "done") for r in fx["requires"])
        if not deps_ok:
            status[fid] = "blocked"
            problems.append(f"🔒 [{fid}] {name} — заблокирована зависимостью")
            print(f"🔒 [{fid}] {name}")
            continue

        if fx["done"] in t:
            status[fid] = "done"
            skipped.append(fid)
            print(f"⏭  [{fid}] {name} — уже применено")
        elif fx["old"] in t:
            texts[f] = t.replace(fx["old"], fx["new"], 1)
            status[fid] = "applied"
            applied.append(fid)
            print(f"✏️  [{fid}] {name}")
        else:
            status[fid] = "missing"
            problems.append(f"❌ [{fid}] {name} — якорь не найден")
            print(f"❌ [{fid}] {name} — якорь не найден")

    if not applied:
        print("─" * 60)
        if problems:
            for p in problems:
                print("   " + p)
        else:
            print("✅ Уже чисто — патч не нужен.")
        return

    touched = sorted({fx["file"] for fx in FIXES if status.get(fx["id"]) == "applied"})
    backup_dir.mkdir(parents=True, exist_ok=True)
    print("─" * 60)
    for f in touched:
        dst = backup_dir / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        Path(f).write_text(texts[f], encoding="utf-8")
        print(f"📦 {f}")
    print(f"📦 Бэкапы: {backup_dir}")

    def rollback(reason: str):
        print(f"⛔ {reason} — откатываю...")
        for f in touched:
            shutil.copy2(backup_dir / f, f)
        print("↩️  Откат выполнен.")

    print("─" * 60)
    for f in touched:
        if not f.endswith(".py"):
            continue
        try:
            py_compile.compile(f, doraise=True)
            print(f"✅ {f}")
        except py_compile.PyCompileError as e:
            rollback(f"Ошибка компиляции {f}: {e}")
            return

    print("─" * 60)
    print("🔬 Смоук-тест:")
    r = subprocess.run([sys.executable, "-c", SMOKE_TEST],
                       capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr)
        rollback("Смоук-тест провален")
        return

    print("═" * 60)
    print(f"🧹 ГОТОВО: {len(applied)} правок, {len(skipped)} уже было, файлов: {len(touched)}")
    if problems:
        print("⚠️  Требуют внимания:")
        for p in problems:
            print("   " + p)
    print()
    print("Перезапусти main.py.")


if __name__ == "__main__":
    main()
