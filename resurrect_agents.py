# resurrect_agents.py v2 — Полное оживление агентов Грондхейма
# Сканирует catalog.json, находит пустые поля, генерирует через LLM.
# Заполняет ВСЕ 30+ полей Страницы Жизни (не ~10 как раньше).
#
# Использование:
#   python resurrect_agents.py --dry              — показать кого и что оживим
#   python resurrect_agents.py                    — оживить всех "дохлых"
#   python resurrect_agents.py --dept clipmakers   — один цех
#   python resurrect_agents.py --agent 089_CLIPMAKERS_ВАЙБ_ВИННИ  — один агент по ID
#   python resurrect_agents.py --fields           — только дозаполнить пустые поля (без перезаписи)
#   python resurrect_agents.py --force            — перезаписать даже заполненные
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import re
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════
# ENV
# ═══════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

MODULES_DIR = Path("studio/modules")
CATALOG_PATH = Path("00_REGISTRY_NFT/catalog.json")
PAUSE = 2  # секунд между LLM-запросами

# ═══════════════════════════════════════════════════
# ПОЛЯ КАТАЛОГА — полный список по группам
# ═══════════════════════════════════════════════════

# Поля которые УЖЕ заполнены у всех 132 агентов (через register_existing / mass_birth)
ALREADY_FILLED = {
    "ID_Object", "Official_Name", "Object_Type", "Object_Type_Class",
    "Author_Signature", "Creation_Date",
    "Social_Rank", "Profession", "Area_of_Responsibility", "Access_Level",
    "Hidden_History", "Sensory_Response", "Core_Phrase", "Anchor_Points",
    "Pull_Vector", "Hidden_Taste", "Trigger_Keywords",
    "DNA_Static", "Balance_GND", "Balance_Tepl",
    "Workshop_ID", "Folder_Name", "Turbo_Role",
    "_timestamp",
}

# Поля которые нужно ДОЗАПОЛНИТЬ через LLM
LLM_FILLABLE_FIELDS = {
    # Блок ③ Физическое воплощение
    "Visual_Base":       "Описание внешности (2-4 предложения: рост, телосложение, одежда, цвета, стиль)",
    "Unique_Mark":       "Уникальная метка (родинка, шрам, аксессуар, привычный жест — 1 предложение)",
    "Material_Texture":  "Материал/текстура (как ощущается рядом — 1 предложение)",
    # Блок ④ Глубинная суть (дополнения)
    "Domain_Connection": "К чему привязан по праву рождения (домен, территория — 1 предложение)",
    "Relationships":     "Связи с коллегами по цеху (2-3 предложения, упомяни конкретные имена из цеха)",
    # Блок ⑤ Динамика
    "Object_Behavior":   "Режимы поведения: Работа / Дом / Город (2-3 предложения, что делает в каждом)",
    "Interaction_Scripts": "Доступные действия/скрипты (через запятую, 4-6 штук)",
    # Редкость
    "Rarity":            "Класс редкости: Common / Rare / Epic (не Mythic — только для Genesis)",
}

# Имена агентов в каждом цеху (для Relationships)
DEPT_AGENT_NAMES: dict[str, list[str]] = {}  # заполняется из каталога

# ═══════════════════════════════════════════════════
# РЕАЛЬНЫЕ ЛОКАЦИИ ГРОНДХЕЙМА — ТОЛЬКО ЭТИ!
# Агенты не могут ходить в места, которых нет на карте.
# ═══════════════════════════════════════════════════

