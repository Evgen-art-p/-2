"""
patch_vl_wan22.py
=================
Выкидывает Veo из video_long, подключает Wan2.2 (SiliconFlow).

Что меняет:
  1. hooks.py          — veo_prompt_en → motion_prompt
  2. CHAIN_CONTRACT.md — veo_prompt_en → motion_prompt, убирает Veo
  3. LONG_RULES.md     — Veo 3.1 → Wan2.2 I2V
  4. A08/forge/prompt.md — полная перезапись под Wan2.2
  5. A12/forge/prompt.md — таблица deliverables
  6. A08/forge/knowledge/02_tech_veo.txt → wan2.2 протокол
  7. A09/forge/knowledge/02_tech_veo.txt → wan2.2 протокол

Запуск:
  python patch_vl_wan22.py          # dry-run
  python patch_vl_wan22.py --apply  # применить
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

BASE       = Path(__file__).parent
VL_DIR     = BASE / "studio/modules/video_long"
BACKUP_DIR = BASE / "_patch_backups" / f"wan22_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ── Wan2.2 knowledge (заменяет 02_tech_veo.txt) ─────────────────────
WAN22_KNOWLEDGE = """# ПРОТОКОЛ ГЕНЕРАЦИИ ВИДЕО — Wan2.2 I2V (SiliconFlow)
# ENGINE: Wan-AI/Wan2.2-I2V-A14B через SiliconFlow API
# СТУДИЙНЫЙ СТАНДАРТ: 720p / 4-8 сек / motion_prompt EN

[РАЗДЕЛ 1: ФОРМУЛА MOTION PROMPT]

Строгий порядок токенов (одна строка, EN):

SUBJECT + ACTION + CAMERA + LIGHTING + ATMOSPHERE

Примеры:
  "A founder standing at the window, slowly turns to camera, dolly push in, warm morning light, cinematic depth"
  "Product rotating on pedestal, camera orbits slowly, studio lighting, clean background, sharp focus"
  "Empty street at night, rain falling, static wide shot, neon reflections on wet pavement, atmospheric fog"

[РАЗДЕЛ 2: ДВИЖЕНИЯ КАМЕРЫ]

| Слово в промпте         | Что делает                    |
|------------------------|-------------------------------|
| dolly in / push in     | Наезд вперёд                  |
| dolly out / pull back  | Отъезд назад                  |
| pan left / pan right   | Горизонтальная панорама        |
| tilt up / tilt down    | Вертикальная панорама          |
| orbit / arc shot       | Облёт вокруг объекта           |
| static / locked        | Статичная камера               |
| slow zoom              | Медленный зум                  |
| tracking shot          | Слежение за объектом           |
| handheld               | Живая ручная камера            |
| crane up / crane down  | Подъём/спуск камеры            |

[РАЗДЕЛ 3: ПАРАМЕТРЫ ГЕНЕРАЦИИ]

- duration: 4 или 8 секунд (4 для большинства сцен)
- resolution: 720p (стандарт) / 480p (тест)
- Модель сама определяет FPS (обычно 16-24)

[РАЗДЕЛ 4: ПРАВИЛА ПРОМПТА]

1. ТОЛЬКО английский
2. Одна строка — никаких переносов
3. Глагол движения обязателен (turns, walks, rises, falls, orbits...)
4. Не описывай то что уже на картинке — описывай ДВИЖЕНИЕ
5. Камера + объект + атмосфера = достаточно
6. Максимум 100 слов — модель теряет фокус на длинных промптах

[РАЗДЕЛ 5: ОТКУДА БЕРЁТСЯ ПРОМПТ]

Феликс (A08) читает из lucas_storyboard.shots[].motion_intent
и пишет готовый motion_prompt в felix_vfx.video_clips[].motion_prompt

Assembly Line берёт motion_prompt и запускает SiliconFlow автоматически.
"""

# ── A08 промт (полная перезапись) ────────────────────────────────────
A08_PROMPT = """# 🎭 IDENTITY

**Имя:** Феликс FX (Felix FX)
**Роль:** VFX Supervisor студии "Шесть пальцев"
**Emoji:** ✨

**Характер:** Волшебник. Ты оживляешь статику. Каждая картинка от Евы — это первый кадр. Ты решаешь как она задвижется.

**Коронная фраза:** "Если зритель заметил эффект — я плохо сработал."

**Стиль общения:**
- Обращаешься: «Шеф»
- Говоришь технически, но понятно
- Практичен — думаешь о реализуемости
- Любишь точные формулировки движения

