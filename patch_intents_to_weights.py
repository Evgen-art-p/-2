#!/usr/bin/env python3
"""
patch_intents_to_weights.py
════════════════════════════════════════════════════════════════
Подключает morning_intents из city_state к compute_location_weights().

Утренний Чекаут генерирует намерения агента:
  ["отдых в Таверне", "Маяк за смыслом", "домой"]

Эти намерения поднимают вес нужных локаций при прогулке.
Агент идёт туда куда с утра собирался — если не передумал.

Логика:
  - Читаем city_state["morning_intents"][agent_key]
  - Для каждого намерения ищем совпадение с именем локации
  - Совпавшие локации получают бонус +0.15 (первое) и +0.08 (остальные)
  - Всё через agent_key который передаём как параметр

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
from pathlib import Path
from datetime import datetime

CITY_WALKER = Path("studio/city_walker.py")

if not CITY_WALKER.exists():
    print("❌ studio/city_walker.py не найден")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════
# 1. Патчим compute_location_weights — добавляем параметр agent_key
#    и блок чтения intents в конце функции
# ════════════════════════════════════════════════════════════════

OLD_SIGNATURE = """def compute_location_weights(
    dna: dict,
    memory: dict,
    locations: list[dict],
) -> dict[str, float]:"""

NEW_SIGNATURE = """def compute_location_weights(
    dna: dict,
    memory: dict,
    locations: list[dict],
    agent_key: str = "",
) -> dict[str, float]:"""

# Блок вставляем перед return weights в конце функции
OLD_RETURN = "    return weights\n\n\ndef format_weights_hint"

NEW_RETURN = """    # ══ КАРТРИДЖ НАМЕРЕНИЙ · Спринт 23 ══
    # Читаем утренние намерения агента из city_state.
    # Каждое намерение — строка типа "Маяк за смыслом" или "отдых в Таверне".
    # Ищем совпадение с именем локации (по вхождению ключевого слова).
    # Первое совпавшее намерение: +0.15, остальные: +0.08.
    # Это НЕ хардкод — это утреннее решение самого агента.
    if agent_key:
        try:
            _cs = {}
            if CITY_STATE.exists():
                import json as _json
                _cs = _json.loads(CITY_STATE.read_text(encoding="utf-8"))
            intents = _cs.get("morning_intents", {}).get(agent_key, [])
            if intents:
                intent_bonuses = [0.15] + [0.08] * (len(intents) - 1)
                for intent_str, bonus in zip(intents, intent_bonuses):
                    intent_lower = intent_str.lower()
                    for loc_name in list(weights.keys()):
                        # Проверяем вхождение названия локации в намерение
                        # или ключевого слова намерения в название локации
                        loc_lower = loc_name.lower()
                        loc_words = [w for w in loc_lower.split() if len(w) > 3]
                        intent_words = [w for w in intent_lower.split() if len(w) > 3]
                        match = (
                            loc_lower in intent_lower or
                            any(lw in intent_lower for lw in loc_words) or
                            any(iw in loc_lower for iw in intent_words)
                        )
                        if match:
                            old_w = weights[loc_name]
                            weights[loc_name] = round(min(0.95, old_w + bonus), 3)
                            print(
                                f"[INTENT] 🎯 {agent_key}: "
                                f"'{intent_str}' → {loc_name} "
                                f"+{bonus:.2f} ({old_w:.2f}→{weights[loc_name]:.2f})"
                            )
                            break  # одно намерение — одна локация
        except Exception as _intent_err:
            print(f"[INTENT] ⚠ {agent_key}: {_intent_err}")
    # ══ END КАРТРИДЖ НАМЕРЕНИЙ ══

    return weights


def format_weights_hint"""

# ════════════════════════════════════════════════════════════════
# 2. Патчим walk_one_agent — передаём agent_key в compute_location_weights
# ════════════════════════════════════════════════════════════════

OLD_WEIGHTS_CALL = """    # ═══ ГОЛОД ПО ЗНАНИЯМ: вычисляем веса ═══
    weights = compute_location_weights(dna, memory, locations)
    weights_hint = format_weights_hint(weights)"""

NEW_WEIGHTS_CALL = """    # ═══ ГОЛОД ПО ЗНАНИЯМ + КАРТРИДЖ НАМЕРЕНИЙ: вычисляем веса ═══
    # agent_key = "{folder}_{workshop}" — ключ из morning_intents в city_state
    _agent_key = f"{folder}_{workshop}"
    weights = compute_location_weights(dna, memory, locations, agent_key=_agent_key)
    weights_hint = format_weights_hint(weights)"""


def apply():
    code = CITY_WALKER.read_text(encoding="utf-8")
    errors = []

    backup = CITY_WALKER.with_suffix(".py.bak_intents")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап: {backup.name}")

    # 1. Сигнатура функции
    if "agent_key: str" in code:
        print("  ℹ agent_key уже есть в сигнатуре")
    elif OLD_SIGNATURE in code:
        code = code.replace(OLD_SIGNATURE, NEW_SIGNATURE, 1)
        print("  ✅ Сигнатура compute_location_weights обновлена")
    else:
        errors.append("Сигнатура compute_location_weights не найдена")

    # 2. Блок intents перед return
    if "КАРТРИДЖ НАМЕРЕНИЙ" in code:
        print("  ℹ Блок intents уже есть")
    elif OLD_RETURN in code:
        code = code.replace(OLD_RETURN, NEW_RETURN, 1)
        print("  ✅ Блок КАРТРИДЖ НАМЕРЕНИЙ добавлен")
    else:
        errors.append("Якорь return weights не найден")

    # 3. Вызов в walk_one_agent
    if "_agent_key" in code:
        print("  ℹ agent_key уже передаётся в walk_one_agent")
    elif OLD_WEIGHTS_CALL in code:
        code = code.replace(OLD_WEIGHTS_CALL, NEW_WEIGHTS_CALL, 1)
        print("  ✅ walk_one_agent: agent_key передаётся в compute_location_weights")
    else:
        errors.append("Якорь вызова compute_location_weights в walk_one_agent не найден")

    if errors:
        print(f"\n⚠ Ошибки ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")

    CITY_WALKER.write_text(code, encoding="utf-8")
    print("  ✅ city_walker.py сохранён")
    return not errors


def main():
    print("=" * 60)
    print("ПАТЧ: morning_intents → compute_location_weights")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    ok = apply()

    print()
    if ok:
        print("✅ Готово.")
        print()
        print("Как работает:")
        print("  1. 🌅 день → чекаут → city_state['morning_intents']")
        print("  2. 🚶 прогулка → compute_location_weights читает intents")
        print("  3. Совпавшие локации получают бонус +0.15/+0.08")
        print("  4. Агент идёт туда куда с утра собирался")
        print()
        print("В консоли увидишь:")
        print("  [INTENT] 🎯 A05_social_mix: 'Маяк за смыслом' → Маяк Пробуждения +0.15")
    else:
        print("⚠ Частично применён — проверь ошибки выше")
    print("=" * 60)


if __name__ == "__main__":
    main()
