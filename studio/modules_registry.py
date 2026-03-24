# studio/modules_registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

MODULES_DIR = Path(__file__).parent / "modules"

# Текущий активный департамент
CURRENT_DEPT = "video_long"


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


def get_worker_path(worker_id: str) -> Path:
    """Путь к папке воркера: modules/social_mix/A01/"""
    return get_dept_path() / worker_id


def get_worker_info(worker_id: str) -> dict | None:
    """Инфа о воркере из info.json"""
    info_path = get_worker_path(worker_id) / "info.json"
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


def get_worker_prompt(worker_id: str) -> str:
    """
    Собирает system prompt агента из трёх слоёв:
    1. core/anchor_points.md  — якоря, ДНК (грузится первым, неизменяемое)
    2. forge/prompt.md        — рабочие инструкции (основной промпт)
    3. prompt.md              — старый формат (совместимость)
    """
    worker_path = get_worker_path(worker_id)
    parts = []

    # 1. Ядро — якоря и статическая ДНК
    core_path = worker_path / "core" / "anchor_points.md"
    if core_path.exists():
        parts.append("# ═══ ЯДРО · ЯКОРНЫЕ ТОЧКИ (неизменяемо) ═══")
        parts.append(core_path.read_text(encoding="utf-8"))
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


def get_worker_home(worker_id: str) -> str:
    """
    Читает домашний контекст агента: home/home_prompt.md
    Используется в Храме и личных сессиях.
    Подаётся в начало user context (не в system prompt).
    """
    home_path = get_worker_path(worker_id) / "home" / "home_prompt.md"
    if home_path.exists():
        try:
            return home_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def get_worker_dna(worker_id: str) -> dict:
    """
    Читает dna.json агента.
    Возвращает полный словарь или пустой dict если файла нет.
    """
    dna_path = get_worker_path(worker_id) / "dna.json"
    return _read_json(dna_path)


def format_worker_state(worker_id: str) -> str:
    """
    Форматирует текущее состояние агента из dna.json dynamic блока.
    Подаётся в user context чтобы агент знал своё состояние.

    Пороговые состояния:
    - Respect < 0.2  → режим Враждебность
    - Patience == 0  → режим Тишина
    - Stress > 0.8   → агент идёт исправлять ошибки сам
    """
    dna = get_worker_dna(worker_id)
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


def get_worker_knowledge(worker_id: str) -> str:
    """
    Читает базу знаний агента.
    Ищет в двух местах (новая структура и старая):
    - forge/knowledge/*.md / *.txt
    - knowledge/*.md / *.txt
    """
    worker_path = get_worker_path(worker_id)
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
    """Список воркеров текущего департамента"""
    dept_path = get_dept_path()
    if not dept_path.exists():
        return []
    
    workers = []
    for d in sorted(dept_path.iterdir()):
        if d.is_dir() and d.name.startswith("A"):
            workers.append(d.name)
    return workers


def get_chain(start_from: int = 1, end_at: int = 12) -> list[str]:
    """Получить цепочку воркеров для запуска"""
    workers = []
    for i in range(start_from, end_at + 1):
        worker_id = f"A{str(i).zfill(2)}"
        if get_worker_path(worker_id).exists():
            workers.append(worker_id)
    return workers
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
        if not d.is_dir():
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
