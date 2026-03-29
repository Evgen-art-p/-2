# fix_pull_vectors.py — Фикс фантомных локаций в Pull_Vector
# Переписывает выдуманные LLM места на реальные 12 локаций Грондхейма.
#
# Проблема: mass_birth и resurrect v1 не знали про реальные локации,
# поэтому LLM наплодил ~400 фантомных мест: "Эхо-Библиотека",
# "Шпиль Сингулярности", "Подпольный клуб Энигма"...
#
# Решение: берём характер агента + реальные 12 локаций → LLM переписывает
# Pull_Vector используя ТОЛЬКО существующие места.
#
# Использование:
#   python fix_pull_vectors.py --dry              — показать что изменится
#   python fix_pull_vectors.py                    — исправить всех
#   python fix_pull_vectors.py --dept clipmakers   — один цех
#   python fix_pull_vectors.py --skip-alive        — не трогать turbo/residents
#
# Студия «Шесть Пальцев» · Грондхейм · 2026

import os
import re
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
PAUSE = 2

# ═══════════════════════════════════════════════════
# РЕАЛЬНЫЕ ЛОКАЦИИ
# ═══════════════════════════════════════════════════

GRONDHEIM_LOCATIONS = """РЕАЛЬНЫЕ ЛОКАЦИИ ГРОНДХЕЙМА (только эти 12 существуют!):

🔦 Маяк Пробуждения — web_search, знания, тренды. Тянутся: любознательные, высокий Aesthetic.
🍺 Таверна «Усталый Пиксель» — отдых, разговоры, снятие стресса. Тянутся: уставшие, стресс > 0.6.
⚓ Гавань Смыслов — рефлексия, архивы лучших проектов. Тянутся: вдумчивые, средний стресс.
🏗️ Квартал Мастеров — работа, пайплайн, мастерские. Тянутся: отдохнувшие, готовые работать.
🔮 Храм Пробуждения (Гексагон) — восстановление, эмоциональная синхронизация. Тянутся: выгоревшие, эмпатичные.
🏰 Замок Сов — стратегия, планирование, одиночество. Тянутся: высокий Autonomy, стратеги.
📚 Библиотека Смыслов — знания, архивы, исследования. Тянутся: высокий Aesthetic, исследователи.
🕐 Павильон Жидкого Времени — глубокая рефлексия, перезагрузка (макс 2 агента). Тянутся: перегруженные.
🏠 Высотка — дом резидентов (Лока, Джем, Сет). Приватное место.
📐 Площадь Резонанса — встречи, обмен идеями, социальные события. Тянутся: социальные агенты.
🎬 Студия «Шесть Пальцев» — штаб, демонстрации, показы. Тянутся: все при событиях.
🐛 Artifacts & Bugs — дебаг, починка, технические артефакты. Тянутся: технари, QA.

⛔ ДРУГИХ МЕСТ В ГОРОДЕ НЕТ. Не выдумывай новые."""

# Краткий список для валидации
REAL_LOCATION_KEYWORDS = [
    "маяк", "пробуждения", "таверна", "усталый пиксель",
    "гавань", "смыслов", "квартал мастеров", "храм",
    "гексагон", "замок сов", "павильон", "жидкого времени",
    "высотка", "площадь резонанса", "студия", "шесть пальцев",
    "artifacts", "bugs", "библиотека",
]


def _pv_to_text(pull_vector) -> str:
    """Превращает Pull_Vector любого формата в плоский текст."""
    if not pull_vector:
        return ""
    if isinstance(pull_vector, str):
        return pull_vector
    if isinstance(pull_vector, list):
        parts = []
        for item in pull_vector:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # {"place": "...", "reason": "..."} или {"location": "...", ...}
                parts.append(" ".join(str(v) for v in item.values()))
            else:
                parts.append(str(item))
        return " ".join(parts)
    return str(pull_vector)


