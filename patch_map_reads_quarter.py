# patch_map_reads_quarter.py
# ═══════════════════════════════════════════════════════════════
# КАРТА ЧИТАЕТ QUARTER — финальный провод
#
# Проблема: patch_quarter_field.py положил Quarter в каталог и
# научил Страницу Жизни его писать — но КАРТА его не читает.
# _find_agent_zone() в ui_cabinet.py вычисляет дом хардкодом:
#   резидент → Высотка, все остальные → Квартал Мастеров.
# Работу — тоже хардкодом: всегда «Студия».
# Поэтому Искра (trading) валится в Квартал Мастеров — «общак».
#
# Что делает патч: переписывает _find_agent_zone() так, чтобы
# дом и работа брались из Quarter агента по карте кварталов:
#
#   Квартал           Дом                  Работа
#   ───────────────── ──────────────────── ──────────────────
#   Квартал Мастеров  Квартал Мастеров     Студия «Шесть Пальцев»
#   Высотка/резидент  Высотка              Студия «Шесть Пальцев»
#   Торговый Квартал  Торговый Квартал     Биржа
#
# Quarter агента читается из dna.json, а при отсутствии (старые
# агенты, рождённые до patch_quarter_field) — из каталога по ID.
#
# Запуск: python patch_map_reads_quarter.py
# ═══════════════════════════════════════════════════════════════

import shutil
import py_compile
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/cabinet/ui_cabinet.py")
BACKUP_DIR = Path("_patch_backups")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Старый текст функции (дословно) ──────────────────────────────
OLD_FUNC = '''    def _find_agent_zone(agent, dept_id, last_walk_loc, locations_by_name):
        """Определить в какой зоне находится агент.
        Приоритет: работает в цеху → Студия > свежая прогулка (< 30 мин) > дом.
        Резиденты → Высотка, рабочие → Квартал Мастеров.
        """
        def _fuzzy_find(keyword):
            """Найти локацию по вхождению ключевого слова."""
            kw = keyword.lower().strip().rstrip(".")
            for loc_name, loc in locations_by_name.items():
                clean = loc_name.lower().strip().rstrip(".")
                if kw in clean or clean in kw:
                    return loc
            return None

        # ── РАБОЧИЙ СТАТУС: агент в цеху → всегда в Студии ──────
        try:
            from studio.city_pulse import is_agent_working as _iaw
            # ПАТЧ city_red №3: пульс хранит worker_id (A01..) + dept
            _aid_w = agent.get("id") or agent.get("ID_Object", "")
            _work = _iaw(_aid_w, dept=dept_id)
            if _work:
                studio_loc = _fuzzy_find("Студия")
                if studio_loc:
                    return studio_loc
        except Exception:
            pass
        # ── END РАБОЧИЙ СТАТУС ──

        # Если агент гулял — проверяем свежесть прогулки
        if last_walk_loc:
            # Парсим время из формата "[2026-03-23 17:50] Локация: ..."
            try:
                import re as _re
                m = _re.match(r'\\[(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2})\\]', last_walk_loc)
                if m:
                    walk_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
                    minutes_ago = (datetime.now() - walk_time).total_seconds() / 60
                    if minutes_ago < 30:
                        # Ещё гуляет — показываем в локации прогулки
                        # Извлекаем название локации после "]"
                        loc_part = last_walk_loc.split("]", 1)[-1].split(":")[0].strip()
                        found = _fuzzy_find(loc_part)
                        if found:
                            return found
                    # Прогулка старше 30 мин — вернулся домой
            except Exception:
                pass

        # Дом: резиденты → Высотка, рабочие → Квартал Мастеров
        is_resident = agent.get("is_resident", False) or dept_id == "residents"
        home_keyword = "Высотка" if is_resident else "Квартал Мастеров"
        return _fuzzy_find(home_keyword)'''


