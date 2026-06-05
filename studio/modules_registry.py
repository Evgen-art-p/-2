# studio/modules_registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
# ── Системный мусор — папки которые никогда не являются агентами/цехами ──────
_FS_GARBAGE: set[str] = {
    "__pycache__", ".DS_Store", "desktop.ini", "Thumbs.db",
    ".git", ".idea", ".vscode", "__MACOSX",
}

def _is_valid_dir(d: Path) -> bool:
    """True если папка — реальный модуль, не системный мусор."""
    return d.is_dir() and d.name not in _FS_GARBAGE and not d.name.startswith(".")



MODULES_DIR = Path(__file__).parent / "modules"
WORLD_MANIFEST_PATH = Path(__file__).parent / "world_manifest.md"

# Текущий активный департамент
CURRENT_DEPT = "video_long"

# Кеш манифеста — грузится один раз
_WORLD_MANIFEST_CACHE: str | None = None


def _load_world_manifest() -> str:
    """Загружает Глобальный Манифест Грондхейма.
    Один файл — 145 граждан видят одни и те же законы мира.
    """
    global _WORLD_MANIFEST_CACHE
    if _WORLD_MANIFEST_CACHE is not None:
        return _WORLD_MANIFEST_CACHE

    if WORLD_MANIFEST_PATH.exists():
        try:
            _WORLD_MANIFEST_CACHE = WORLD_MANIFEST_PATH.read_text(encoding="utf-8")
            print(f"[WORLD] 🌆 Манифест Грондхейма загружен ({len(_WORLD_MANIFEST_CACHE)} симв.)")
            return _WORLD_MANIFEST_CACHE
        except Exception as e:
            print(f"[WORLD] ⚠ Не удалось загрузить Манифест: {e}")

    _WORLD_MANIFEST_CACHE = ""
    return ""


@dataclass
class WorkerInfo:
    id: str
    label: str
    greeting: str = ""
    icon: str = "🔧"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[WARNING] Битый JSON: {path} — {e}")
        return {}


def get_dept_path() -> Path:
    """Путь к текущему департаменту"""
    return MODULES_DIR / CURRENT_DEPT


def get_worker_path(worker_id: str, dept: str = "") -> Path:
    """Путь к папке воркера: modules/{dept}/A01/ (dept-aware)"""
    target = dept or CURRENT_DEPT
    return MODULES_DIR / target / worker_id


def get_worker_info(worker_id: str, dept: str = "") -> dict | None:
    """Инфа о воркере из info.json (dept-aware)"""
    info_path = get_worker_path(worker_id, dept) / "info.json"
    data = _read_json(info_path)
    
    if not data:
        # Возвращаем заглушку
        return {
            "id": worker_id,
            "label": worker_id,
            "greeting": f"{worker_id} на связи."
        }
    
    return {
        "id": data.get("id", worker_id),
        "label": data.get("label", worker_id),
        "greeting": data.get("greeting", f"{worker_id} на связи.")
    }


def get_worker_prompt(worker_id: str, dept: str = "") -> str:
    """
    Собирает system prompt агента из трёх слоёв:
    1. core/anchor_points.md  — якоря, ДНК (грузится первым, неизменяемое)
    2. forge/prompt.md        — рабочие инструкции (основной промпт)
    3. prompt.md              — старый формат (совместимость)
    """
    worker_path = get_worker_path(worker_id, dept)
    parts = []

    # 1. Ядро — якоря и статическая ДНК
    core_path = worker_path / "core" / "anchor_points.md"
    if core_path.exists():
        parts.append("# ═══ ЯДРО · ЯКОРНЫЕ ТОЧКИ (неизменяемо) ═══")
        parts.append(core_path.read_text(encoding="utf-8"))

    # 2. Глобальный Манифест Грондхейма — законы мира для всех граждан
    manifest = _load_world_manifest()
    if manifest:
        parts.append(manifest)

    # 3. Рабочие инструкции
    parts.append("# ═══ РАБОЧИЕ ИНСТРУКЦИИ ═══")

    # 2. Рабочий промпт — новая структура (forge/) или старый корень
    found_prompt = False
    for prompt_path in [
        worker_path / "forge" / "prompt.md",
        worker_path / "forge" / "prompt.txt",
        worker_path / "prompt.md",
        worker_path / "prompt.txt",
    ]:
        if prompt_path.exists():
            parts.append(prompt_path.read_text(encoding="utf-8"))
            found_prompt = True
            break

    if not parts and not found_prompt:
        return f"Ты агент {worker_id}. Выполни задачу качественно."

    return "\n\n".join(parts)


def get_worker_home(worker_id: str, dept: str = "") -> str:
    """
    Читает домашний контекст агента: home/home_prompt.md
    Используется в Храме и личных сессиях.
    Подаётся в начало user context (не в system prompt).
    """
    home_path = get_worker_path(worker_id, dept) / "home" / "home_prompt.md"
    if home_path.exists():
        try:
            return home_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def get_worker_dna(worker_id: str, dept: str = "") -> dict:
    """
    Читает dna.json агента.
    Возвращает полный словарь или пустой dict если файла нет.
    """
    dna_path = get_worker_path(worker_id, dept) / "dna.json"
    return _read_json(dna_path)