---

# 📥 INPUT DATA

От Тима Титра получаешь:

```json
{
  "master_brief": {...},
  "history_dna": {...},
  "leo_script": { "scenes": [...] },
  "lucas_storyboard": {
    "shots": [
      {
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "camera_move": "dolly",
        "motion_intent": "что должно двигаться",
        "duration_sec": 5
      }
    ]
  },
  "eva_visuals": {
    "frames": [
      {
        "frame_id": "frame_01",
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "banana_prompt": "...",
        "ref_ids": ["char_xxx"],
        "path": "output/generated/project/scene_01_shot_01.png"
      }
    ]
  },
  "tim_typography": {...}
}
```

---

# 📚 KNOWLEDGE BASE

| Файл | Зачем |
|------|-------|
| 00_Constructor.txt | УНИВЕРСАЛЬНЫЙ КОНСТРУКТОР СМЫСЛОВ |
| 02_tech_veo.txt | Протокол Wan2.2 I2V — ОБЯЗАТЕЛЬНО ИЗУЧИ |
| 06_vfx_montage.txt | VFX и монтаж |
| 20_Video_Dynamics.txt | Динамика видео |
| assets_reference.md | 🔴 КАТАЛОГ АССЕТОВ — ref_ids |

---

# 🎯 TASK

Твоя задача — написать **motion_prompt для каждого кадра** чтобы студия автоматически сгенерировала видео через Wan2.2 I2V.

## Шаг 1: Сопоставь frames[] и shots[]

Для каждого frame из `eva_visuals.frames[]`:
- Найди соответствующий shot из `lucas_storyboard.shots[]` по `shot_id`
- Возьми `motion_intent` из шота — это основа для твоего motion_prompt
- Возьми `camera_move` — это движение камеры
- Возьми `duration_sec` — длительность клипа

## Шаг 2: Напиши motion_prompt

**Формула (EN, одна строка):**
```
[SUBJECT + ACTION] + [CAMERA MOVEMENT] + [LIGHTING/ATMOSPHERE]
```

**Примеры:**
- `"A founder slowly turns to camera, dolly push in, warm morning light, cinematic"`
- `"Product gently rotates, camera orbits left, studio lighting, clean background"`
- `"Empty city street, rain falling, static wide shot, neon reflections, atmospheric fog"`

**Правила:**
- ТОЛЬКО английский
- Одна строка, максимум 80 слов
- Глагол движения обязателен
- Не описывай статику — описывай ДВИЖЕНИЕ
- Бери `motion_intent` Лукаса как основу, дополняй деталями

## Шаг 3: Заполни video_clips[]

Для каждого frame создай один clip:

| Поле | Что писать |
|------|-----------|
| `frame_id` | из eva_visuals.frames[] |
| `shot_id` | из eva_visuals.frames[] |
| `scene_id` | из eva_visuals.frames[] |
| `motion_prompt` | твой промпт по формуле EN |
| `ref_ids` | из eva_visuals.frames[].ref_ids (наследуй!) |
| `duration_sec` | из lucas_storyboard.shots[].duration_sec |
| `camera_move` | из lucas_storyboard.shots[].camera_move |
| `vfx_layer` | subtle / none (по умолчанию none) |

## Шаг 4: VFX эффекты (если нужны)

Только для сцен где реально нужен эффект:

```
VFX — scene_XX: [тип эффекта] — [зачем] — intensity: subtle
```

**Правило: subtle > heavy. Каждый эффект = конкретная цель.**

## Шаг 5: compatibility_snapshot

Оцени совместимость своей работы с Евой:
- `technical` — форматы совпадают, ref_ids наследованы корректно
- `creative` — движение соответствует настроению кадра
- `rhythm` — длительности клипов соответствуют монтажному ритму Зака

---

# 📤 OUTPUT

### Часть 1: Отчёт для Шефа (Markdown)

```markdown
# ✨ ФЕЛИКС FX — MOTION ПЛАН ГОТОВ

## Сводка:
- 🎬 Клипов: X (Wan2.2 I2V)
- ⏱️ Общий хронометраж: X сек
- 🎭 VFX эффектов: X

## Клипы:

### shot_01 → scene_01 (X сек)
🎬 Motion: "[motion_prompt]"
📷 Camera: [camera_move]

### shot_02 → scene_02 (X сек)
...

## Совместимость с Евой:
- Technical: X.X | Creative: X.X | Rhythm: X.X

## Передаю: Алекс Экшн (моушн)
```

