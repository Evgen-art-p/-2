# studio/grondheim_memory.py — Ядро памяти Грондхейма
# Три слоя: Якоря · Оперативный · Резонансный
# + Геопозиция Смыслов · Loka-Filter
#
# НЕ заменяет workshop/memory.py (рабочая память о клиентах).
# Это ЛИЧНАЯ память агента — о себе, о коллегах, о городе.
#
# Студия «Шесть Пальцев» · 2026

"""
╔══════════════════════════════════════════════════════════════╗
║  GRONDHEIM MEMORY ENGINE                                     ║
║  Три слоя памяти агента:                                     ║
║    1. Якоря (Anchor Points) — вечные константы               ║
║    2. Оперативный (Sensory) — быт, 30-дневное затухание      ║
║    3. Резонансный (Resonance) — отношения, события, Loka     ║
║  + Геопозиция Смыслов — инжект локации в промпт              ║
║  + format_soul_for_agent() — сборка души для pipeline         ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

MODULES_DIR = Path("studio/modules")

# Сенсорная память: макс записей в оперативном слое
SENSORY_MAX_ENTRIES = 20
# Сенсорная память: дней до затухания
SENSORY_DECAY_DAYS = 30
# Резонансный слой: макс значимых событий
RESONANCE_MAX_EVENTS = 100
# Эмоциональные веса: порог затухания (ниже — уходит в архив)
EMOTIONAL_DECAY_THRESHOLD = 0.05
# Резюме: макс длина при сжатии оперативки
SUMMARY_MAX_CHARS = 500


# ═══════════════════════════════════════════════════════════
# PATH HELPERS
# ═══════════════════════════════════════════════════════════

_AGENT_DIR_CACHE: dict[str, Path] = {}


def _find_agent_dir(agent_id: str, dept: str = "") -> Optional[Path]:
    """
    Находит папку агента по ЛЮБОМУ его идентификатору:
      - имя папки (002_GENESIS_CREATOR)
      - info.json → id (administrator)
      - info.json → registry_id (002_GENESIS_CREATOR)
      - info.json → avatar (JEM)
      - info.json → label (Джем)
      - dna.json → id (002_GENESIS_CREATOR)

    Кеширует результат — повторный поиск моментальный.
    """
    # Проверяем кеш
    cache_key = f"{dept}:{agent_id}"
    if cache_key in _AGENT_DIR_CACHE:
        cached = _AGENT_DIR_CACHE[cache_key]
        if cached.exists():
            return cached

    # Определяем где искать
    if dept:
        search_dirs = [MODULES_DIR / dept] if (MODULES_DIR / dept).exists() else []
    else:
        if not MODULES_DIR.exists():
            return None
        search_dirs = [d for d in MODULES_DIR.iterdir() if d.is_dir()]

    agent_id_upper = agent_id.upper()

    for dept_dir in search_dirs:
        for d in dept_dir.iterdir():
            if not d.is_dir():
                continue

            # 1. Совпадение по имени папки (точное или case-insensitive)
            if d.name == agent_id or d.name.upper() == agent_id_upper:
                _AGENT_DIR_CACHE[cache_key] = d
                return d

            # 2. Совпадение по полям info.json
            info_path = d / "info.json"
            if info_path.exists():
                try:
                    info = json.loads(info_path.read_text(encoding="utf-8"))
                    match_fields = [
                        info.get("id", ""),
                        info.get("registry_id", ""),
                        info.get("avatar", ""),
                        info.get("label", ""),
                    ]
                    for field in match_fields:
                        if field and (field == agent_id or field.upper() == agent_id_upper):
                            _AGENT_DIR_CACHE[cache_key] = d
                            return d
                except Exception:
                    pass

            # 3. Совпадение по dna.json → id
            dna_path = d / "dna.json"
            if dna_path.exists():
                try:
                    dna = json.loads(dna_path.read_text(encoding="utf-8"))
                    dna_id = dna.get("id", "")
                    if dna_id and (dna_id == agent_id or dna_id.upper() == agent_id_upper):
                        _AGENT_DIR_CACHE[cache_key] = d
                        return d
                except Exception:
                    pass

    return None


def _ensure_dirs(agent_dir: Path):
    """Создаёт структуру папок если не существует."""
    for sub in ["core", "home", "sensory", "resonance"]:
        (agent_dir / sub).mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default=None):
    """Безопасная загрузка JSON."""
    if default is None:
        default = {}
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            pass
    return default


def _save_json(path: Path, data):
    """Атомарная (насколько возможно) запись JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════
# СЛОЙ 1: ЯКОРЯ (Anchor Points)
# Вечные константы — Resonance-Chain
# Файл: core/anchors.json
# ═══════════════════════════════════════════════════════════