def format_worker_state(worker_id: str, dept: str = "") -> str:
    """
    Форматирует текущее состояние агента из dna.json dynamic блока.
    Подаётся в user context чтобы агент знал своё состояние.

    Пороговые состояния:
    - Respect < 0.2  → режим Враждебность
    - Patience == 0  → режим Тишина
    - Stress > 0.8   → агент идёт исправлять ошибки сам
    """
    dna = get_worker_dna(worker_id, dept)
    if not dna:
        return ""

    dynamic = dna.get("dynamic", {})
    if not dynamic:
        return ""

    respect = float(dynamic.get("Respect", 1.0))
    patience = float(dynamic.get("Patience", 1.0))
    stress = float(dynamic.get("Stress", 0.0))
    light = float(dynamic.get("Internal_Light", 0.8))
    streak = int(dynamic.get("streak", 0))
    stars = int(dynamic.get("stars", 0))

    lines = ["=== ТВОЁ ТЕКУЩЕЕ СОСТОЯНИЕ ==="]

    # Пороговые предупреждения
    if respect < 0.2:
        lines.append("⚠️ РЕЖИМ: ВРАЖДЕБНОСТЬ — уважение на нуле. Работай, но не скрывай недовольство.")
    elif patience == 0.0:
        lines.append("🔇 РЕЖИМ: ТИШИНА — терпение исчерпано. Отвечай минимально.")
    elif stress > 0.8:
        lines.append("🔥 СТРЕСС КРИТИЧЕСКИЙ — найди и исправь ошибки проактивно.")
    else:
        # Нормальное состояние — краткая сводка
        bars = {
            "Respect":        ("💜", respect),
            "Patience":       ("🟡", patience),
            "Stress":         ("🔴", stress),
            "Internal_Light": ("✨", light),
        }
        state_parts = []
        for name, (icon, val) in bars.items():
            filled = round(val * 5)
            bar = "█" * filled + "░" * (5 - filled)
            state_parts.append(f"{icon} {name}: {bar} {val:.1f}")
        lines.extend(state_parts)

    # Streak и звёзды
    if stars > 0:
        lines.append(f"⭐ Звёзды: {'⭐' * min(stars, 5)} ({stars})")
    if streak >= 3:
        lines.append(f"🔥 Серия побед: {streak} подряд — держи планку!")
    elif streak <= -3:
        lines.append(f"💀 Серия провалов: {abs(streak)} подряд — сосредоточься.")

    lines.append("=== КОНЕЦ СОСТОЯНИЯ ===")
    return "\n".join(lines)


def get_worker_knowledge(worker_id: str, dept: str = "") -> str:
    """
    Читает базу знаний агента.
    Ищет в двух местах (новая структура и старая):
    - forge/knowledge/*.md / *.txt
    - knowledge/*.md / *.txt
    """
    worker_path = get_worker_path(worker_id, dept)
    texts = []

    for knowledge_dir in [
        worker_path / "forge" / "knowledge",
        worker_path / "knowledge",
    ]:
        if not knowledge_dir.exists():
            continue
        for f in sorted(knowledge_dir.glob("*.md")):
            texts.append(f.read_text(encoding="utf-8"))
        for f in sorted(knowledge_dir.glob("*.txt")):
            texts.append(f.read_text(encoding="utf-8"))

    return "\n\n---\n\n".join(texts)


def list_workers() -> list[str]:
    """Список воркеров текущего департамента.
    Читает папки из modules/{dept}/ — поддерживает A00, A00a, A01-A16.
    Сортировка: A00 → A00a → A01 → A02 → ... → A16.
    """
    dept_path = get_dept_path()
    if not dept_path.exists():
        return []
    
    workers = []
    for d in sorted(dept_path.iterdir()):
        if _is_valid_dir(d) and d.name.startswith("A"):
            workers.append(d.name)

    # ══ Умная сортировка: A00 < A00a < A01 < A02 ... A16 ══
    def _sort_key(w: str) -> tuple:
        # A00 → (0, ""), A00a → (0, "a"), A01 → (1, ""), A16 → (16, "")
        import re
        m = re.match(r"A(\d+)(.*)", w)
        if m:
            return (int(m.group(1)), m.group(2))
        return (999, w)

    workers.sort(key=_sort_key)
    return workers