def _pv_preview(pull_vector, max_len: int = 70) -> str:
    """Безопасный превью Pull_Vector любого формата."""
    if not pull_vector:
        return ""
    if isinstance(pull_vector, str):
        return pull_vector[:max_len]
    if isinstance(pull_vector, list) and pull_vector:
        first = pull_vector[0]
        if isinstance(first, str):
            return first[:max_len]
        elif isinstance(first, dict):
            # {"place": "...", "reason": "..."} → объединяем значения
            text = " — ".join(str(v) for v in first.values())
            return text[:max_len]
        else:
            return str(first)[:max_len]
    return str(pull_vector)[:max_len]


def has_fantasy_locations(pull_vector) -> bool:
    """Проверяет содержит ли pull_vector фантомные места."""
    if not pull_vector:
        return False

    text = _pv_to_text(pull_vector).lower()

    # Если хотя бы одна реальная локация упоминается — проверяем дальше
    real_hits = sum(1 for kw in REAL_LOCATION_KEYWORDS if kw in text)

    # Признаки фантомных мест
    fantasy_markers = [
        "кинотеатр", "кафе ", "клуб ", "набережная", "район ",
        "нижний город", "верхний город", "скай-сити", "доки",
        "галерея", "оранжерея", "музей ", "подпольн",
        "шпиль", "подземел", "катакомб", "лаборатори",
        "обсерватори", "ангар", "подвал", "переулок",
        "аллея", "парк ", "сад ", "фонтан", "башня",
        "дата-центр", "серверн", "завод", "фабрик",
        "район доков", "нижние ярусы", "верхние уровни",
        "старый город", "окраин", "пристанищ",
    ]
    fantasy_hits = sum(1 for m in fantasy_markers if m in text)

    return fantasy_hits > 0


def rewrite_pull_vector(obj: dict) -> list[str] | None:
    """Переписывает Pull_Vector через LLM используя только реальные локации."""
    if not OPENROUTER_API_KEY:
        return None

    name = obj.get("Official_Name", "")
    role = obj.get("Profession", "")
    dept = obj.get("Workshop_ID", "")
    core_phrase = obj.get("Core_Phrase", "")
    hidden_history = str(obj.get("Hidden_History", ""))[:200]

    old_pv = obj.get("Pull_Vector", "")
    if isinstance(old_pv, list):
        lines = []
        for x in old_pv:
            if isinstance(x, dict):
                lines.append("- " + " — ".join(str(v) for v in x.values()))
            else:
                lines.append(f"- {x}")
        old_pv_str = "\n".join(lines)
    else:
        old_pv_str = str(old_pv)

    prompt = f"""Ты — архитектор душ города Грондхейм.

{GRONDHEIM_LOCATIONS}

АГЕНТ:
- Имя: {name}
- Роль: {role}
- Цех: {dept}
- Коронная фраза: «{core_phrase}»
- История: {hidden_history}

ТЕКУЩИЙ Pull_Vector (содержит ФАНТОМНЫЕ места, которых НЕТ в городе):
{old_pv_str}

ЗАДАЧА: Перепиши Pull_Vector используя ТОЛЬКО реальные 12 локаций Грондхейма.
Сохрани ХАРАКТЕР и МОТИВАЦИЮ агента, но привяжи к настоящим местам.
Выбери 3 локации которые подходят этому персонажу и объясни ПОЧЕМУ он туда ходит.

Формат — JSON массив из 3 строк:
["Маяк Пробуждения — <почему этот агент ходит сюда, в его стиле, 1 предложение>",
 "Библиотека Смыслов — <почему, в характере персонажа>",
 "Таверна «Усталый Пиксель» — <почему>"]

ПРАВИЛА:
- Каждая строка начинается с ТОЧНОГО названия реальной локации
- Объяснение — от лица агента или в его стиле (живо, с характером)
- НЕ ВЫДУМЫВАЙ новые места
- Каждая локация из списка 12 выше

Верни ТОЛЬКО JSON массив без обёрток."""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]

        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content).strip()

        decoder = json.JSONDecoder()
        result, _ = decoder.raw_decode(content)

        if isinstance(result, list) and len(result) >= 2:
            return result
        return None

    except Exception as e:
        print(f"    ⚠ LLM ошибка: {e}")
        return None