# ── Новый текст функции ──────────────────────────────────────────
NEW_FUNC = '''    # Карта кварталов: Quarter агента → (домашняя зона, рабочая зона)
    # Дом — где агент отдыхает; Работа — куда идёт на ран.
    # Берётся из Quarter (dna.json или каталог), не из хардкода.
    _QUARTER_HOME_WORK = {
        "Квартал Мастеров": ("Квартал Мастеров", "Студия"),
        "Высотка":          ("Высотка", "Студия"),
        "Торговый Квартал": ("Торговый Квартал", "Биржа"),
    }

    def _agent_quarter(agent, dept_id):
        """Quarter агента: сначала dna.json, потом каталог по ID. Иначе ''."""
        aid = agent.get("id") or agent.get("ID_Object", "")
        # 1. dna.json (пишется при рождении после patch_quarter_field)
        try:
            from studio.cabinet.agents import _get_agent_dna as _gad
            q = (_gad(aid, dept_id) or {}).get("quarter", "")
            if q:
                return q
        except Exception:
            pass
        # 2. Каталог по ID_Object (старые агенты без quarter в dna)
        try:
            from studio.cabinet.agents import _load_registry_cache as _lrc
            for obj in _lrc():
                if obj.get("Object_Type_Class") != "agent":
                    continue
                oid = obj.get("ID_Object", "")
                # Матч по точному ID или по совпадению хвоста (A01 ↔ A01_ISKRA)
                if oid == aid or oid.startswith(aid + "_") or oid.endswith("_" + aid):
                    return obj.get("Quarter", "")
        except Exception:
            pass
        return ""

    def _find_agent_zone(agent, dept_id, last_walk_loc, locations_by_name):
        """Определить в какой зоне находится агент.
        Приоритет: работает → рабочая зона квартала > свежая прогулка (< 30 мин) > дом.
        Дом и работа берутся из Quarter агента (не из хардкода).
        """
        def _fuzzy_find(keyword):
            """Найти локацию по вхождению ключевого слова."""
            if not keyword:
                return None
            kw = keyword.lower().strip().rstrip(".")
            for loc_name, loc in locations_by_name.items():
                clean = loc_name.lower().strip().rstrip(".")
                if kw in clean or clean in kw:
                    return loc
            return None

        # Quarter агента → домашняя и рабочая зоны
        is_resident = agent.get("is_resident", False) or dept_id == "residents"
        quarter = _agent_quarter(agent, dept_id)
        if not quarter:
            quarter = "Высотка" if is_resident else "Квартал Мастеров"
        home_kw, work_kw = _QUARTER_HOME_WORK.get(
            quarter, ("Квартал Мастеров", "Студия")
        )

        # ── РАБОЧИЙ СТАТУС: агент на ране → рабочая зона своего квартала ──
        try:
            from studio.city_pulse import is_agent_working as _iaw
            # ПАТЧ city_red №3: пульс хранит worker_id (A01..) + dept
            _aid_w = agent.get("id") or agent.get("ID_Object", "")
            _work = _iaw(_aid_w, dept=dept_id)
            if _work:
                work_loc = _fuzzy_find(work_kw)
                if work_loc:
                    return work_loc
        except Exception:
            pass
        # ── END РАБОЧИЙ СТАТУС ──

        # Если агент гулял — проверяем свежесть прогулки
        if last_walk_loc:
            # Парсим время из формата "[2026-03-23 17:50] Локация: ..."
            try:
                import re as _re
                m = _re.match(r'\\[(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2})\\]', last_walk_loc)
                if m:
                    walk_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
                    minutes_ago = (datetime.now() - walk_time).total_seconds() / 60
                    if minutes_ago < 30:
                        # Ещё гуляет — показываем в локации прогулки
                        # Извлекаем название локации после "]"
                        loc_part = last_walk_loc.split("]", 1)[-1].split(":")[0].strip()
                        found = _fuzzy_find(loc_part)
                        if found:
                            return found
                    # Прогулка старше 30 мин — вернулся домой
            except Exception:
                pass

        # Дом: домашняя зона квартала агента
        home = _fuzzy_find(home_kw)
        if home:
            return home
        # Фоллбэк — сам квартал как зона (если домашней локации нет)
        return _fuzzy_find(quarter)'''


def main():
    print("═" * 60)
    print("ПАТЧ — КАРТА ЧИТАЕТ QUARTER")
    print("═" * 60)

    if not TARGET.exists():
        print(f"❌ {TARGET} не найден. Запускай из корня проекта.")
        return

    text = TARGET.read_text(encoding="utf-8")

    # Идемпотентность
    if "_QUARTER_HOME_WORK" in text:
        print("✅ Карта уже читает Quarter — патч не нужен.")
        return

    if OLD_FUNC not in text:
        print("❌ Якорная функция _find_agent_zone не найдена дословно.")
        print("   Файл мог измениться. Нужна ручная правка.")
        return

    # Бэкап
    BACKUP_DIR.mkdir(exist_ok=True)
    bak = BACKUP_DIR / f"ui_cabinet.py.bak_quarter_map_{STAMP}"
    shutil.copy2(TARGET, bak)
    print(f"📦 Бэкап: {bak}")

    # Замена
    text = text.replace(OLD_FUNC, NEW_FUNC, 1)
    TARGET.write_text(text, encoding="utf-8")
    print("✏️  _find_agent_zone переписана: дом и работа из Quarter")

    # Компиляция
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("✅ Компиляция OK")
    except py_compile.PyCompileError as e:
        print(f"❌ Ошибка компиляции, откатываю: {e}")
        shutil.copy2(bak, TARGET)
        return

    print()
    print("═" * 60)
    print("ГОТОВО. Перезапусти студию → карта в Кабинете:")
    print("• Искра отдыхает → Торговый Квартал")
    print("• Искра на ране → Биржа")
    print("• Студийные дома → Квартал Мастеров, на ране → Студия")
    print("• Резиденты дома → Высотка, на ране → Студия")
    print()
    print("Quarter берётся из dna.json (новые агенты) или каталога")
    print("(старые, как Искра — рождённые до patch_quarter_field).")
    print("═" * 60)


if __name__ == "__main__":
    main()