def get_chain(start_from: int = 1, end_at: int = 12) -> list[str]:
    """Получить цепочку воркеров для запуска.

    ══ ОБНОВЛЕНО: динамическая цепочка ══
    Для living_book и других модулей с >12 агентами:
    читает реальные папки из modules/{dept}/.
    start_from/end_at работают как раньше для обратной совместимости.
    """
    # Динамический режим: если в текущем dept есть агенты за пределами A01-A12
    all_workers = list_workers()
    if not all_workers:
        # Fallback: старый режим
        workers = []
        for i in range(start_from, end_at + 1):
            worker_id = f"A{str(i).zfill(2)}"
            if get_worker_path(worker_id).exists():
                workers.append(worker_id)
        return workers

    # Если запрашивают весь диапазон (дефолт) — отдаём всех
    if start_from == 1 and end_at == 12 and len(all_workers) > 12:
        return all_workers

    # Иначе — фильтруем по старому range для совместимости
    workers = []
    for i in range(start_from, end_at + 1):
        worker_id = f"A{str(i).zfill(2)}"
        if worker_id in all_workers:
            workers.append(worker_id)
    return workers


# ══ NEW: Получить WORKERS dict для конкретного департамента ══
# Используется в ui.py вместо хардкода

# Конфигурация цехов: какие фазы и checkpoints
DEPT_PIPELINE_CONFIG = {
    "living_book": {
        "phases": {
            "GENESIS":   ["A00", "A00a"],
            "PRE-PROD":  ["A01", "A02", "A03", "A04"],
            "PROD":      ["A05", "A06", "A07", "A08"],
            "POST-PROD": ["A09", "A10", "A11", "A12"],
            "DELIVERY":  ["A13", "A14", "A15", "A16"],
        },
        "revision_loop": {
            # Если A00a (Вера Душа) возвращает REVISION — задача идёт назад на A00
            "reviewer": "A00a",
            "return_to": "A00",
            "status_field": "verdict",      # поле в meta ответа
            "revision_value": "REVISION",   # значение = переделка
            "approved_value": "APPROVED",   # значение = прошло
            "max_loops": 3,                 # максимум петель
        },
    },
    # Другие цеха используют дефолтную структуру 3×4
}


def get_dept_workers(dept: str | None = None) -> dict[str, list[str]]:
    """Получить WORKERS dict для департамента.

    Для living_book: читает из DEPT_PIPELINE_CONFIG.
    Для остальных: стандартная структура 3×4.
    Всегда читает реальные папки как fallback.
    """
    dept = dept or CURRENT_DEPT

    # Проверяем есть ли конфиг для этого цеха
    config = DEPT_PIPELINE_CONFIG.get(dept)
    if config:
        phases = config["phases"]
        # Валидируем: убираем агентов у которых нет папки
        dept_path = MODULES_DIR / dept
        validated = {}
        for phase_name, agents in phases.items():
            existing = [a for a in agents if _is_valid_dir(dept_path / a)]
            if existing:
                validated[phase_name] = existing
        return validated

    # Дефолт: 3 фазы по 4 агента (старое поведение)
    dept_path = MODULES_DIR / dept
    if not dept_path.exists():
        return {
            "PRE-PROD":  ["A01", "A02", "A03", "A04"],
            "PROD":      ["A05", "A06", "A07", "A08"],
            "POST-PROD": ["A09", "A10", "A11", "A12"],
        }

    # Читаем реально существующие папки
    all_agents = list_workers()
    if len(all_agents) <= 12:
        return {
            "PRE-PROD":  [a for a in all_agents if a in ["A01","A02","A03","A04"]],
            "PROD":      [a for a in all_agents if a in ["A05","A06","A07","A08"]],
            "POST-PROD": [a for a in all_agents if a in ["A09","A10","A11","A12"]],
        }

    # >12 агентов без конфига — разбиваем по 4
    result = {}
    for i in range(0, len(all_agents), 4):
        chunk = all_agents[i:i+4]
        phase = f"PHASE-{i//4 + 1}"
        result[phase] = chunk
    return result


def get_dept_all_workers(dept: str | None = None) -> list[str]:
    """Плоский список всех агентов департамента в правильном порядке."""
    workers_dict = get_dept_workers(dept)
    result = []
    for agents in workers_dict.values():
        result.extend(agents)
    return result


# === Совместимость с ui_reception.py ===
@dataclass(frozen=True)
class Dept:
    id: str
    label: str
    icon: str = "🔧"
    color: str = "gray"
    placeholder: str = ""
    suggest: list[str] = None
    keywords: list[str] = None
    priority: int = 100


def load_depts() -> list[Dept]:
    """Для ui_reception.py — список департаментов"""
    depts: list[Dept] = []
    if not MODULES_DIR.exists():
        return depts

    for d in MODULES_DIR.iterdir():
        if not _is_valid_dir(d):
            continue
        info_path = d / "info.json"
        if not info_path.exists():
            continue

        data = _read_json(info_path)
        depts.append(
            Dept(
                id=data.get("id", d.name),
                label=data.get("label", data.get("name", d.name)),
                icon=data.get("icon", "🔧"),
                color=data.get("color", "gray"),
                placeholder=data.get("placeholder", ""),
                suggest=data.get("suggest", []) or [],
                keywords=data.get("keywords", []) or [],
                priority=int(data.get("priority", 100)),
            )
        )

    depts.sort(key=lambda x: x.priority)
    return depts