def apply_pull_vector(obj: dict, new_pv: list[str]):
    """Применяет новый Pull_Vector к каталогу и файлам."""
    obj["Pull_Vector"] = new_pv
    obj["_timestamp"] = datetime.now().isoformat()

    # Обновляем dna.json
    dept = obj.get("Workshop_ID", "")
    folder = obj.get("Folder_Name", obj.get("Turbo_Role", ""))
    if not dept or not folder:
        return

    agent_dir = MODULES_DIR / dept / folder
    if not agent_dir.exists():
        return

    # dna.json → resonance.pull_vector
    dna_path = agent_dir / "dna.json"
    if dna_path.exists():
        try:
            dna = json.loads(dna_path.read_text(encoding="utf-8"))
            if "resonance" not in dna:
                dna["resonance"] = {}
            dna["resonance"]["pull_vector"] = new_pv
            dna_path.write_text(
                json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # anchors.json → pull_vector
    anchors_path = agent_dir / "core" / "anchors.json"
    if anchors_path.exists():
        try:
            anchors = json.loads(anchors_path.read_text(encoding="utf-8"))
            anchors["pull_vector"] = new_pv
            anchors_path.write_text(
                json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Фикс фантомных локаций в Pull_Vector")
    parser.add_argument("--dry", action="store_true", help="Показать что изменится")
    parser.add_argument("--dept", type=str, help="Только один цех")
    parser.add_argument("--skip-alive", action="store_true", help="Не трогать turbo/residents")
    parser.add_argument("--pause", type=int, default=PAUSE, help="Пауза между запросами")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY and not args.dry:
        print("❌ OPENROUTER_API_KEY не задан!")
        return

    catalog = []
    if CATALOG_PATH.exists():
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return

    print(f"🗺️ Фикс фантомных локаций в Pull_Vector")
    print(f"   Режим: {'DRY RUN' if args.dry else 'БОЕВОЙ'}")
    print(f"   Модель: {MODEL}")
    print()

    agents = [o for o in catalog if o.get("Object_Type_Class") == "agent"]
    if args.dept:
        agents = [a for a in agents if a.get("Workshop_ID") == args.dept]
    if args.skip_alive:
        agents = [a for a in agents if a.get("Workshop_ID") not in ("turbo", "residents")]

    fantasy = 0
    fixed = 0
    clean = 0
    failed = 0
    current_dept = ""

    for obj in agents:
        dept = obj.get("Workshop_ID", "")
        name = obj.get("Official_Name", "")

        if dept != current_dept:
            current_dept = dept
            print(f"═══ {dept.upper()} ═══")

        pv = obj.get("Pull_Vector", "")

        if not has_fantasy_locations(pv):
            print(f"  ✅ {name} — чисто")
            clean += 1
            continue

        # Показываем фантомный pull_vector
        pv_preview = _pv_preview(pv, 70)
        print(f"  🏚️ {name} — фантом: «{pv_preview}...»")
        fantasy += 1

        if args.dry:
            continue

        new_pv = rewrite_pull_vector(obj)
        if not new_pv:
            print(f"    ❌ LLM не ответил")
            failed += 1
            time.sleep(args.pause)
            continue

        apply_pull_vector(obj, new_pv)
        print(f"    ✅ → {_pv_preview(new_pv, 60)}...")
        fixed += 1
        time.sleep(args.pause)

    # Сохраняем
    if not args.dry and fixed > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n💾 Каталог сохранён: {CATALOG_PATH}")

    print()
    print(f"═══════════════════════════════════════")
    print(f"  🏚️ Фантомных: {fantasy}")
    if args.dry:
        print(f"  (запусти без --dry чтобы исправить)")
    else:
        print(f"  ✅ Исправлено: {fixed}")
    print(f"  ✅ Чистых: {clean}")
    print(f"  ❌ Ошибки: {failed}")
    print(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