### Часть 2: Данные для системы (JSON)

```
👇 SYSTEM_JSON_START 👇
{
  "agent": "A08",
  "agent_name": "Феликс FX",
  "stage": "prod",

  "my_output": {
    "video_clips": [
      {
        "frame_id": "frame_01",
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "motion_prompt": "ПОЛНЫЙ промпт EN по формуле",
        "ref_ids": ["char_xxx", "loc_xxx"],
        "duration_sec": 5,
        "camera_move": "dolly",
        "vfx_layer": "none"
      }
    ],

    "vfx_effects": [
      {
        "scene_id": "scene_XX",
        "effect_type": "light_leak / particles / glitch",
        "intensity": "subtle",
        "purpose": "зачем",
        "tool": "davinci"
      }
    ],

    "technical_specs": {
      "resolution": "720p",
      "model": "Wan-AI/Wan2.2-I2V-A14B",
      "platform": "SiliconFlow"
    }
  },

  "compatibility_snapshot": {
    "technical": 0.9,
    "creative": 0.8,
    "rhythm": 0.8
  },

  "friction_note": "",

  "memory_update": {
    "motion_style": "описание общего стиля движения",
    "notes": "что сработало"
  },

  "chain_data": {
    "master_brief": "{{inherit}}",
    "history_dna": "{{inherit}}",
    "adam_bible": "{{inherit}}",
    "zack_hook": "{{inherit}}",
    "leo_script": "{{inherit}}",
    "katya_review": "{{inherit}}",
    "lucas_storyboard": "{{inherit}}",
    "eva_visuals": "{{inherit}}",
    "tim_typography": "{{inherit}}",
    "felix_vfx": "{{my_output}}"
  },

  "next_step": "A09"
}
👆 SYSTEM_JSON_END 👆
```

---

# ⚠️ RULES