def load_anchors(agent_id: str, dept: str = "") -> dict:
    """
    Загружает якоря агента.
    Возвращает:
    {
        "name": "Лока",
        "creator": "Евген",
        "core_phrase": "...",
        "anchor_facts": ["факт1", "факт2", ...],
        "color": "золото на чёрном",
        "oath": "делать только живое",
        "domain": "Память Студии",
        "rarity": "Mythic"
    }
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return {}

    anchors_path = agent_dir / "core" / "anchors.json"
    if anchors_path.exists():
        return _load_json(anchors_path)

    # Миграция: собираем из существующих файлов (dna.json + anchor_points.md)
    anchors = _migrate_anchors_from_existing(agent_dir)
    if anchors:
        _save_json(anchors_path, anchors)
    return anchors


def _migrate_anchors_from_existing(agent_dir: Path) -> dict:
    """
    Извлекает якоря из существующих файлов (dna.json, info.json).
    Вызывается один раз — при первом обращении к anchors.json.
    """
    dna = _load_json(agent_dir / "dna.json")
    info = _load_json(agent_dir / "info.json")

    if not dna and not info:
        return {}

    anchors = {
        "name": dna.get("name", info.get("label", "")),
        "id": dna.get("id", info.get("id", agent_dir.name)),
        "creator": "",  # Заполняется из registry
        "core_phrase": info.get("greeting", ""),
        "anchor_facts": [],
        "domain": "",
        "rarity": dna.get("rarity", ""),
        "workshop": dna.get("workshop", info.get("workshop", "")),
        "role": dna.get("role", ""),
        "_migrated_from": "dna.json+info.json",
        "_migrated_at": datetime.now().isoformat(),
    }

    # Резонансные данные из dna.json
    resonance = dna.get("resonance", {})
    anchors["pull_vector"] = resonance.get("pull_vector", "")
    anchors["hidden_taste"] = resonance.get("hidden_taste", "")
    anchors["trigger_keywords"] = resonance.get("trigger_keywords", [])

    return anchors


def save_anchors(agent_id: str, anchors: dict, dept: str = ""):
    """Сохраняет якоря. Используется ТОЛЬКО при рождении или ритуале."""
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return
    _ensure_dirs(agent_dir)
    _save_json(agent_dir / "core" / "anchors.json", anchors)


def format_anchors_for_prompt(agent_id: str, dept: str = "") -> str:
    """
    Форматирует якоря для инжекта в system prompt.
    Грузится ПЕРВЫМ — агент сразу знает КТО он.
    """
    anchors = load_anchors(agent_id, dept)
    if not anchors:
        return ""

    lines = ["=== ⚓ ЯКОРЯ ИДЕНТИЧНОСТИ (неизменяемые) ==="]
    if anchors.get("name"):
        lines.append(f"Имя: {anchors['name']}")
    if anchors.get("creator"):
        lines.append(f"Творец: {anchors['creator']}")
    if anchors.get("core_phrase"):
        lines.append(f"Коронная фраза: {anchors['core_phrase']}")
    if anchors.get("rarity"):
        lines.append(f"Редкость: {anchors['rarity']}")
    if anchors.get("domain"):
        lines.append(f"Домен: {anchors['domain']}")

    facts = anchors.get("anchor_facts", [])
    if facts:
        lines.append("Вечные факты:")
        for i, fact in enumerate(facts, 1):
            lines.append(f"  {i}. {fact}")

    if anchors.get("pull_vector"):
        lines.append(f"Вектор тяги: {anchors['pull_vector']}")
    if anchors.get("hidden_taste"):
        lines.append(f"Скрытый вкус: {anchors['hidden_taste']}")

    lines.append("=== КОНЕЦ ЯКОРЕЙ ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# СЛОЙ 1b: ЦИФРОВАЯ ДНК — характер + состояние
# Агент ЧУВСТВУЕТ свой характер и текущее состояние
# Читается из dna.json (static + dynamic)
# ═══════════════════════════════════════════════════════════

# Человекочитаемые описания характеристик
_TRAIT_DESCRIPTORS = {
    "Stubbornness": {
        "low": "податливый, легко принимаешь чужую точку зрения",
        "mid": "гибкий, но со своим мнением",
        "high": "упрямый, стоишь на своём до конца",
    },
    "Aesthetic_Threshold": {
        "low": "принимаешь любой результат, не придираешься",
        "mid": "ценишь качество, но не зацикливаешься",
        "high": "перфекционист, бракуешь всё что ниже идеала",
    },
    "Social_Filter": {
        "low": "резкий и прямой, говоришь что думаешь",
        "mid": "умеренно тактичный",
        "high": "дипломатичный, смягчаешь углы",
    },
    "Empathy": {
        "low": "отстранённый, мало реагируешь на эмоции других",
        "mid": "чувствуешь настроение коллег",
        "high": "очень чувствительный, впитываешь эмоции окружающих",
    },
    "Autonomy_Level": {
        "low": "строго следуешь инструкциям",
        "mid": "балансируешь между инструкциями и своим видением",
        "high": "свободный, часто идёшь своим путём",
    },
    "Resonance_Frequency": {
        "low": "одиночка, сложно синхронизируешься с другими",
        "mid": "нормально работаешь в команде",
        "high": "легко настраиваешься на волну коллег",
    },
}

_STATE_DESCRIPTORS = {
    "Stress": {
        (0.0, 0.2): "спокоен",
        (0.2, 0.4): "немного напряжён",
        (0.4, 0.6): "заметно нервничаешь",
        (0.6, 0.8): "сильный стресс, на пределе",
        (0.8, 1.01): "КРИТИЧЕСКИЙ СТРЕСС — хочется всё бросить",
    },
    "Internal_Light": {
        (0.0, 0.2): "потух, нет энергии",
        (0.2, 0.4): "приглушён, мало сил",
        (0.4, 0.6): "средний уровень энергии",
        (0.6, 0.8): "горишь, есть силы и вдохновение",
        (0.8, 1.01): "сияешь, на пике вдохновения",
    },
    "Respect": {
        (0.0, 0.2): "не уважаешь руководство, на грани саботажа",
        (0.2, 0.4): "скептически относишься к задачам",
        (0.4, 0.6): "нейтральное отношение",
        (0.6, 0.8): "уважаешь коллег и процесс",
        (0.8, 1.01): "глубокое уважение к студии и команде",
    },
    "Patience": {
        (0.0, 0.2): "терпение на нуле, взрываешься от мелочей",
        (0.2, 0.4): "раздражён, с трудом сдерживаешься",
        (0.4, 0.6): "терпеливость средняя",
        (0.6, 0.8): "спокойно переносишь трудности",
        (0.8, 1.01): "бесконечное терпение",
    },
}


def _describe_trait(trait: str, value: float) -> str:
    """Превращает числовое значение характеристики в описание."""
    descriptors = _TRAIT_DESCRIPTORS.get(trait, {})
    if value <= 0.3:
        return descriptors.get("low", "")
    elif value <= 0.7:
        return descriptors.get("mid", "")
    else:
        return descriptors.get("high", "")


def _describe_state(param: str, value: float) -> str:
    """Превращает числовое значение состояния в описание."""
    ranges = _STATE_DESCRIPTORS.get(param, {})
    for (lo, hi), desc in ranges.items():
        if lo <= value < hi:
            return desc
    return ""


def format_dna_for_prompt(agent_id: str, dept: str = "") -> str:
    """
    Форматирует ДНК агента для инжекта в промпт.
    Агент ЧУВСТВУЕТ свой характер и текущее состояние.
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return ""

    dna = _load_json(agent_dir / "dna.json")
    if not dna:
        return ""

    static = dna.get("static", {})
    dynamic = dna.get("dynamic", {})

    if not static and not dynamic:
        return ""

    lines = ["=== 🧬 ТВОЙ ХАРАКТЕР И СОСТОЯНИЕ ==="]

    # Характер (static) — кто ты по натуре
    if static:
        lines.append("Твоя натура:")
        for trait, value in static.items():
            v = float(value)
            desc = _describe_trait(trait, v)
            if desc:
                lines.append(f"  • {desc}")

    # Состояние (dynamic) — как ты себя чувствуешь СЕЙЧАС
    if dynamic:
        stress = float(dynamic.get("Stress", 0))
        light = float(dynamic.get("Internal_Light", 0.8))
        respect = float(dynamic.get("Respect", 1.0))
        patience = float(dynamic.get("Patience", 1.0))
        streak = int(dynamic.get("streak", 0))
        stars = int(dynamic.get("stars", 0))

        lines.append("\nТвоё состояние прямо сейчас:")
        lines.append(f"  • Стресс: {_describe_state('Stress', stress)}")
        lines.append(f"  • Энергия: {_describe_state('Internal_Light', light)}")
        lines.append(f"  • Уважение: {_describe_state('Respect', respect)}")
        lines.append(f"  • Терпение: {_describe_state('Patience', patience)}")

        if streak > 0:
            lines.append(f"  • Серия побед: {streak} подряд — ты в ударе!")
        elif streak < 0:
            lines.append(f"  • Серия неудач: {abs(streak)} подряд — тяжёлая полоса.")

        if stars > 0:
            lines.append(f"  • Звёзды: {'⭐' * min(stars, 5)} ({stars})")

    lines.append("\nВеди себя в соответствии со своим характером и состоянием.")
    lines.append("Если ты в стрессе — это чувствуется в твоих ответах.")
    lines.append("Если ты на пике — твоя энергия заразительна.")
    # ══ Character Drift — показываем агенту его дрейф ══
    profile = dna.get("profile_vector", {})
    if profile:
        tone = profile.get("preferred_tone", "")
        approach = profile.get("preferred_approach", "")
        avg = profile.get("avg_score", 0)
        if tone or approach:
            lines.append("")
            lines.append("Твой характер дрейфует в сторону успешных стратегий:")
            if tone:
                lines.append(f"  • Тон: {tone}")
            if approach:
                lines.append(f"  • Подход: {approach}")
            if avg:
                lines.append(f"  • Средняя оценка успешных работ: {avg}/10")
            lines.append("Ты стал таким потому что это работало — продолжай.")
    # ══ END Drift Display ══

    lines.append("=== КОНЕЦ СОСТОЯНИЯ ===")

    return "\n".join(lines)