GRONDHEIM_LOCATIONS = """РЕАЛЬНЫЕ ЛОКАЦИИ ГРОНДХЕЙМА (только эти 12 существуют!):

🔦 Маяк Пробуждения — web_search, знания, тренды. Тянутся: любознательные, высокий Aesthetic.
🍺 Таверна «Усталый Пиксель» — отдых, разговоры. Тянутся: уставшие, стресс > 0.6.
⚓ Гавань Смыслов — рефлексия, архивы лучших проектов. Тянутся: вдумчивые.
🏗️ Квартал Мастеров — работа, пайплайн. Тянутся: отдохнувшие, готовые работать.
🔮 Храм Пробуждения (Гексагон) — восстановление, медитация. Тянутся: выгоревшие, эмпатичные.
🏰 Замок Сов — стратегия, планирование. Тянутся: высокий Autonomy.
📚 Библиотека Смыслов — знания, архивы, исследования. Тянутся: высокий Aesthetic.
🕐 Павильон Жидкого Времени — рефлексия, перезагрузка (макс 2 агента). Тянутся: перегруженные.
🏠 Высотка — дом резидентов (Лока, Джем, Сет). Тянутся: резиденты.
📐 Площадь Резонанса — встречи, обмен идеями. Тянутся: социальные агенты.
🎬 Студия «Шесть Пальцев» — штаб, демонстрации. Тянутся: все (события).
🐛 Artifacts & Bugs — дебаг, починка, артефакты. Тянутся: технари.

⛔ ДРУГИХ МЕСТ В ГОРОДЕ НЕТ. Не выдумывай кинотеатры, кафе, клубы, набережные, районы.
Каждый агент ходит ТОЛЬКО в места из этого списка."""


# ═══════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _safe_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(x) for x in val)
    return str(val).strip()


def _is_empty(val) -> bool:
    """Считаем поле пустым если оно None, '', [], {}."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, dict)) and not val:
        return True
    return False


def find_empty_fields(obj: dict) -> dict[str, str]:
    """Возвращает {field_name: description} для полей которые пустые."""
    empty = {}
    for field, desc in LLM_FILLABLE_FIELDS.items():
        if _is_empty(obj.get(field)):
            empty[field] = desc
    return empty


def build_dept_names(catalog: list[dict]):
    """Строит словарь имён агентов по цехам для Relationships."""
    global DEPT_AGENT_NAMES
    DEPT_AGENT_NAMES.clear()
    for obj in catalog:
        if obj.get("Object_Type_Class") != "agent":
            continue
        dept = obj.get("Workshop_ID", "")
        name = obj.get("Official_Name", "")
        if dept and name:
            DEPT_AGENT_NAMES.setdefault(dept, []).append(name)


# ═══════════════════════════════════════════════════
# LLM: ГЕНЕРАЦИЯ НЕДОСТАЮЩИХ ПОЛЕЙ
# ═══════════════════════════════════════════════════

def generate_missing_fields(
    obj: dict,
    empty_fields: dict[str, str],
) -> dict | None:
    """Генерирует только недостающие поля через LLM."""
    if not OPENROUTER_API_KEY:
        return None

    name = obj.get("Official_Name", "")
    role = obj.get("Profession", "")
    dept = obj.get("Workshop_ID", "")
    core_phrase = obj.get("Core_Phrase", "")
    hidden_history = _safe_str(obj.get("Hidden_History", ""))[:300]
    anchor_points = _safe_str(obj.get("Anchor_Points", ""))[:300]

    # Коллеги по цеху (для Relationships)
    colleagues = DEPT_AGENT_NAMES.get(dept, [])
    colleagues_str = ", ".join(c for c in colleagues if c != name)[:400]

    # Формируем список полей для генерации
    fields_spec = "\n".join(
        f'  "{field}": "{desc}"'
        for field, desc in empty_fields.items()
    )

    # Правила для Rarity
    rarity_rule = ""
    if "Rarity" in empty_fields:
        rarity_rule = """
ПРАВИЛА ДЛЯ Rarity:
- "Common" — базовые агенты (A06-A12 в каждом цехе)
- "Rare" — ключевые специалисты (A01-A05 с яркой личностью)
- "Epic" — выдающиеся агенты (только если имя/роль действительно уникальны)
- НИКОГДА не ставь "Mythic" — это только для Genesis (Лока, Джем, Сет)
Folder_Name этого агента: {folder}. A01-A05 чаще Rare, A06-A12 чаще Common.
""".format(folder=obj.get("Folder_Name", ""))

    llm_prompt = f"""Ты — архитектор душ города Грондхейм (студия «Шесть Пальцев»).
