# studio/modules/living_book/hooks.py — Хуки живой книги
# Студия «Шесть Пальцев» · 2026
# СТАНДАРТ v3.0 compliant.
#
# ИЗМЕНЕНИЯ:
#   on_before_agent("A00") — инжектирует biography_snapshot (память ребёнка)
#   on_after_agent("A16")  — валидирует формат chapter (scenes[], voice_choice, keywords)


import json
import re
from typing import Optional


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _format_biography_snapshot(snap: dict) -> str:
    """Форматирует biography_snapshot для инжекции в контекст агента."""
    lines = ["\n\n=== БИОГРАФИЯ РЕБЁНКА (память из прошлых глав) ==="]

    main_char = snap.get("main_character")
    if main_char:
        lines.append(f"Главный герой: {main_char} (уже выбран, НЕ МЕНЯТЬ)")

    home_world = snap.get("home_world")
    if home_world:
        lines.append(f"Родной мир: {home_world}")

    karma = snap.get("karma")
    if karma is not None:
        lines.append(f"Карма: {karma}")

    artifacts = snap.get("artifacts", [])
    if artifacts:
        names = [a.get("name") or a.get("id") for a in artifacts if a]
        lines.append(f"Артефакты: {', '.join(names)}")

    last_choices = snap.get("last_choices", [])
    if last_choices:
        # Фильтруем пустые строки
        choices = [c for c in last_choices if c]
        if choices:
            lines.append(f"Паттерн выборов: {', '.join(choices[-5:])}")

    completed = snap.get("completed_stories", [])
    if completed:
        lines.append(f"Пройденные главы: {', '.join(completed)} (НЕ ПОВТОРЯТЬ)")

    char_bonds = snap.get("character_bonds", {})
    if char_bonds:
        bond_str = ", ".join(f"{k}:{v}" for k, v in char_bonds.items())
        lines.append(f"Отношения с персонажами: {bond_str}")

    lines.append("=== КОНЕЦ БИОГРАФИИ ===")
    return "\n".join(lines)


def _validate_chapter_format(human_text: str) -> list[str]:
    """Проверяет что A16 выдал chapter в формате STANDARD v3.0.

    Возвращает список предупреждений (пустой = OK).
    """
    warnings = []

    # Пытаемся найти JSON в ответе
    package = None
    json_blocks = re.findall(r'```json\s*(.*?)```', human_text, re.DOTALL)
    for block in json_blocks:
        try:
            package = json.loads(block.strip())
            break
        except Exception:
            continue
    if package is None:
        try:
            package = json.loads(human_text.strip())
        except Exception:
            pass

    if package is None:
        warnings.append("A16: не найден JSON в ответе — chapter не распознан")
        return warnings

    chapter = package.get("chapter")
    if not chapter:
        warnings.append("A16: нет поля 'chapter' в JSON (STANDARD §4.6)")
        return warnings

    scenes = chapter.get("scenes", [])
    if not scenes:
        warnings.append("A16: chapter.scenes[] пуст — нет сцен")
        return warnings

    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")

        # mode обязательно voice_choice
        mode = scene.get("mode")
        if mode != "voice_choice":
            warnings.append(f"A16: {sid}.mode = '{mode}' (ожидается 'voice_choice', STANDARD §6.1)")

        # choices обязательны
        choices = scene.get("choices", [])
        if not choices:
            warnings.append(f"A16: {sid} — нет choices[]")
            continue

        for j, choice in enumerate(choices):
            cid = choice.get("id", f"choice_{j}")
            if not choice.get("keywords"):
                warnings.append(f"A16: {sid}/{cid} — нет keywords[] (STANDARD §6.2)")
            if not choice.get("next_scene"):
                warnings.append(f"A16: {sid}/{cid} — нет next_scene (STANDARD §6.2)")

    # on_end
    if not chapter.get("on_end"):
        warnings.append("A16: нет chapter.on_end (STANDARD §6.3)")

    return warnings


# ── HOOKS ────────────────────────────────────────────────────────────────────

def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Вызывается ПЕРЕД каждым агентом. Модифицирует контекст.

    A00 (Фабула) — получает:
        1. child_info (имя, возраст, интересы, задача)
        2. biography_snapshot (память ребёнка из прошлых глав)
           → Фабула знает: кто герой, какие артефакты, паттерн выборов,
             что уже пройдено (не повторять)

    A00a (Вера Душа) — получает психологические критерии проверки.
    """

    # Фабула — данные ребёнка + биографический снэпшот
    if worker_id == "A00":
        child_info = state.get("child_info", {})
        if child_info:
            context += f"\n\n=== ДАННЫЕ РЕБЁНКА ==="
            context += f"\nИмя: {child_info.get('name', 'не указано')}"
            context += f"\nВозраст: {child_info.get('age', 'не указан')}"
            context += f"\nИнтересы: {child_info.get('interests', 'не указаны')}"
            context += f"\nОсобенности: {child_info.get('notes', 'нет')}"
            context += f"\nЗадача: {child_info.get('task', '')}"
            context += f"\n=== КОНЕЦ ДАННЫХ РЕБЁНКА ==="

        # Биографический снэпшот (STANDARD §4.5)
        snap = state.get("biography_snapshot")
        if snap:
            context += _format_biography_snapshot(snap)

    # Вера Душа — психологические критерии
    if worker_id == "A00a":
        context += (
            "\n\n=== КРИТЕРИИ ПРОВЕРКИ ==="
            "\n1. Безопасность: нет пугающих элементов для целевого возраста"
            "\n2. Привязанность: история создаёт чувство безопасной базы"
            "\n3. Персонализация: ребёнок узнает себя в герое"
            "\n4. Эмоциональная дуга: от тревоги к разрешению через поддержку"
            "\n=== КОНЕЦ КРИТЕРИЕВ ==="
        )

    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Вызывается ПОСЛЕ каждого агента. Обработка результатов.

    A00 — сохраняем сюжетный каркас в state.
    A16 — валидируем соответствие STANDARD §6 (chapter, scenes, voice_choice).
    """

    # После A00 (Фабула) — сохраняем сюжетный каркас
    if worker_id == "A00":
        state["story_framework"] = human_text[:2000]

    # После A16 (Марка Файн) — валидация формата
    if worker_id == "A16":
        state["book_complete"] = True

        warnings = _validate_chapter_format(human_text)
        if warnings:
            print(f"\n[LIVING_BOOK] ⚠️  A16 format warnings ({len(warnings)}):")
            for w in warnings:
                print(f"  • {w}")
            # Сохраняем предупреждения в state — для логов и отладки
            state["a16_format_warnings"] = warnings
        else:
            print(f"[LIVING_BOOK] ✅ A16 chapter format OK (STANDARD v3.0)")

        print(f"[LIVING_BOOK] 📖 Книга завершена!")

    return {}


def on_revision_notes(state: dict, notes: str, loop_number: int) -> str:
    """Вызывается при РЕВИЗИИ — усиливает замечания Веры на 3-й итерации."""
    if loop_number >= 3:
        notes += (
            "\n\n⚠️ ТРЕТЬЯ РЕВИЗИЯ. Это последняя попытка. "
            "Сосредоточься на главном замечании и исправь его полностью."
        )
    return notes


def get_turbo_config() -> dict:
    """Living Book не имеет TURBO — слишком сложный пайплайн."""
    return {}