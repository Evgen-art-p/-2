#!/usr/bin/env python3
"""
patch_sprint26_sparks.py
════════════════════════
Спринт 26 · Блок 2 — Искрение (emotional_weights → pipeline)

ИДЕЯ:
  Агенты помнят друг друга через emotional_weights.
  Если A05 не доверяет A03 (trust < 0.3) — напряжение должно
  ощущаться когда они работают вместе: чуть выше температура,
  намёк в контексте. Если A07 и A08 — старые друзья (warmth > 0.8)
  — работа идёт теплее и плавнее.

ЧТО ДЕЛАЕТ:
  В build_agent_context() добавляем шаг "искрение":
  
  1. Читаем emotional_weights агента
  2. Смотрим на коллег которые УЖЕ отработали в этом ране
     (они есть в state["results"])
  3. Вычисляем spark_score = f(warmth, trust, rivalry)
  4. Если есть значимые отношения — добавляем HINT в контекст
     ("Ты хорошо знаешь A03, доверяешь ему")
  5. Модифицируем температуру агента через spark_modifier
     (±0.05 — деликатно, не ломает работу)

ФИЗИКА:
  spark_score = warmth*0.4 + trust*0.3 - rivalry*0.3
  нейтраль = 0.5 (warmth=0.5, trust=0.5, rivalry=0.0)
  
  spark_score > 0.65 → тепло, trust_hint в контекст, temp -0.05
  spark_score < 0.35 → напряжение, tension_hint в контекст, temp +0.07
  иначе → молчим (не засоряем контекст нейтральщиной)

ПРИНЦИП:
  - Только ЗНАЧИМЫЕ отношения (deviation от нейтрали > 0.2)
  - Только коллеги которые УЖЕ в этом ране (state["results"])
  - Максимум 2 упоминания — не превращаем в мыльную оперу
  - Никаких новых каналов DNA — только temperature + hint

ФАЙЛЫ:
  studio/workshop/pipeline.py  ← build_agent_context() + call_agent()
"""

from pathlib import Path

PIPELINE_PATH = Path("studio/workshop/pipeline.py")


# ══════════════════════════════════════════════════════════════
# ФУНКЦИЯ ИСКРЕНИЯ — вставляем в pipeline.py
# ══════════════════════════════════════════════════════════════

SPARKS_FUNCTION = '''

def _get_spark_context(worker_id: str, state: dict, dept: str = "") -> tuple[str, float]:
    """
    Спринт 26 · Искрение: emotional_weights → контекст + температура.

    Читает отношения агента к коллегам которые уже отработали в этом ране.
    Возвращает (hint_text, temp_modifier).

    Физика:
      spark_score = warmth*0.4 + trust*0.3 - rivalry*0.3
      > 0.65 → тепло   → hint + temp -0.05
      < 0.35 → трение  → hint + temp +0.07
      иначе  → молчим  (нейтраль — не засоряем контекст)

    Лимит: max 2 значимых отношения за вызов.
    """
    if not _GRONDHEIM_ENABLED:
        return "", 0.0

    try:
        from studio.grondheim_memory import load_emotional_weights
        weights = load_emotional_weights(worker_id, dept)
    except Exception:
        return "", 0.0

    if not weights:
        return "", 0.0

    # Коллеги которые уже отработали в этом ране
    already_ran = set(state.get("results", {}).keys())
    if not already_ran:
        return "", 0.0

    hints = []
    temp_modifier = 0.0
    count = 0

    for colleague_id, rel in weights.items():
        if colleague_id not in already_ran:
            continue
        if count >= 2:  # не мыльная опера
            break

        warmth  = float(rel.get("warmth",  0.5))
        trust   = float(rel.get("trust",   0.5))
        respect = float(rel.get("respect", 0.5))
        rivalry = float(rel.get("rivalry", 0.0))
        memory  = rel.get("memory", "")

        # Отклонение от нейтрали — стоит ли говорить об этом?
        deviation = abs(warmth - 0.5) + abs(trust - 0.5) + rivalry
        if deviation < 0.2:
            continue  # нейтральные отношения — молчим

        spark_score = warmth * 0.4 + trust * 0.3 + respect * 0.1 - rivalry * 0.3

        if spark_score > 0.65:
            # Тепло и доверие
            if trust > 0.75:
                hint = f"С {colleague_id} у тебя крепкое доверие — его работу можно брать как надёжную основу."
            else:
                hint = f"С {colleague_id} у тебя тёплые отношения — работать с ним приятно."
            if memory:
                hint += f" ({memory[:80]})"
            hints.append(f"  🤝 {hint}")
            temp_modifier -= 0.05  # чуть спокойнее, увереннее

        elif spark_score < 0.35:
            # Трение или соперничество
            if rivalry > 0.5:
                hint = f"С {colleague_id} у тебя соперничество — проверь его работу особенно внимательно."
            elif trust < 0.3:
                hint = f"С {colleague_id} у тебя мало доверия — перепроверь его выводы своим взглядом."
            else:
                hint = f"С {colleague_id} у тебя непростые отношения — держись профессионально."
            if memory:
                hint += f" ({memory[:80]})"
            hints.append(f"  ⚡ {hint}")
            temp_modifier += 0.07  # чуть острее, напряжённее

        count += 1

    if not hints:
        return "", 0.0

    lines = ["=== ✨ ИСКРЕНИЕ (отношения с коллегами в этом ране) ==="]
    lines.extend(hints)
    lines.append("=== КОНЕЦ ИСКРЕНИЯ ===")

    return "\\n".join(lines), round(temp_modifier, 3)
'''


