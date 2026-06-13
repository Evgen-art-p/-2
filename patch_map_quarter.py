import shutil, py_compile
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/cabinet/ui_cabinet.py")
BACKUP_DIR = Path("_patch_backups")

OLD = '''        # Дом: резиденты → Высотка, рабочие → Квартал Мастеров
        is_resident = agent.get("is_resident", False) or dept_id == "residents"
        home_keyword = "Высотка" if is_resident else "Квартал Мастеров"
        return _fuzzy_find(home_keyword)'''

NEW = '''        # Дом: резиденты → Высотка
        #      рабочие → квартал из manifest.json цеха (quarter)
        #      дефолт   → Квартал Мастеров
        # ЗАКОН ПАРЫ: знаем и агента и цех → берём квартал из манифеста
        is_resident = agent.get("is_resident", False) or dept_id == "residents"
        if is_resident:
            return _fuzzy_find("Высотка")
        # Спрашиваем манифест цеха — там уже лежит quarter (trading → Торговый Квартал)
        try:
            from studio.modules_registry import get_cartridge as _gc
            _cart = _gc(dept_id)
            _q = (_cart or {}).get("quarter", "")
            if _q:
                found = _fuzzy_find(_q)
                if found:
                    return found
        except Exception:
            pass
        return _fuzzy_find("Квартал Мастеров")'''

if not TARGET.exists():
    print("Файл не найден, запускай из корня проекта.")
    raise SystemExit

text = TARGET.read_text(encoding="utf-8")

if NEW.strip().split('\n')[1].strip() in text:
    print("Уже применено.")
    raise SystemExit

if OLD not in text:
    print("Якорь не найден — файл изменился.")
    raise SystemExit

BACKUP_DIR.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
bak = BACKUP_DIR / f"map_quarter_{stamp}_ui_cabinet.py"
shutil.copy2(TARGET, bak)
print(f"Бэкап: {bak}")

TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print("Правка применена.")

try:
    py_compile.compile(str(TARGET), doraise=True)
    print("Компиляция OK.")
except py_compile.PyCompileError as e:
    print(f"Ошибка компиляции, откатываю: {e}")
    shutil.copy2(bak, TARGET)
    raise SystemExit

print()
print("Готово. Перезапусти main.py.")
print("Искра появится в Торговом Квартале на карте.")