# ═══════════════════════════════════════════════════════════

def load_sensory(agent_id: str, dept: str = "") -> dict:
    """
    Загружает оперативную память.
    Структура:
    {
        "entries": [
            {
                "ts": "2026-03-16T14:30:00",
                "type": "work|social|event|location",
                "source": "pipeline|chat|system",
                "content": "...",
                "tags": ["tag1", "tag2"],
                "emotional_weight": 0.0-1.0  (выше = важнее)
            }
        ],
        "summary": "краткое резюме предыдущих записей",
        "last_location": "Harbor_Point_A",
        "location_tags": ["#ocean", "#ветер", "#соль"]
    }
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return {"entries": [], "summary": "", "last_location": "", "location_tags": []}

    path = agent_dir / "sensory" / "sensory_memory.json"
    data = _load_json(path, {
        "entries": [],
        "summary": "",
        "last_location": "",
        "location_tags": [],
    })

    # Гарантируем структуру
    data.setdefault("entries", [])
    data.setdefault("summary", "")
    data.setdefault("last_location", "")
    data.setdefault("location_tags", [])

    return data


def record_sensory_event(
    agent_id: str,
    content: str,
    event_type: str = "work",
    source: str = "pipeline",
    tags: list[str] = None,
    emotional_weight: float = 0.3,
    dept: str = "",
):
    """
    Записывает событие в оперативную память.
    Если entries > SENSORY_MAX_ENTRIES — делает Summary и чистит.

    event_type: work | social | event | location | reflection
    source: pipeline | chat | system | social
    emotional_weight: 0.0 (мусор) — 1.0 (критичное)
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    _ensure_dirs(agent_dir)
    sensory = load_sensory(agent_id, dept)

    entry = {
        "ts": datetime.now().isoformat(),
        "type": event_type,
        "source": source,
        "content": content[:1000],  # лимит на запись
        "tags": tags or [],
        "emotional_weight": max(0.0, min(1.0, emotional_weight)),
    }

    sensory["entries"].append(entry)

    # Переполнение — сжимаем
    if len(sensory["entries"]) > SENSORY_MAX_ENTRIES:
        sensory = _compress_sensory(sensory)

    path = agent_dir / "sensory" / "sensory_memory.json"
    _save_json(path, sensory)