# ══════════════════════════════════════════════════════════════
# ШАГ 1 — добавляем функцию _get_spark_context в pipeline.py
# Вставляем после _get_lighthouse_knowledge()
# ══════════════════════════════════════════════════════════════

INSERT_AFTER = "def build_settings_ctx(state: dict) -> str:"

def patch_add_sparks_function():
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    if "_get_spark_context" in text:
        print("  ✓  pipeline.py: _get_spark_context уже есть")
        return

    if INSERT_AFTER not in text:
        print("  ⚠  pipeline.py: не найдена точка вставки (build_settings_ctx)")
        return

    text = text.replace(INSERT_AFTER, SPARKS_FUNCTION + "\n\n" + INSERT_AFTER)
    PIPELINE_PATH.write_text(text, encoding="utf-8")
    print("  ✅ pipeline.py: функция _get_spark_context добавлена")


# ══════════════════════════════════════════════════════════════
# ШАГ 2 — вызываем искрение в build_agent_context()
# После блока energy budget, перед economy
# ══════════════════════════════════════════════════════════════

# Вставляем ПОСЛЕ блока Resource Economy, ПЕРЕД Economy блоком
INSERT_SPARKS_AFTER = "    # ══ END Resource Economy ══"
INSERT_SPARKS_BEFORE = "\n\n    # ══ Economy: Cost Intuition + Ministry"

SPARKS_CALL = """

    # ══ Искрение · Спринт 26 ══
    # Отношения агента к коллегам которые уже отработали в этом ране.
    # Добавляет hint в контекст и возвращает temperature modifier.
    # Результат modifier хранится в state для call_agent().
    _spark_ctx, _spark_temp = _get_spark_context(
        worker_id, state, state.get("active_dept", "")
    )
    if _spark_ctx:
        context += _spark_ctx + "\\n\\n"
        print(f"[SPARKS] ✨ {worker_id}: искрение ({_spark_temp:+.2f}°)")
    # Сохраняем модификатор температуры для call_agent
    state.setdefault("_spark_temp", {})[worker_id] = _spark_temp
    # ══ END Искрение ══"""


def patch_add_sparks_call():
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    if '"_spark_temp"' in text:
        print("  ✓  pipeline.py: вызов _get_spark_context уже есть")
        return

    target = INSERT_SPARKS_AFTER + INSERT_SPARKS_BEFORE
    replacement = INSERT_SPARKS_AFTER + SPARKS_CALL + INSERT_SPARKS_BEFORE

    if target not in text:
        print("  ⚠  pipeline.py: не найдена точка вставки (END Resource Economy / Economy блок)")
        return

    text = text.replace(target, replacement)
    PIPELINE_PATH.write_text(text, encoding="utf-8")
    print("  ✅ pipeline.py: вызов _get_spark_context добавлен в build_agent_context()")


# ══════════════════════════════════════════════════════════════
# ШАГ 3 — применяем spark_temp modifier в call_agent()
# Суммируем с основной температурой агента (из ДНК)
# ══════════════════════════════════════════════════════════════

# В call_agent() после вычисления agent_temp — применяем модификатор
OLD_TEMP_PRINT = (
    '                    print(f"[DNA→T°] {worker_id} {label}: '
    'Stress={dynamic.get(\'Stress\',0)} Light={dynamic.get(\'Internal_Light\',0.8)} → temp={agent_temp}")'
)
NEW_TEMP_PRINT = (
    '                    print(f"[DNA→T°] {worker_id} {label}: '
    'Stress={dynamic.get(\'Stress\',0)} Light={dynamic.get(\'Internal_Light\',0.8)} → temp={agent_temp}")\n'
    '        # ── Искрение: применяем модификатор температуры · Спринт 26 ──\n'
    '        _st = state.get("_spark_temp", {}).get(worker_id, 0.0)\n'
    '        if _st != 0.0 and agent_temp is not None:\n'
    '            agent_temp = round(max(0.1, min(1.5, agent_temp + _st)), 3)\n'
    '            print(f"[SPARKS] {worker_id}: temp после искрения = {agent_temp} ({_st:+.2f})")\n'
    '        # ── END Искрение ──'
)