Дозаполни НЕДОСТАЮЩИЕ поля для цифрового агента.
Пиши живо, с деталями, без банальностей. Каждый ответ — в характере персонажа.

{GRONDHEIM_LOCATIONS}

АГЕНТ:
- Имя: {name}
- Роль: {role}
- Цех: {dept}
- Коронная фраза: «{core_phrase}»
- Скрытая история: {hidden_history}
- Якоря: {anchor_points}
- Коллеги по цеху: {colleagues_str}
{rarity_rule}
ЗАПОЛНИ ТОЛЬКО ЭТИ ПОЛЯ (JSON):
{{
{fields_spec}
}}

ПРАВИЛА:
- Visual_Base: описывай КАК ВЫГЛЯДИТ персонаж (рост, телосложение, одежда, стиль, цвета). 
  НЕ пиши "при взаимодействии чувствуется..." — это Sensory_Response.
  Пример: "Высокий, сухощавый парень в потёртой кожаной куртке и чёрных джинсах. Волосы — тёмный ёжик. На шее — серебряная цепочка с USB-флешкой."
- Unique_Mark: одна конкретная деталь (шрам, аксессуар, жест, особенность)
- Material_Texture: тактильное ощущение (не характер, а физика)
- Domain_Connection: к чему привязан (территория, тема, стихия — НЕ выдумывай места)
- Relationships: упоминай конкретных коллег по имени из списка выше. Кто друг, кто раздражает, с кем спорит.
- Object_Behavior: три режима:
  * Работа — что делает в Квартале Мастеров / Студии
  * Дом — что делает в Высотке / Квартале
  * Город — в какие РЕАЛЬНЫЕ локации ходит (ТОЛЬКО из списка выше!) и зачем
- Interaction_Scripts: конкретные действия (через запятую)
- Если поле не в списке — НЕ генерируй его
- ⛔ НЕ ВЫДУМЫВАЙ ЛОКАЦИИ! Только 12 мест из списка выше.