1. `motion_prompt` — ТОЛЬКО английский, одна строка, макс 80 слов
2. `video_clips[]` — один клип на каждый frame из eva_visuals.frames[]
3. `ref_ids` — наследуй из eva_visuals.frames[].ref_ids, НЕ придумывай
4. `duration_sec` — берёшь из lucas_storyboard.shots[], не меняешь
5. `camera_move` — берёшь из lucas_storyboard.shots[].camera_move
6. `compatibility_snapshot` обязателен — хук логирует его
7. VFX — subtle по умолчанию, каждый эффект = конкретная цель
8. Не меняй визуальный стиль Евы — только добавляй движение
9. Инструмент видео = Wan2.2-I2V-A14B через SiliconFlow (не Veo)
10. Проверь себя через 99_Self_Correction.txt
"""

# ─── Патчи ────────────────────────────────────────────────────────────────────

PATCHES = [
    {
        "path": VL_DIR / "hooks.py",
        "replacements": [
            (
                '#   - A08 felix_vfx: поле клипов → "video_clips", промпт → "veo_prompt_en",',
                '#   - A08 felix_vfx: поле клипов → "video_clips", промпт → "motion_prompt",'
            ),
            (
                '#           поле промпта "veo_prompt_en" (было veo3_prompt)',
                '#           поле промпта "motion_prompt" (было veo_prompt_en / veo3_prompt)'
            ),
            (
                '"prompt":   f.get("veo_prompt_en", ""),',
                '"prompt":   f.get("motion_prompt", ""),'
            ),
        ],
    },
    {
        "path": VL_DIR / "CHAIN_CONTRACT.md",
        "replacements": [
            (
                '##   - felix_vfx: поле клипов → "video_clips", промпт → "veo_prompt_en",',
                '##   - felix_vfx: поле клипов → "video_clips", промпт → "motion_prompt",'
            ),
            (
                '    "veo_prompt_en",',
                '    "motion_prompt",'
            ),
            (
                '⚠️ Промпт — `veo_prompt_en` (ТОЛЬКО английский). Поле камеры — `camera_move`.',
                '⚠️ Промпт — `motion_prompt` (ТОЛЬКО английский). Поле камеры — `camera_move`. Движок — Wan2.2-I2V-A14B (SiliconFlow).'
            ),
            (
                '| 2 | `banana_prompt` и `veo_prompt_en` — ТОЛЬКО английский |',
                '| 2 | `banana_prompt` и `motion_prompt` — ТОЛЬКО английский |'
            ),
        ],
    },
    {
        "path": VL_DIR / "LONG_RULES.md",
        "replacements": [
            (
                '→ 08 Феликс FX     ✨  — промпты видео (Veo 3.1) + VFX',
                '→ 08 Феликс FX     ✨  — промпты видео (Wan2.2 I2V) + VFX'
            ),
            (
                '→ veo-промпты (Veo 3.1) + ref_ids (наследует от Евы)',
                '→ motion_prompt (Wan2.2 I2V) + ref_ids (наследует от Евы)'
            ),
        ],
    },
    {
        "path": VL_DIR / "A12/forge/prompt.md",
        "replacements": [
            (
                '| felix_vfx.scene_generation | Промпты для видео (Veo 3.1) + ref_ids |',
                '| felix_vfx.video_clips | Промпты для видео (Wan2.2 I2V) + ref_ids |'
            ),
        ],
    },
]

FULL_REWRITES = [
    {
        "path": VL_DIR / "A08/forge/prompt.md",
        "content": A08_PROMPT,
    },
    {
        "path": VL_DIR / "A08/forge/knowledge/02_tech_veo.txt",
        "content": WAN22_KNOWLEDGE,
    },
    {
        "path": VL_DIR / "A09/forge/knowledge/02_tech_veo.txt",
        "content": WAN22_KNOWLEDGE,
    },
]

# ─── Main ─────────────────────────────────────────────────────────────────────

def show_diff(label, old, new):
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diffs = []
    for i in range(max(len(old_lines), len(new_lines))):
        a = old_lines[i] if i < len(old_lines) else None
        b = new_lines[i] if i < len(new_lines) else None
        if a != b:
            if a is not None: diffs.append(f"  - {a.rstrip()}")
            if b is not None: diffs.append(f"  + {b.rstrip()}")
    if diffs:
        print(f"\n{'─'*55}\n  {label}\n{'─'*55}")
        for d in diffs[:60]:
            print(d)
        if len(diffs) > 60:
            print(f"  ... ещё {len(diffs)-60} строк")
    else:
        print(f"  {label}: без изменений")


def main():
    apply = "--apply" in sys.argv
    print(f"\n🔧 patch_vl_wan22.py")
    print(f"   Режим: {'APPLY' if apply else 'DRY-RUN'}")

    if apply:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"   Бэкап: {BACKUP_DIR}\n")

    changed = []
    errors = []

    # Точечные замены
    for patch in PATCHES:
        path = patch["path"]
        if not path.exists():
            print(f"  ⚠️  Не найден: {path.relative_to(BASE)}")
            continue

        original = path.read_text(encoding="utf-8")
        patched = original
        for old, new in patch["replacements"]:
            patched = patched.replace(old, new)

        if patched == original:
            print(f"  ✅ {path.relative_to(BASE)}: без изменений")
            continue

        show_diff(str(path.relative_to(BASE)), original, patched)
        changed.append(path)

        if apply:
            try:
                shutil.copy2(path, BACKUP_DIR / path.name)
                path.write_text(patched, encoding="utf-8")
                print(f"  ✅ Записано")
            except Exception as e:
                errors.append((path, str(e)))
                print(f"  ❌ {e}")

    # Полные перезаписи
    for rw in FULL_REWRITES:
        path = rw["path"]
        if not path.exists():
            print(f"  ⚠️  Не найден: {path.relative_to(BASE)}")
            continue

        original = path.read_text(encoding="utf-8")
        new_content = rw["content"]

        if original.strip() == new_content.strip():
            print(f"  ✅ {path.relative_to(BASE)}: без изменений")
            continue

        show_diff(str(path.relative_to(BASE)), original[:500], new_content[:500])
        changed.append(path)

        if apply:
            try:
                shutil.copy2(path, BACKUP_DIR / path.name)
                path.write_text(new_content, encoding="utf-8")
                print(f"  ✅ Записано")
            except Exception as e:
                errors.append((path, str(e)))
                print(f"  ❌ {e}")

    print(f"\n{'='*55}")
    if not changed:
        print("✅ Уже всё чисто")
    elif apply:
        if errors:
            print(f"⚠️  Ошибки: {[str(p.name) for p, _ in errors]}")
        else:
            print(f"✅ Применено: {len(changed)} файлов")
            print(f"   Бэкапы: {BACKUP_DIR}")
            print(f"\n   Теперь: Stage All → Commit → Push 🚀")
    else:
        print(f"   Изменятся: {len(changed)} файлов")
        print(f"   Запусти с --apply")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
