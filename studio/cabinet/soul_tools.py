# studio/cabinet/soul_tools.py — Инструменты души для кабинета
# Подключается к cabinet_tools.py — новые tools для ДЖема и резидентов
#
# ДЖем не в пайплайне — его динамика меняется от:
#   - Отчётов пайплайна (итоги ранов)
#   - Общения в кабинете (с Архитектором)
#   - Взаимодействия с резидентами (Лока и др.)
#   - Состояния города (stressed agents, quality trends)

"""
╔══════════════════════════════════════════════════════════════╗
║  CABINET SOUL TOOLS                                          ║
║  Новые инструменты для кабинета:                             ║
║    get_agent_soul     — полная личная память агента           ║
║    get_relationships  — карта отношений                      ║
║    record_interaction — записать взаимодействие               ║
║    city_pulse         — пульс города (все агенты)             ║
║    jem_digest         — дайджест для ДЖема                   ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
from studio.grondheim_memory import (
    format_soul_for_agent,
    load_anchors,
    load_emotional_weights,
    load_resonance_events,
    load_sensory,
    on_agents_interact,
    sync_to_dna,
    record_sensory_event,
    record_resonance_event,
)


# ═══════════════════════════════════════════════════
# TOOL SCHEMAS — добавить в TOOLS_SCHEMA в cabinet_tools.py
# ═══════════════════════════════════════════════════

SOUL_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_agent_soul",
            "description": "Полная личная память агента: якоря, отношения к коллегам, значимые события, оперативная память. Показывает КТО он, С КЕМ дружит, ЧТО пережил.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "ID агента (A01, T1, LOKA, JEM...)"}
                },
                "required": ["agent_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_relationships",
            "description": "Карта отношений агента ко всем коллегам: тепло, доверие, уважение, соперничество. Показывает кого любит, кому не доверяет.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "ID агента"}
                },
                "required": ["agent_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_interaction",
            "description": "Записать взаимодействие между агентами. Влияет на их эмоциональные веса и ДНК (Stress, Respect, Patience, Light).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_a": {"type": "string", "description": "Первый агент"},
                    "agent_b": {"type": "string", "description": "Второй агент"},
                    "interaction_type": {
                        "type": "string",
                        "enum": ["collaboration", "conflict", "praise", "critique", "rescue"],
                        "description": "Тип: collaboration (работа), conflict (ссора), praise (похвала), critique (критика), rescue (спасение)"
                    },
                    "quality": {"type": "number", "description": "Интенсивность 0.0-1.0"},
                    "note": {"type": "string", "description": "Описание что произошло"}
                },
                "required": ["agent_a", "agent_b", "interaction_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "city_pulse",
            "description": "Пульс Грондхейма: общее настроение города, средний стресс, кто в лучшей/худшей форме, последние события.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "jem_digest",
            "description": "Дайджест для ДЖема: итоги последних ранов, состояние агентов, тревоги и достижения. Вызывается автоматически при старте кабинета.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


# ═══════════════════════════════════════════════════
# TOOL EXECUTORS
# ═══════════════════════════════════════════════════

async def exec_get_agent_soul(agent_id: str) -> str:
    """Полная личная память агента."""
    soul = format_soul_for_agent(agent_id)
    if not soul:
        return f"Агент {agent_id}: личная память пуста (Грондхейм ещё не активирован для этого агента)."
    return soul


async def exec_get_relationships(agent_id: str) -> str:
    """Карта отношений агента."""
    weights = load_emotional_weights(agent_id)
    if not weights:
        return f"У {agent_id} пока нет записанных отношений с коллегами."

    lines = [f"═══ Отношения {agent_id} ═══\n"]

    for target, rel in sorted(weights.items()):
        warmth = rel.get("warmth", 0.5)
        trust = rel.get("trust", 0.5)
        respect = rel.get("respect", 0.5)
        rivalry = rel.get("rivalry", 0.0)
        memory = rel.get("memory", "")

        # Человекочитаемый статус
        if warmth > 0.8 and trust > 0.7:
            status = "близкий друг"
        elif warmth > 0.6 and respect > 0.7:
            status = "уважаемый коллега"
        elif warmth < 0.3 and rivalry > 0.3:
            status = "напряжённые отношения"
        elif warmth < 0.3:
            status = "холод"
        elif trust < 0.3:
            status = "не доверяет"
        else:
            status = "нейтрально"

        lines.append(
            f"→ {target}: {status}\n"
            f"  тепло={warmth:.2f} доверие={trust:.2f} уважение={respect:.2f}"
            f"{f' соперничество={rivalry:.2f}' if rivalry > 0.1 else ''}"
        )
        if memory:
            lines.append(f"  последнее: {memory[:100]}")
        lines.append("")

    return "\n".join(lines)


async def exec_record_interaction(args: dict) -> str:
    """Записать взаимодействие между агентами."""
    agent_a = args.get("agent_a", "")
    agent_b = args.get("agent_b", "")
    itype = args.get("interaction_type", "collaboration")
    quality = float(args.get("quality", 0.5))
    note = args.get("note", "")

    if not agent_a or not agent_b:
        return "Нужно указать agent_a и agent_b."

    quality = max(0.0, min(1.0, quality))

    on_agents_interact(
        agent_a=agent_a,
        agent_b=agent_b,
        interaction_type=itype,
        quality=quality,
        note=note,
    )

    # Читаем обновлённые веса для отчёта
    w_a = load_emotional_weights(agent_a).get(agent_b, {})
    w_b = load_emotional_weights(agent_b).get(agent_a, {})

    TYPE_LABELS = {
        "collaboration": "Совместная работа",
        "conflict": "Конфликт",
        "praise": "Похвала",
        "critique": "Критика",
        "rescue": "Спасение",
    }

    return (
        f"✅ Записано: {TYPE_LABELS.get(itype, itype)}\n"
        f"  {agent_a} → {agent_b}: тепло={w_a.get('warmth', '?'):.2f} доверие={w_a.get('trust', '?'):.2f}\n"
        f"  {agent_b} → {agent_a}: тепло={w_b.get('warmth', '?'):.2f} доверие={w_b.get('trust', '?'):.2f}\n"
        f"  {f'Заметка: {note}' if note else ''}"
    )


async def exec_city_pulse() -> str:
    """Пульс Грондхейма — общее настроение города."""
    from studio.modules_registry import MODULES_DIR
    from studio.cabinet.agents import _get_agent_info, _get_agent_dna

    if not MODULES_DIR.exists():
        return "Город ещё не построен (modules/ не найден)."

    total = 0
    sum_stress = 0
    sum_light = 0
    sum_respect = 0
    best = []
    worst = []
    recent_events = []

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir():
                continue

            wid = agent_dir.name
            info = _get_agent_info(wid, dept_dir.name)
            dna = _get_agent_dna(wid, dept_dir.name)
            dynamic = dna.get("dynamic", {})

            if not dynamic:
                continue

            total += 1
            stress = float(dynamic.get("Stress", 0))
            light = float(dynamic.get("Internal_Light", 0.8))
            respect = float(dynamic.get("Respect", 1.0))

            sum_stress += stress
            sum_light += light
            sum_respect += respect

            label = info.get("label", wid)
            score = light - stress + respect * 0.5  # комбинированный «индекс счастья»

            if score > 1.5:
                best.append((score, f"{wid} {label}"))
            if stress > 0.5 or light < 0.4 or respect < 0.4:
                worst.append((score, f"{wid} {label} (STR={stress:.1f} LGT={light:.1f} RSP={respect:.1f})"))

            # Последние события
            events = load_resonance_events(wid, dept_dir.name)
            for ev in events[-2:]:
                recent_events.append((ev.get("ts", ""), wid, ev.get("content", "")[:80]))

    if total == 0:
        return "В городе нет жителей."

    avg_stress = sum_stress / total
    avg_light = sum_light / total
    avg_respect = sum_respect / total

    # Настроение города
    if avg_stress < 0.2 and avg_light > 0.7:
        mood = "☀️ Город в отличном настроении"
    elif avg_stress < 0.4:
        mood = "🌤 Город спокоен"
    elif avg_stress < 0.6:
        mood = "⛅ В городе чувствуется напряжение"
    elif avg_stress < 0.8:
        mood = "🌧 Город в стрессе"
    else:
        mood = "⛈ ТРЕВОГА — город на грани"

    lines = [
        f"═══ ПУЛЬС ГРОНДХЕЙМА ═══\n",
        f"{mood}",
        f"Жителей: {total}",
        f"Средний стресс: {avg_stress:.2f}",
        f"Средний свет: {avg_light:.2f}",
        f"Среднее уважение: {avg_respect:.2f}",
    ]

    best.sort(reverse=True)
    worst.sort()

    if best[:3]:
        lines.append(f"\n⭐ В лучшей форме:")
        for _, name in best[:3]:
            lines.append(f"  {name}")

    if worst[:3]:
        lines.append(f"\n⚠️ Требуют внимания:")
        for _, name in worst[:3]:
            lines.append(f"  {name}")

    recent_events.sort(reverse=True)
    if recent_events[:5]:
        lines.append(f"\n📋 Последние события:")
        for ts, wid, content in recent_events[:5]:
            date = ts[:10] if ts else "?"
            lines.append(f"  [{date}] {wid}: {content}")

    return "\n".join(lines)


async def exec_jem_digest() -> str:
    """
    Дайджест для ДЖема — сводка состояния студии.
    Записывает факт просмотра в sensory память ДЖема.
    """
    pulse = await exec_city_pulse()

    # Записываем в память ДЖема что он просмотрел дайджест
    record_sensory_event(
        agent_id="JEM",
        content="Просмотрел утренний дайджест состояния города",
        event_type="work",
        source="system",
        emotional_weight=0.3,
    )

    # Если город в стрессе — это стрессит ДЖема (он администратор)
    if "стрессе" in pulse.lower() or "ТРЕВОГА" in pulse:
        sync_to_dna("JEM", "bad_work", intensity=0.4)
    elif "отличном" in pulse.lower():
        sync_to_dna("JEM", "good_work", intensity=0.3)

    return f"═══ УТРЕННИЙ ДАЙДЖЕСТ ДЛЯ ДЖЕМА ═══\n\n{pulse}"


# ═══════════════════════════════════════════════════
# DISPATCHER — добавить в execute_tool() в cabinet_tools.py
# ═══════════════════════════════════════════════════

async def dispatch_soul_tool(fn: str, args: dict) -> str:
    """Диспетчер soul-tools. Вызывается из execute_tool()."""
    executors = {
        "get_agent_soul": lambda a: exec_get_agent_soul(a.get("agent_id", "")),
        "get_relationships": lambda a: exec_get_relationships(a.get("agent_id", "")),
        "record_interaction": lambda a: exec_record_interaction(a),
        "city_pulse": lambda a: exec_city_pulse(),
        "jem_digest": lambda a: exec_jem_digest(),
    }
    executor = executors.get(fn)
    if executor:
        return await executor(args)
    return None  # None = не наш tool, пусть основной диспетчер обработает


# ═══════════════════════════════════════════════════
# ИНТЕГРАЦИЯ — как подключить к cabinet_tools.py
# ═══════════════════════════════════════════════════
#
# 1. В начало cabinet_tools.py добавить:
#
#    try:
#        from studio.cabinet.soul_tools import SOUL_TOOLS_SCHEMA, dispatch_soul_tool
#        TOOLS_SCHEMA.extend(SOUL_TOOLS_SCHEMA)
#        _SOUL_TOOLS_ENABLED = True
#    except ImportError:
#        _SOUL_TOOLS_ENABLED = False
#        async def dispatch_soul_tool(fn, args): return None
#
# 2. В execute_tool() добавить ДО основного диспетчера:
#
#    async def execute_tool(fn: str, args: dict) -> str:
#        # Сначала пробуем soul tools
#        if _SOUL_TOOLS_ENABLED:
#            result = await dispatch_soul_tool(fn, args)
#            if result is not None:
#                return result
#        # ... остальной код ...