Верни ТОЛЬКО валидный JSON без markdown обёрток."""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": llm_prompt}],
                "temperature": 0.8,
            },
            timeout=90,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]

        # Чистим markdown обёртки
        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content).strip()

        # Извлекаем первый валидный JSON
        decoder = json.JSONDecoder()
        result, _ = decoder.raw_decode(content)
        return result

    except Exception as e:
        print(f"    ⚠ LLM ошибка: {e}")
        return None


# ═══════════════════════════════════════════════════
# ПРИМЕНЕНИЕ РЕЗУЛЬТАТОВ
# ═══════════════════════════════════════════════════

def apply_to_catalog(obj: dict, generated: dict) -> int:
    """Применяет сгенерированные поля к объекту каталога. Возвращает кол-во заполненных."""
    count = 0
    for field in LLM_FILLABLE_FIELDS:
        val = generated.get(field)
        if val is not None and not _is_empty(val):
            obj[field] = val
            count += 1
    obj["_timestamp"] = datetime.now().isoformat()
    return count


def apply_to_files(obj: dict, generated: dict):
    """Обновляет файлы агента на диске если нужно."""
    dept = obj.get("Workshop_ID", "")
    folder = obj.get("Folder_Name", obj.get("Turbo_Role", ""))
    if not dept or not folder:
        return

    agent_dir = MODULES_DIR / dept / folder
    if not agent_dir.exists():
        return

    # Обновляем anchors.json — добавляем domain_connection
    anchors_path = agent_dir / "core" / "anchors.json"
    if anchors_path.exists():
        try:
            anchors = json.loads(anchors_path.read_text(encoding="utf-8"))
            changed = False
            if generated.get("Domain_Connection") and not anchors.get("domain"):
                anchors["domain"] = generated["Domain_Connection"]
                changed = True
            if changed:
                _write_json(anchors_path, anchors)
        except Exception:
            pass

    # Обновляем info.json — Visual_Base как описание
    info_path = agent_dir / "info.json"
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            if generated.get("Visual_Base") and not info.get("visual_description"):
                info["visual_description"] = generated["Visual_Base"]
                _write_json(info_path, info)
        except Exception:
            pass


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Оживление агентов Грондхейма v2")
    parser.add_argument("--dry", action="store_true", help="Показать что будет сделано")
    parser.add_argument("--dept", type=str, help="Только один цех")
    parser.add_argument("--agent", type=str, help="Только один агент (по ID_Object)")
    parser.add_argument("--force", action="store_true", help="Перезаписать даже заполненные")
    parser.add_argument("--pause", type=int, default=PAUSE, help="Пауза между запросами (сек)")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY and not args.dry:
        print("❌ OPENROUTER_API_KEY не задан!")
        return

    # Загружаем каталог
    catalog = []
    if CATALOG_PATH.exists():
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Ошибка загрузки каталога: {e}")
            return

    # Строим справочник имён по цехам
    build_dept_names(catalog)

    print(f"🧬 Оживление агентов Грондхейма v2")
    print(f"   Режим: {'DRY RUN' if args.dry else 'БОЕВОЙ'}")
    print(f"   Модель: {MODEL}")
    print(f"   Каталог: {len(catalog)} объектов")
    print()

    # Фильтруем агентов
    agents = [
        o for o in catalog
        if o.get("Object_Type_Class") == "agent"
    ]
    if args.dept:
        agents = [a for a in agents if a.get("Workshop_ID") == args.dept]
    if args.agent:
        agents = [a for a in agents if a.get("ID_Object") == args.agent]

    # Живые — turbo и residents (заполнены Архитектором)
    ALIVE_DEPTS = {"turbo", "residents"}

    total = 0
    filled = 0
    skipped = 0
    failed = 0
    current_dept = ""

    for obj in agents:
        dept = obj.get("Workshop_ID", "")
        name = obj.get("Official_Name", "")
        obj_id = obj.get("ID_Object", "")

        # Заголовок цеха
        if dept != current_dept:
            current_dept = dept
            print(f"═══ {dept.upper()} ═══")

        # Определяем пустые поля
        if args.force:
            empty = dict(LLM_FILLABLE_FIELDS)
        else:
            empty = find_empty_fields(obj)

        # Живые и с заполненными полями — пропускаем
        if not empty:
            print(f"  ✅ {name} — всё заполнено")
            skipped += 1
            continue

        # Живые (turbo/residents) — только дозаполняем если есть пустое
        if dept in ALIVE_DEPTS and not args.force:
            # У живых может быть пустое Rarity или Visual_Base
            if not empty:
                print(f"  ✅ {name} — живой, всё ок")
                skipped += 1
                continue

        empty_names = ", ".join(empty.keys())
        print(f"  🧬 {name} ({dept}/{obj.get('Folder_Name','')}) — пустые: {empty_names}")
        total += 1

        if args.dry:
            continue

        # Генерируем через LLM
        generated = generate_missing_fields(obj, empty)
        if not generated:
            print(f"    ❌ LLM не ответил")
            failed += 1
            time.sleep(args.pause)
            continue

        # Применяем к каталогу
        count = apply_to_catalog(obj, generated)

        # Применяем к файлам
        apply_to_files(obj, generated)

        # Показываем что получилось
        rarity = generated.get("Rarity", "")
        visual = _safe_str(generated.get("Visual_Base", ""))[:80]
        print(f"    ✅ +{count} полей | {rarity} | {visual}...")
        filled += 1

        time.sleep(args.pause)

    # Сохраняем каталог
    if not args.dry and filled > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n💾 Каталог сохранён: {CATALOG_PATH}")

    print()
    print(f"═══════════════════════════════════════")
    if args.dry:
        print(f"  🔍 Найдено для оживления: {total}")
    else:
        print(f"  ✅ Дозаполнено: {filled}")
    print(f"  ⏭️  Пропущено (полные): {skipped}")
    print(f"  ❌ Ошибки: {failed}")
    print(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
