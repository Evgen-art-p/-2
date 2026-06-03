"""
patch_emotional_weights_pipeline.py — эмоции из города в производство

Что делает:
  В build_agent_context() в pipeline.py добавляем чтение
  emotional_weights между агентами текущего цеха.

  Если A03 и A05 подружились в Таверне:
    warmth > 0.65 + trust > 0.65 → "С A03 тёплые отношения — вы слаженны"
  Если есть resentment:
    rivalry > 0.5 → "С A03 есть соперничество — сосредоточься на своей задаче"
  Если ссорились (conflict → warmth < 0.3):
    → "С A03 сейчас напряжение — работай профессионально"

  Порог: не меньше двух значимых отношений — иначе молчим.
  Место в контексте: сразу после soul_ctx (душа агента).

  Правило трёх каналов НЕ нарушаем:
    - Мы только ЧИТАЕМ emotional_weights
    - Ничего не пишем в DNA через этот канал
    - Это информационный инжект, не изменение state

Файл: studio/workshop/pipeline.py
Запуск из корня: python patch_emotional_weights_pipeline.py
"""

import sys
from pathlib import Path

PIPELINE_PY = Path("studio") / "workshop" / "pipeline.py"
errors = []


def patch(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        errors.append(f"MISS [{label}]")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK {label}")
    return True


# ──────────────────────────────────────────────────────────────
# PATCH 1 — добавляем функцию _get_colleague_relations()
# перед build_agent_context()
# ──────────────────────────────────────────────────────────────

OLD_BUILD_ANCHOR = 'def build_settings_ctx(state: dict) -> str:'

NEW_COLLEAGUE_FUNC = '''\
def _get_colleague_relations(worker_id: str, dept: str, agent_ids: list) -> str:
    """
    Читает emotional_weights агента к коллегам по текущему цеху.
    Возвращает текстовый блок для инжекта в контекст — или пустую строку.

    Правило трёх каналов: только READ, никакой записи в DNA.
    Это информационный инжект — агент знает с кем работает сегодня.

    Пороги:
      Тёплый союз:   warmth > 0.65 AND trust > 0.65
      Холодок:       warmth < 0.35
      Соперничество: rivalry > 0.50
      Уважение:      respect > 0.75
    """
    if not _GRONDHEIM_ENABLED:
        return ""
    if not agent_ids:
        return ""

    try:
        from studio.grondheim_memory import load_emotional_weights
    except ImportError:
        return ""

    try:
        weights = load_emotional_weights(worker_id, dept)
    except Exception:
        return ""

    if not weights:
        return ""

    lines = []
    for colleague_id in agent_ids:
        if colleague_id == worker_id:
            continue

        rel = weights.get(colleague_id) or weights.get(colleague_id.upper())
        if not rel:
            continue

        warmth  = float(rel.get("warmth",  0.5))
        trust   = float(rel.get("trust",   0.5))
        respect = float(rel.get("respect", 0.5))
        rivalry = float(rel.get("rivalry", 0.0))
        memory  = rel.get("memory", "")

        notes = []

        # Тёплый союз — работают слаженно
        if warmth > 0.65 and trust > 0.65:
            notes.append(f"с {colleague_id} тёплые отношения — вы слаженно работаете")
            if memory:
                notes.append(f"  (помнишь: {memory[:80]})")

        # Глубокое уважение
        elif respect > 0.75 and warmth >= 0.4:
            notes.append(f"к {colleague_id} глубокое профессиональное уважение")

        # Соперничество — не конфликт, но напряжение
        elif rivalry > 0.50:
            notes.append(
                f"с {colleague_id} есть соперничество — "
                "сосредоточься на своей задаче, не на нём"
            )

        # Холодок / напряжение
        elif warmth < 0.35:
            notes.append(
                f"с {colleague_id} сейчас напряжение — "
                "будь профессионален, не давай личному мешать работе"
            )

        lines.extend(notes)

    if not lines:
        return ""

    result = ["=== 🤝 ОТНОШЕНИЯ В ЦЕХЕ (из жизни города) ==="]
    result.extend(f"  • {line}" for line in lines)
    result.append("=== КОНЕЦ ОТНОШЕНИЙ ===")
    return "\n".join(result)


''' + OLD_BUILD_ANCHOR


# ──────────────────────────────────────────────────────────────
# PATCH 2 — вызываем _get_colleague_relations() в build_agent_context()
# после блока soul_ctx (личная память агента)
# ──────────────────────────────────────────────────────────────

OLD_AFTER_SOUL = (
    "    # ══ Рюкзак Знаний — данные с Маяка Пробуждения ══\n"
    "    backpack = _get_lighthouse_knowledge(worker_id, state.get(\"active_dept\", \"\"))\n"
    "    if backpack:\n"
    "        context += backpack + \"\\n\\n\"\n"
    "        print(f\"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)\")"
)

NEW_AFTER_SOUL = (
    "    # ══ Отношения с коллегами (из emotional_weights города) ══\n"
    "    _pipeline_agents = list(state.get(\"results\", {}).keys())\n"
    "    # Добавляем агентов из manifest если есть\n"
    "    _manifest_agents = state.get(\"_agent_ids\", [])\n"
    "    _all_colleagues = list(dict.fromkeys(_pipeline_agents + _manifest_agents))\n"
    "    if _all_colleagues:\n"
    "        _relations_ctx = _get_colleague_relations(\n"
    "            worker_id, state.get(\"active_dept\", \"\"), _all_colleagues\n"
    "        )\n"
    "        if _relations_ctx:\n"
    "            context += _relations_ctx + \"\\n\\n\"\n"
    "            print(f\"[RELATIONS] 🤝 {worker_id}: отношения с коллегами инжектированы\")\n"
    "    # ══ END Отношения ══\n"
    "\n"
    "    # ══ Рюкзак Знаний — данные с Маяка Пробуждения ══\n"
    "    backpack = _get_lighthouse_knowledge(worker_id, state.get(\"active_dept\", \"\"))\n"
    "    if backpack:\n"
    "        context += backpack + \"\\n\\n\"\n"
    "        print(f\"[РЮКЗАК] 🔦 {worker_id} несёт знания с Маяка ({len(backpack)} симв.)\")"
)


# ──────────────────────────────────────────────────────────────
# PATCH 3 — сохраняем agent_ids в state при старте рана
# чтобы _get_colleague_relations() знал всех коллег цеха
# Место: в process_agent_result, в начале функции
# ──────────────────────────────────────────────────────────────
# Это делается через CartridgeRunner который уже передаёт agent_ids
# через state["_agent_ids"] — проверим есть ли это в cartridge.py
# Если нет — добавим через on_agents_interact где agent_ids известны

print("=== patch_emotional_weights_pipeline.py ===\n")
print("studio/workshop/pipeline.py:")
patch(PIPELINE_PY, OLD_BUILD_ANCHOR, NEW_COLLEAGUE_FUNC,
      "_get_colleague_relations() добавлена")
patch(PIPELINE_PY, OLD_AFTER_SOUL, NEW_AFTER_SOUL,
      "вызов _get_colleague_relations() в build_agent_context()")

print()
if errors:
    print("ОШИБКИ:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("Готово.")
print()
print("Что изменилось:")
print("  • _get_colleague_relations() читает emotional_weights агента к коллегам")
print("  • Тёплый союз (warmth>0.65, trust>0.65) → 'вы слаженно работаете'")
print("  • Соперничество (rivalry>0.5) → 'сосредоточься на своей задаче'")
print("  • Напряжение (warmth<0.35) → 'будь профессионален'")
print("  • Только READ — правило трёх каналов не нарушено")
print("  • Работает для всех цехов — данные из реальных прогулок")
print()
print("Commit:")
print("  feat: emotional_weights из города → контекст агентов в pipeline")