# Fallback: если блок не нашёлся — ищем другую точку
OLD_TEMP_FALLBACK = "    slot_id = state.get(\"_slot_id\", \"unknown\")"
NEW_TEMP_FALLBACK = (
    "    # ── Искрение: применяем модификатор температуры · Спринт 26 ──\n"
    "    _st = state.get(\"_spark_temp\", {}).get(worker_id, 0.0)\n"
    "    if _st != 0.0 and agent_temp is not None:\n"
    "        agent_temp = round(max(0.1, min(1.5, agent_temp + _st)), 3)\n"
    "        print(f\"[SPARKS] {worker_id}: temp после искрения = {agent_temp} ({_st:+.2f})\")\n"
    "    # ── END Искрение ──\n"
    "    slot_id = state.get(\"_slot_id\", \"unknown\")"
)


def patch_apply_spark_temp():
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    if '"_spark_temp"' in text and "temp после искрения" in text:
        print("  ✓  pipeline.py: spark_temp модификатор уже применяется")
        return

    if OLD_TEMP_PRINT in text:
        text = text.replace(OLD_TEMP_PRINT, NEW_TEMP_PRINT)
        PIPELINE_PATH.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py: spark_temp применяется после DNA→temperature")
    elif OLD_TEMP_FALLBACK in text:
        text = text.replace(OLD_TEMP_FALLBACK, NEW_TEMP_FALLBACK)
        PIPELINE_PATH.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py: spark_temp применяется (fallback точка)")
    else:
        print("  ⚠  pipeline.py: не найдена точка применения spark_temp в call_agent()")
        print("     Добавь вручную после вычисления agent_temp:")
        print("       _st = state.get('_spark_temp', {}).get(worker_id, 0.0)")
        print("       if _st and agent_temp: agent_temp = round(max(0.1, min(1.5, agent_temp + _st)), 3)")


# ══════════════════════════════════════════════════════════════
# ШАГ 4 — очищаем _spark_temp из state после каждого агента
# Чтобы модификатор не переносился на следующего
# ══════════════════════════════════════════════════════════════

# В process_agent_result() в начале — чистим устаревший модификатор
OLD_PROCESS_START = (
    '    info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
    '    label = info.get("label", worker_id) if info else worker_id'
)
NEW_PROCESS_START = (
    '    info = get_worker_info(worker_id, state.get("active_dept", ""))\n'
    '    label = info.get("label", worker_id) if info else worker_id\n'
    '    # Искрение · Спринт 26: очищаем модификатор — он одноразовый\n'
    '    state.get("_spark_temp", {}).pop(worker_id, None)'
)


def patch_cleanup_spark_temp():
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    if "очищаем модификатор — он одноразовый" in text:
        print("  ✓  pipeline.py: очистка _spark_temp уже есть")
        return

    if OLD_PROCESS_START in text:
        text = text.replace(OLD_PROCESS_START, NEW_PROCESS_START)
        PIPELINE_PATH.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py: очистка _spark_temp добавлена в process_agent_result()")
    else:
        print("  ⚠  pipeline.py: не найдена точка очистки _spark_temp")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("СПРИНТ 26 · БЛОК 2 — Искрение (emotional_weights → pipeline)")
    print("=" * 60)

    print("\n[1/4] Добавляем _get_spark_context() в pipeline.py...")
    patch_add_sparks_function()

    print("\n[2/4] Вызываем искрение в build_agent_context()...")
    patch_add_sparks_call()

    print("\n[3/4] Применяем spark_temp модификатор в call_agent()...")
    patch_apply_spark_temp()

    print("\n[4/4] Очистка _spark_temp в process_agent_result()...")
    patch_cleanup_spark_temp()

    print("\n" + "=" * 60)
    print("✅ ГОТОВО.")
    print()
    print("ФИЗИКА ИСКРЕНИЯ:")
    print("  spark_score = warmth×0.4 + trust×0.3 + respect×0.1 - rivalry×0.3")
    print("  > 0.65 → тепло:    hint в контекст + temp −0.05")
    print("  < 0.35 → трение:   hint в контекст + temp +0.07")
    print("  иначе  → молчим    (нейтраль не засоряет контекст)")
    print()
    print("ПРАВИЛА:")
    print("  • Только коллеги уже отработавшие в этом ране")
    print("  • Только отношения с deviation > 0.2 от нейтрали")
    print("  • Максимум 2 упоминания за агента")
    print("  • Temp modifier зажат: min=0.1, max=1.5")
    print("  • _spark_temp одноразовый — чистится после применения")
    print()
    print("ДАННЫЕ появятся автоматически после первого рана")
    print("(on_agents_interact() пишет в emotional_weights каждый ран)")
    print()
    print("СЛЕДУЮЩИЙ ШАГ: промты video_long (12 агентов)")
    print("=" * 60)