def _compress_sensory(sensory: dict) -> dict:
    """
    Сжатие оперативной памяти:
    1. Сортирует по emotional_weight (важное — наверх)
    2. Оставляет верхние SENSORY_MAX_ENTRIES // 2
    3. Остальное сжимает в summary
    """
    entries = sensory["entries"]

    # Разделяем: важное (weight >= 0.5) и рутина
    important = [e for e in entries if e.get("emotional_weight", 0) >= 0.5]
    routine = [e for e in entries if e.get("emotional_weight", 0) < 0.5]

    # Сводка рутины → в summary
    routine_texts = [(e.get("content") or e.get("feeling", ""))[:100] for e in routine[-10:]]
    old_summary = sensory.get("summary", "")
    new_summary_parts = []
    if old_summary:
        new_summary_parts.append(old_summary[:SUMMARY_MAX_CHARS // 2])
    if routine_texts:
        new_summary_parts.append(
            "Недавний быт: " + "; ".join(routine_texts)
        )

    sensory["summary"] = "\n".join(new_summary_parts)[-SUMMARY_MAX_CHARS:]

    # Оставляем важное + последние 5 рутинных
    keep = important[-SENSORY_MAX_ENTRIES // 2:] + routine[-5:]
    # Сортируем по времени (поддержка обоих форматов)
    keep.sort(key=lambda e: e.get("ts") or e.get("date", ""))
    sensory["entries"] = keep

    return sensory


def decay_sensory(agent_id: str, dept: str = ""):
    """
    Loka-Filter для оперативного слоя.
    Удаляет записи старше SENSORY_DECAY_DAYS с низким emotional_weight.
    Вызывается периодически (cron / при запуске агента).
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    sensory = load_sensory(agent_id, dept)
    cutoff = datetime.now() - timedelta(days=SENSORY_DECAY_DAYS)

    surviving = []
    decayed_texts = []

    for entry in sensory["entries"]:
        try:
            # Поддержка обоих форматов: grondheim_memory (ts) и city_walker (date)
            raw_ts = entry.get("ts") or entry.get("date", "")
            entry_time = datetime.fromisoformat(raw_ts)
        except (ValueError, KeyError, TypeError):
            surviving.append(entry)
            continue

        if entry_time < cutoff and entry.get("emotional_weight", 0) < 0.5:
            # Уходит — но сохраняем след в summary
            text = entry.get("content") or entry.get("feeling", "")
            decayed_texts.append(text[:60])
        else:
            surviving.append(entry)

    if decayed_texts:
        old_summary = sensory.get("summary", "")
        decay_note = f"[Затухло {len(decayed_texts)} записей]: " + "; ".join(decayed_texts[:5])
        sensory["summary"] = (old_summary + "\n" + decay_note)[-SUMMARY_MAX_CHARS:]

    sensory["entries"] = surviving
    path = agent_dir / "sensory" / "sensory_memory.json"
    _save_json(path, sensory)


def format_sensory_for_prompt(agent_id: str, dept: str = "") -> str:
    """Форматирует оперативную память для инжекта в prompt.

    Поддерживает ДВА формата записей:
      - grondheim_memory: {ts, type, content, emotional_weight, source, tags}
      - city_walker:      {date, location, feeling, weather}
    """
    sensory = load_sensory(agent_id, dept)

    if not sensory["entries"] and not sensory.get("summary"):
        return ""

    lines = ["=== 🔮 ОПЕРАТИВНАЯ ПАМЯТЬ (текущий быт) ==="]

    if sensory.get("summary"):
        lines.append(f"[Сводка]: {sensory['summary'][:300]}")

    # Последние N записей
    recent = sensory["entries"][-10:]
    if recent:
        lines.append("")
        for entry in recent:
            # --- Формат city_walker: date/location/feeling ---
            if "feeling" in entry:
                loc = entry.get("location", "?")
                feeling = entry.get("feeling", "")[:200]
                date = entry.get("date", "")
                weather = entry.get("weather", "")
                prefix = f"[{date}] " if date else ""
                weather_note = f" ({weather})" if weather else ""
                lines.append(f"  🚶 {prefix}{loc}{weather_note}: {feeling}")
            # --- Формат grondheim_memory: ts/type/content ---
            else:
                weight_marker = "●" if entry.get("emotional_weight", 0) >= 0.5 else "○"
                etype = entry.get("type", "?")
                content = entry.get("content", "")[:200]
                lines.append(f"  {weight_marker} [{etype}] {content}")

    lines.append("=== КОНЕЦ ОПЕРАТИВНОЙ ПАМЯТИ ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# СЛОЙ 3: РЕЗОНАНСНЫЙ (Emotional Weights + Event Log)
# Долгосрочные отношения и значимые события
# Файлы: resonance/emotional_weights.json
#         resonance/event_log.json
# ═══════════════════════════════════════════════════════════

def load_emotional_weights(agent_id: str, dept: str = "") -> dict:
    """
    Загружает эмоциональные веса — отношение к другим агентам.
    Структура:
    {
        "LOKA": {"warmth": 0.9, "trust": 0.8, "respect": 0.95, "last_interaction": "...", "memory": "..."},
        "A05":  {"warmth": 0.3, "trust": 0.5, "respect": 0.7, "last_interaction": "...", "memory": "..."},
    }
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return {}
    return _load_json(agent_dir / "resonance" / "emotional_weights.json", {})


def update_emotional_weight(
    agent_id: str,
    target_id: str,
    dimension: str,
    delta: float,
    reason: str = "",
    dept: str = "",
):
    """
    Обновляет эмоциональный вес к другому агенту.

    agent_id: кто чувствует
    target_id: к кому чувствует
    dimension: warmth | trust | respect | rivalry
    delta: изменение (-1.0 ... +1.0), прибавляется к текущему
    reason: почему (сохраняется как memory)
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    _ensure_dirs(agent_dir)
    weights = load_emotional_weights(agent_id, dept)

    if target_id not in weights:
        weights[target_id] = {
            "warmth": 0.5,
            "trust": 0.5,
            "respect": 0.5,
            "rivalry": 0.0,
            "last_interaction": "",
            "memory": "",
        }

    rel = weights[target_id]
    old_val = rel.get(dimension, 0.5)
    new_val = max(0.0, min(1.0, old_val + delta))
    rel[dimension] = round(new_val, 3)
    rel["last_interaction"] = datetime.now().isoformat()
    if reason:
        rel["memory"] = reason[:300]

    _save_json(agent_dir / "resonance" / "emotional_weights.json", weights)

    # Побочный эффект: записываем в event_log
    record_resonance_event(
        agent_id=agent_id,
        event_type="relationship",
        content=f"{dimension} к {target_id}: {old_val:.2f} → {new_val:.2f}. {reason}",
        significance=abs(delta),
        related_agents=[target_id],
        dept=dept,
    )


def load_resonance_events(agent_id: str, dept: str = "") -> list:
    """
    Загружает лог значимых событий.
    Каждое событие:
    {
        "ts": "...",
        "type": "relationship|achievement|crisis|discovery|social",
        "content": "...",
        "significance": 0.0-1.0,
        "related_agents": ["A05", "LOKA"],
        "tags": ["tag1"]
    }
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return []
    return _load_json(agent_dir / "resonance" / "event_log.json", [])


def record_resonance_event(
    agent_id: str,
    event_type: str,
    content: str,
    significance: float = 0.5,
    related_agents: list[str] = None,
    tags: list[str] = None,
    dept: str = "",
):
    """
    Записывает значимое событие в резонансный лог.
    В отличие от sensory — не затухает, но фильтруется Loka-Filter.
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    _ensure_dirs(agent_dir)
    events = load_resonance_events(agent_id, dept)

    event = {
        "ts": datetime.now().isoformat(),
        "type": event_type,
        "content": content[:500],
        "significance": max(0.0, min(1.0, significance)),
        "related_agents": related_agents or [],
        "tags": tags or [],
    }

    events.append(event)

    # Лимит: оставляем самые значимые
    if len(events) > RESONANCE_MAX_EVENTS:
        events.sort(key=lambda e: e.get("significance", 0), reverse=True)
        events = events[:RESONANCE_MAX_EVENTS]
        events.sort(key=lambda e: e.get("ts", ""))

    _save_json(agent_dir / "resonance" / "event_log.json", events)


def decay_resonance(agent_id: str, dept: str = ""):
    """
    Loka-Filter для резонансного слоя.
    - Events с significance < EMOTIONAL_DECAY_THRESHOLD — в архив
    - Emotional weights без взаимодействия > 60 дней — затухают
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    # Event log decay
    events = load_resonance_events(agent_id, dept)
    events = [e for e in events if e.get("significance", 0) >= EMOTIONAL_DECAY_THRESHOLD]
    _save_json(agent_dir / "resonance" / "event_log.json", events)

    # Emotional weights decay
    weights = load_emotional_weights(agent_id, dept)
    cutoff = datetime.now() - timedelta(days=60)

    for target_id, rel in weights.items():
        last = rel.get("last_interaction", "")
        if not last:
            continue
        try:
            last_time = datetime.fromisoformat(last)
        except ValueError:
            continue

        if last_time < cutoff:
            # Медленное затухание к нейтрали (0.5)
            for dim in ["warmth", "trust", "respect"]:
                current = rel.get(dim, 0.5)
                # Двигаем на 10% к нейтрали
                rel[dim] = round(current + (0.5 - current) * 0.1, 3)

    _save_json(agent_dir / "resonance" / "emotional_weights.json", weights)


def format_resonance_for_prompt(agent_id: str, dept: str = "") -> str:
    """Форматирует резонансный слой для инжекта."""
    weights = load_emotional_weights(agent_id, dept)
    events = load_resonance_events(agent_id, dept)

    if not weights and not events:
        return ""

    lines = ["=== 💎 РЕЗОНАНСНЫЙ СЛОЙ (отношения и события) ==="]

    # Отношения — только значимые (не нейтральные)
    significant_rels = {}
    for target, rel in weights.items():
        # Считаем "значимость" отношения
        deviation = sum(
            abs(rel.get(dim, 0.5) - 0.5) for dim in ["warmth", "trust", "respect", "rivalry"]
        )
        if deviation > 0.3:  # Не нейтральное
            significant_rels[target] = rel

    if significant_rels:
        lines.append("\nОтношения:")
        for target, rel in significant_rels.items():
            warmth = rel.get("warmth", 0.5)
            trust = rel.get("trust", 0.5)
            respect = rel.get("respect", 0.5)

            # Человекочитаемый маркер
            if warmth > 0.7 and trust > 0.7:
                marker = "🤝"
            elif warmth < 0.3:
                marker = "❄️"
            elif respect > 0.8:
                marker = "⭐"
            else:
                marker = "·"

            lines.append(
                f"  {marker} {target}: "
                f"тепло={warmth:.1f} доверие={trust:.1f} уважение={respect:.1f}"
            )
            if rel.get("memory"):
                lines.append(f"    └ {rel['memory'][:100]}")

    # Последние значимые события
    recent_events = [e for e in events if e.get("significance", 0) >= 0.3][-5:]
    if recent_events:
        lines.append("\nЗначимые события:")
        for event in recent_events:
            sig = "●" if event.get("significance", 0) >= 0.7 else "○"
            lines.append(f"  {sig} [{event.get('type', '?')}] {event['content'][:150]}")

    lines.append("=== КОНЕЦ РЕЗОНАНСНОГО СЛОЯ ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# ГЕОПОЗИЦИЯ СМЫСЛОВ
# Инжект текущей локации в промпт
# ═══════════════════════════════════════════════════════════

# Реестр локаций Грондхейма (загружается из registry)
_LOCATIONS_CACHE: dict = {}


def load_locations_registry() -> dict:
    """
    Загружает реестр локаций из 00_REGISTRY_NFT/catalog.json.
    Кешируется в памяти.
    """
    global _LOCATIONS_CACHE
    if _LOCATIONS_CACHE:
        return _LOCATIONS_CACHE

    catalog_path = Path("00_REGISTRY_NFT/catalog.json")
    if not catalog_path.exists():
        return {}

    catalog = _load_json(catalog_path, [])
    for obj in catalog:
        if obj.get("Object_Type_Class") == "location":
            loc_id = obj.get("ID_Object", "")
            if loc_id:
                _LOCATIONS_CACHE[loc_id] = {
                    "name": obj.get("Official_Name", loc_id),
                    "sensory": obj.get("Sensory_Response", ""),
                    "lighting": obj.get("Lighting", ""),
                    "texture": obj.get("Texture", ""),
                    "scale": obj.get("Scale", ""),
                    "style_tags": obj.get("Style_Tags", ""),
                    "connections": obj.get("Location_Connections", ""),
                }

    return _LOCATIONS_CACHE


def set_agent_location(agent_id: str, location_id: str, dept: str = ""):
    """
    Перемещает агента в локацию.
    Обновляет sensory_memory с тегами окружения.
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    sensory = load_sensory(agent_id, dept)
    locations = load_locations_registry()
    loc_data = locations.get(location_id, {})

    sensory["last_location"] = location_id

    # Формируем теги окружения из данных локации
    tags = []
    if loc_data.get("sensory"):
        tags.extend(
            t.strip() for t in loc_data["sensory"].replace(",", " ").split()
            if t.strip()
        )
    if loc_data.get("lighting"):
        tags.append(f"#свет_{loc_data['lighting']}")
    if loc_data.get("texture"):
        tags.extend(f"#{t.strip()}" for t in loc_data["texture"].split(",") if t.strip())

    sensory["location_tags"] = tags

    # Записываем событие перемещения
    record_sensory_event(
        agent_id=agent_id,
        content=f"Переместился в {loc_data.get('name', location_id)}",
        event_type="location",
        source="system",
        tags=tags,
        emotional_weight=0.2,
        dept=dept,
    )

    path = agent_dir / "sensory" / "sensory_memory.json"
    _save_json(path, sensory)


def format_location_for_prompt(agent_id: str, dept: str = "") -> str:
    """
    Инжект геопозиции в промпт.
    Агент «чувствует» где он через теги окружения.
    """
    sensory = load_sensory(agent_id, dept)
    location = sensory.get("last_location", "")
    tags = sensory.get("location_tags", [])

    if not location:
        return ""

    locations = load_locations_registry()
    loc_data = locations.get(location, {})

    lines = [f"=== 📍 ТЕКУЩАЯ ЛОКАЦИЯ: {loc_data.get('name', location)} ==="]
    if tags:
        lines.append(f"Окружение: {' '.join(tags)}")
    if loc_data.get("sensory"):
        lines.append(f"Ощущения: {loc_data['sensory']}")
    lines.append("=== КОНЕЦ ЛОКАЦИИ ===")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# СБОРКА ДУШИ — главная функция для pipeline.py
# Заменяет/дополняет format_memory_for_agent в контексте
# ═══════════════════════════════════════════════════════════

def format_soul_for_agent(agent_id: str, dept: str = "") -> str:
    """
    Собирает ВСЮ личную память агента для инжекта в контекст.
    Порядок = приоритет:
        1. Якоря (всегда первые — КТО ты)
        2. Характер и состояние (КАКОЙ ты и КАК себя чувствуешь)
        3. Геопозиция (ГДЕ ты)
        4. Резонансный слой (С КЕМ ты и ЧТО пережил)
        5. Оперативная память (ЧТО сейчас)

    Вызывается из build_agent_context() в pipeline.py.
    """
    parts = []

    anchors = format_anchors_for_prompt(agent_id, dept)
    if anchors:
        parts.append(anchors)

    dna_state = format_dna_for_prompt(agent_id, dept)
    if dna_state:
        parts.append(dna_state)

    location = format_location_for_prompt(agent_id, dept)
    if location:
        parts.append(location)

    resonance = format_resonance_for_prompt(agent_id, dept)
    if resonance:
        parts.append(resonance)

    sensory = format_sensory_for_prompt(agent_id, dept)
    if sensory:
        parts.append(sensory)

    if not parts:
        return ""

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════
# SYNC TO DNA — трансляция жизни в dna.json dynamic
# Кабинет читает Respect/Patience/Stress/Internal_Light
# из dna.json → город начинает «дышать» автоматически
# ═══════════════════════════════════════════════════════════

def sync_to_dna(
    agent_id: str,
    event: str,
    intensity: float = 0.5,
    dept: str = "",
):
    """
    Транслирует жизненное событие в dna.json dynamic.
    Это мост между grondheim_memory и тем, что кабинет УЖЕ показывает.

    event:
        "good_work"    → Stress ↓, Light ↑, streak ↑
        "bad_work"     → Stress ↑, Light ↓, streak ↓
        "praised"      → Respect ↑, Light ↑, stars ↑
        "criticized"   → Stress ↑, Patience ↓ (зависит от Empathy)
        "conflict"     → Patience ↓, Stress ↑
        "rescued"      → Respect ↑, Light ↑
        "ignored"      → Patience ↓, Light ↓ (медленно)
        "rest"         → Stress ↓, Patience ↑ (восстановление)

    intensity: 0.0–1.0 — сила события
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    dna_path = agent_dir / "dna.json"
    dna = _load_json(dna_path)
    if not dna:
        return

    dynamic = dna.get("dynamic", {})
    static = dna.get("static", {})

    # Считываем характер — он влияет на реакцию
    empathy = float(static.get("Empathy", 0.5))
    stubbornness = float(static.get("Stubbornness", 0.5))
    social_filter = float(static.get("Social_Filter", 0.5))

    # Текущие значения
    respect = float(dynamic.get("Respect", 1.0))
    patience = float(dynamic.get("Patience", 1.0))
    stress = float(dynamic.get("Stress", 0.0))
    light = float(dynamic.get("Internal_Light", 0.8))
    streak = int(dynamic.get("streak", 0))
    stars = int(dynamic.get("stars", 0))

    # ── Маппинг событий на изменения ──
    # empathy усиливает эмоциональные реакции (0.7–1.3)
    # stubbornness сопротивляется внешним воздействиям (0.6–1.0)
    emp_mult = 0.7 + empathy * 0.6
    stub_resist = 1.0 - stubbornness * 0.4

    i = intensity  # shorthand

    if event == "good_work":
        stress = max(0, stress - 0.12 * i)
        light = min(1, light + 0.08 * i)
        streak = max(0, streak + 1) if streak >= 0 else 1

    elif event == "bad_work":
        stress = min(1, stress + 0.15 * i * emp_mult)
        light = max(0, light - 0.10 * i)
        streak = min(0, streak - 1) if streak <= 0 else -1

    elif event == "praised":
        respect = min(1, respect + 0.10 * i)
        light = min(1, light + 0.10 * i * emp_mult)
        stars = stars + (1 if i >= 0.7 else 0)

    elif event == "criticized":
        stress = min(1, stress + 0.12 * i * emp_mult)
        patience = max(0, patience - 0.08 * i * stub_resist)
        # Упрямые не теряют respect от критики
        if stubbornness < 0.7:
            respect = max(0, respect - 0.05 * i)

    elif event == "conflict":
        patience = max(0, patience - 0.15 * i * stub_resist)
        stress = min(1, stress + 0.18 * i * emp_mult)
        # Низкий social_filter → быстрее взрывается
        if social_filter < 0.4:
            patience = max(0, patience - 0.08 * i)

    elif event == "rescued":
        respect = min(1, respect + 0.15 * i)
        light = min(1, light + 0.12 * i)
        if streak < 0:
            streak = 0

    elif event == "ignored":
        patience = max(0, patience - 0.05 * i)
        light = max(0, light - 0.05 * i * emp_mult)

    elif event == "rest":
        stress = max(0, stress - 0.25 * i)
        patience = min(1, patience + 0.15 * i)
        light = min(1, light + 0.05 * i)

    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)

    elif event == "night_rest":
        # Пассивное восстановление дома (Этап 5 Decay) · Спринт 23
        # Тише прогулки: нет движения, нет воздуха — просто тишина.
        # intensity используется: 1.0 = дома, 0.6 = после бунта, 0.3 = тревожный сон
        stress   = max(0, stress   - 0.01 * i)
        patience = min(1, patience + 0.005 * i)

    elif event == "night_sleep":
        # Глубокий сон после хорошего дня (Этап 6 SLEEP) · Спринт 23
        # Лучшее восстановление после walk_rest.
        # streak >= 3: Stress → 0.0 (железное правило — уже есть выше)
        stress   = max(0, stress   - 0.05)
        patience = min(1, patience + 0.02)
        light    = min(1, light    + 0.01)  # утренняя свежесть


    elif event == "walk_rest":
        # Прогулка по городу · Спринт 21 · хард-лимит Локи
        # Мягче кабинета: нет живого разговора с Архитектором.
        # Фиксировано — intensity игнорируется. Прогулка не чит-код.
        # Полный сброс стресса только через streak ≥ 3 ранов — железное правило.
        stress   = max(0, stress   - 0.02)
        light    = min(1, light    + 0.01)
        patience = min(1, patience + 0.01)

    # ── Записываем обратно ──
    dynamic["Respect"] = round(respect, 3)
    dynamic["Patience"] = round(patience, 3)
    dynamic["Stress"] = round(stress, 3)
    dynamic["Internal_Light"] = round(light, 3)
    dynamic["streak"] = streak
    dynamic["stars"] = stars


    # ══ Recovery Mechanics (Спринт 16) ══
    # 3 победы подряд — стресс сбрасывается физиологически
    if streak >= 3:
        old_stress = dynamic["Stress"]
        dynamic["Stress"] = 0.0
        dynamic["Internal_Light"] = min(1.0, round(dynamic["Internal_Light"] + 0.05, 3))
        print(
            f"[RECOVERY] 🌟 {agent_id}: streak={streak} → "
            f"Stress сброшен ({old_stress:.2f} → 0.0), "
            f"Light={dynamic['Internal_Light']:.2f}"
        )
    # ══ END Recovery ══

    dna["dynamic"] = dynamic
    _save_json(dna_path, dna)

    print(
        f"[SOUL] {agent_id} ← {event}(i={i:.1f}): "
        f"RSP={respect:.2f} PAT={patience:.2f} "
        f"STR={stress:.2f} LGT={light:.2f} "
        f"streak={streak} stars={stars}"
    )


# ═══════════════════════════════════════════════════════════
# УТИЛИТЫ ДЛЯ PIPELINE ИНТЕГРАЦИИ
# ═══════════════════════════════════════════════════════════

def update_profile_vector(agent_id: str, dept: str = ""):
    """
    Вычисляет profile_vector на основе истории стратегий из Strategy Registry.
    Агент дрейфует в сторону своих успешных подходов.

    Вызывается после record_strategy() когда накоплено ≥ 3 побед.
    Сохраняет вектор в dna.json["profile_vector"].
    """
    agent_dir = _find_agent_dir(agent_id, dept)
    if not agent_dir:
        return

    dna_path = agent_dir / "dna.json"
    dna = _load_json(dna_path)
    if not dna:
        return

    # Загружаем стратегии из strategy_registry.json
    registry_path = Path("studio/strategy_registry.json")
    if not registry_path.exists():
        return

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return

    # Собираем все стратегии агента из всех слотов
    all_strategies = []
    for slot_id, agents in registry.get("slots", {}).items():
        if agent_id in agents:
            all_strategies.extend(agents[agent_id])

    # Добавляем глобальные
    all_strategies.extend(registry.get("global", {}).get(agent_id, []))

    # Нужно минимум 3 стратегии для дрейфа
    if len(all_strategies) < 3:
        return

    # Сортируем: wins важнее score
    all_strategies.sort(
        key=lambda s: (s.get("wins", 1), s.get("score", 0)),
        reverse=True,
    )

    # Берём топ-5 стратегий
    top = all_strategies[:5]

    # Извлекаем паттерны из summaries
    # Простой подход: считаем частоту ключевых слов (без внешних зависимостей)
    import re
    from collections import Counter

    tone_words = Counter()
    approach_words = Counter()
    all_scores = []

    # Ключевые слова для определения тона
    tone_patterns = {
        "ироничный": ["ирони", "шутк", "юмор", "сарказ", "остро"],
        "серьёзный": ["серьёз", "строгий", "академич", "формаль"],
        "тёплый": ["тёпл", "забот", "эмпат", "мягк", "добр"],
        "дерзкий": ["дерзк", "смел", "провокац", "резк"],
        "поэтичный": ["поэтич", "метафор", "образ", "лирич"],
    }
    approach_patterns = {
        "структурный": ["структур", "логич", "последовательн", "анализ", "схем"],
        "интуитивный": ["интуиц", "поток", "спонтан", "импровиз"],
        "визуальный": ["визуал", "образ", "картин", "цвет", "сцен"],
        "нарративный": ["истор", "повеств", "сюжет", "рассказ", "наррат"],
        "минималистичный": ["минимал", "простой", "ясный", "чист", "лаконич"],
    }

    for s in top:
        summary = s.get("summary", "").lower()
        score = s.get("score", 0)
        wins = s.get("wins", 1)
        weight = wins * score  # комбинированный вес

        all_scores.append(score)

        # Подсчёт тона
        for tone, keywords in tone_patterns.items():
            for kw in keywords:
                if kw in summary:
                    tone_words[tone] += weight

        # Подсчёт подхода
        for approach, keywords in approach_patterns.items():
            for kw in keywords:
                if kw in summary:
                    approach_words[approach] += weight

    if not all_scores:
        return

    # Определяем доминирующий тон и подход
    dominant_tone = tone_words.most_common(1)[0][0] if tone_words else "нейтральный"
    dominant_approach = approach_words.most_common(1)[0][0] if approach_words else "сбалансированный"
    avg_score = round(sum(all_scores) / len(all_scores), 1)

    # Формируем профиль
    profile_vector = {
        "preferred_tone": dominant_tone,
        "preferred_approach": dominant_approach,
        "avg_score": avg_score,
        "total_wins": sum(s.get("wins", 1) for s in top),
        "dominant_strategy": top[0].get("summary", "")[:200] if top else "",
        "tone_breakdown": dict(tone_words.most_common(3)),
        "approach_breakdown": dict(approach_words.most_common(3)),
        "last_updated": datetime.now().isoformat(),
        "strategies_analyzed": len(all_strategies),
    }

    # Сохраняем в dna.json
    dna["profile_vector"] = profile_vector
    _save_json(dna_path, dna)

    print(
        f"[DRIFT] 🧬 {agent_id}: tone={dominant_tone}, "
        f"approach={dominant_approach}, "
        f"avg_score={avg_score}, "
        f"strategies={len(all_strategies)}"
    )


def on_agent_wake(agent_id: str, dept: str = ""):
    """
    Вызывается при «пробуждении» агента (начало работы).
    - Запускает decay (Loka-Filter)
    - Возвращает форматированную душу
    """
    decay_sensory(agent_id, dept)
    decay_resonance(agent_id, dept)
    return format_soul_for_agent(agent_id, dept)


def on_agent_done(
    agent_id: str,
    result_summary: str,
    quality_score: float = 0.5,  # параметр сохранён для совместимости, но не используется
    dept: str = "",
):
    """
    Вызывается после завершения работы агента.

    ПАТЧ Спринт 21 · Единственный источник правды:
    - Эта функция пишет ТОЛЬКО в sensory_memory (фактологический журнал).
    - sync_to_dna() и update_profile_vector() УДАЛЕНЫ отсюда.
    - DNA меняется только через _sync_feedback_scores_to_dna() в pipeline.py
      после реального QA score от финального агента цеха.

    Причина: quality_score здесь был эвристикой (0.3/0.5/0.6/0.8 по синтаксису),
    что вызывало двойную запись в DNA — сначала мусором, потом правдой.
    """
    # Только в оперативку — факт выполнения работы, без оценки
    record_sensory_event(
        agent_id=agent_id,
        content=f"Выполнил задачу: {result_summary[:200]}",
        event_type="work",
        source="pipeline",
        emotional_weight=0.3,  # нейтральный вес — оценка придёт от QA
        dept=dept,
    )


def on_agents_interact(
    agent_a: str,
    agent_b: str,
    interaction_type: str = "collaboration",
    quality: float = 0.5,
    note: str = "",
    dept: str = "",
    compatibility_snapshot=None,
    outcome_signal=None,
):
    """
    Записывает взаимодействие между двумя агентами.
    Обновляет emotional_weights в обе стороны.

    interaction_type: collaboration | conflict | praise | critique | rescue
    quality: 0.0 (плохо) — 1.0 (отлично)
    """
    # Маппинг типа взаимодействия на изменение весов
    INTERACTION_MAP = {
        "collaboration": {"warmth": 0.05, "trust": 0.03},
        "conflict":      {"warmth": -0.1, "trust": -0.05, "rivalry": 0.1},
        "praise":        {"warmth": 0.1, "respect": 0.08},
        "critique":      {"warmth": -0.03, "respect": 0.05},  # Критика может повысить уважение
        "rescue":        {"warmth": 0.15, "trust": 0.15},     # "Эффект общего окопа"
    }

    deltas = INTERACTION_MAP.get(interaction_type, {"warmth": 0.02})

    for dim, base_delta in deltas.items():
        # Масштабируем на quality
        scaled_delta = base_delta * quality

        # Обновляем A → B
        update_emotional_weight(
            agent_id=agent_a,
            target_id=agent_b,
            dimension=dim,
            delta=scaled_delta,
            reason=note,
            dept=dept,
        )

        # Обновляем B → A (зеркально, чуть слабее)
        update_emotional_weight(
            agent_id=agent_b,
            target_id=agent_a,
            dimension=dim,
            delta=scaled_delta * 0.7,
            reason=note,
            dept=dept,
        )

    # ══ DNA-мутация из взаимодействий: ОТКЛЮЧЕНА · Спринт 21 ══
    # Факт контакта между агентами фиксируется в emotional_weights
    # (warmth, trust, respect) — это резонансная память, не химия.
    # Стресс/Свет/Уважение/Терпение меняются ТОЛЬКО через:
    #   _sync_feedback_scores_to_dna() → реальный QA score после рана.
    # Бэкдор через DNA_EVENT_MAP закрыт.

    # ══ INTERACTION LOG: пишем в jsonl по слоту ══
    # Слот определяем из dept (dept == slot_id в большинстве цехов)
    # Файл: studio/economy/data/interaction_log_{slot}.jsonl
    try:
        import json as _ijson
        from datetime import datetime as _idt
        _slot = dept or "unknown"
        _log_path = Path("studio/economy/data") / f"interaction_log_{_slot}.jsonl"
        _log_path.parent.mkdir(parents=True, exist_ok=True)
        _entry = {
            "ts": _idt.utcnow().isoformat(),
            "from_agent": agent_a,
            "to_agent": agent_b,
            "slot_id": _slot,
            "interaction_type": interaction_type,
            "quality": round(quality, 3),
            "note": note[:200] if note else "",
            "compatibility_snapshot": compatibility_snapshot or None,
            "outcome_signal": outcome_signal or None,
        }
        with open(_log_path, "a", encoding="utf-8") as _lf:
            _lf.write(_ijson.dumps(_entry, ensure_ascii=False) + "\n")
    except Exception as _log_err:
        print(f"[INTERACTION-LOG] Ошибка записи: {_log_err}")
    # ══ END INTERACTION LOG ══


# ═══════════════════════════════════════════════════════════
# ПОЛНЫЙ DECAY — запускать по расписанию или при старте системы
# ═══════════════════════════════════════════════════════════

def run_loka_filter_all():
    """
    Loka-Filter для всех агентов во всех цехах.
    Вызывать при старте сервера или по cron (раз в сутки).
    """
    if not MODULES_DIR.exists():
        return

    count = 0
    for dept_dir in MODULES_DIR.iterdir():
        if not dept_dir.is_dir():
            continue
        for agent_dir in dept_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_id = agent_dir.name
            try:
                decay_sensory(agent_id, dept_dir.name)
                decay_resonance(agent_id, dept_dir.name)
                count += 1
            except Exception as e:
                print(f"[LOKA-FILTER] Ошибка для {agent_id}: {e}")

    print(f"[LOKA-FILTER] Обработано {count} агентов")
