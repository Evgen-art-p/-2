"""
sprint30_patch_lucas.py — точечный патч промпта Лукаса A05
Запускать из корня студии: python sprint30_patch_lucas.py
"""
from pathlib import Path

path = Path("studio/modules/video_long/A05/forge/prompt.md")

if not path.exists():
    print(f"❌ Файл не найден: {path}")
    exit(1)

content = path.read_text(encoding="utf-8")

# ── Патч 1: Переименовываем старый Шаг 4 → Шаг 5 ──────────────
OLD_STEP4 = "### Шаг 4: Проверь по history_dna.visual_history.avoid"
NEW_STEP5 = "### Шаг 5: Проверь по history_dna.visual_history.avoid"

if OLD_STEP4 not in content:
    print("⚠️  Шаг 4 (проверка avoid) не найден — возможно уже применён")
else:
    content = content.replace(OLD_STEP4, NEW_STEP5, 1)
    print("✅ Шаг 4 → Шаг 5 (проверка avoid)")

# ── Патч 2: Добавляем новый Шаг 4 разметки shot_type ──────────
NEW_STEP4 = """### Шаг 4: Разметь shot_type

Для каждого shot обязательно проставь тип:

| shot_type | Когда | character_id |
|-----------|-------|-------------|
| `"dialog"` | персонаж говорит, framing close_up или medium, в сцене есть dialogue | имя из history_dna |
| `"action"` | движение, реакция, рот не важен | null |
| `"broll"` | пейзаж, объект, атмосфера без речи | null |

ПРАВИЛО:
- `dialogue != null` И `framing == close_up / medium` → **dialog**
- `dialogue == null` ИЛИ `framing == wide / aerial` → **action** или **broll**
- Групповые планы где рот не виден → **action** или **broll**, не dialog

`character_id` — только для dialog. Берёшь из `history_dna.character_memory`. Иначе null.

"""

if "### Шаг 4: Разметь shot_type" in content:
    print("⚠️  Шаг 4 разметки уже есть — пропускаю")
else:
    content = content.replace(NEW_STEP5, NEW_STEP4 + NEW_STEP5, 1)
    print("✅ Шаг 4 разметки shot_type добавлен")

# ── Патч 3: shot_type и character_id в JSON схему ─────────────
OLD_JSON = '''          "duration_sec": 0,
          "composition_note": "rule_of_thirds / center / diagonal / frame_in_frame"'''

NEW_JSON = '''          "duration_sec": 0,
          "composition_note": "rule_of_thirds / center / diagonal / frame_in_frame",
          "shot_type": "dialog / action / broll",
          "character_id": "имя персонажа или null"'''

if '"shot_type"' in content:
    print("⚠️  shot_type в JSON уже есть — пропускаю")
elif OLD_JSON not in content:
    print("⚠️  JSON маркер не найден — пропускаю")
else:
    content = content.replace(OLD_JSON, NEW_JSON, 1)
    print("✅ shot_type и character_id добавлены в JSON схему")

# ── Патч 4: shot_type в RULES контракт ─────────────────────────
OLD_RULES = "- `motion_intent` — рекомендация. Феликс имеет право отступить."
NEW_RULES = """- `motion_intent` — рекомендация. Феликс имеет право отступить.
- `shot_type` — обязательное поле. Один из: `dialog`, `action`, `broll`.
- `character_id` — обязательное поле для dialog. Для остальных — `null`."""

if "shot_type` — обязательное" in content:
    print("⚠️  shot_type в RULES уже есть — пропускаю")
elif OLD_RULES not in content:
    print("⚠️  RULES маркер не найден — пропускаю")
else:
    content = content.replace(OLD_RULES, NEW_RULES, 1)
    print("✅ shot_type добавлен в RULES")

# ── Сохраняем ──────────────────────────────────────────────────
path.write_text(content, encoding="utf-8")
print("\n✅ A05/forge/prompt.md обновлён — Спринт 30")
