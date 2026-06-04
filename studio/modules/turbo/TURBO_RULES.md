# 📜 TURBO PIPELINE — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Быстрый конвейер шортсов

**Версия:** 4.2
**Дата:** 2026-06-02
**Режим:** TURBO (5 агентов)
**Модель изображений:** Nano Banana 2 (fal-ai/nano-banana-2)
**Модель анимации:** Wan2.2 I2V (SiliconFlow)
**Озвучка:** ElevenLabs (музыка + SFX) + CosyVoice (VO)
**Монтаж:** ffmpeg через 006_MONTEUR

---

## ⚡ ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.1

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Veo3 → Wan2.2 I2V** | Veo3 недоступен. Wan2.2 через SiliconFlow |
| 2 | **Поля анимации переименованы** | `veo3_prompt` → `wan_motion_prompt`, `veo3_camera_motion` → `wan_camera_move`, `veo3_duration_sec` → `wan_duration_sec` |
| 3 | **A02 Мими — реальная озвучка + audio review** | hooks.py генерирует ElevenLabs + CosyVoice, Мими слушает трек и даёт APPROVED/REJECTED |
| 4 | **A03 — три этапа: промпты + self-review картинок + clip-review клипов** | Никто не сдаёт вслепую. Визор смотрит на всё своими глазами |
| 5 | **ОТК через vision_client** | PASS/REJECT по стандарту video_long. Брак → `output/rejected/` |
| 6 | **Chain Integrity Check в A05** | 7 пунктов. BLOCKED → цепочка возвращается. APPROVED → Монтажёр |
| 7 | **Монтажёр после A05** | hooks.py запускает 006_MONTEUR → ffmpeg → `final.mp4` |
| 8 | **Ministry score учитывает клипы и аудио** | Более честная оценка рана |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
A01 / T1 Стелла Стратег (🧠) — стратегия + сценарий + SEO + подбор ассетов
        │
        ├──→ A02 / T2 Мими Мем (🎵)                       ⎤
        │    Вызов 1: пишет промпты                         ⎥ ПАРАЛЛЕЛЬНО
        │    hooks → ElevenLabs музыка + SFX + CosyVoice VO ⎥
        │    Вызов 2: слушает трек → APPROVED/REJECTED       ⎥
        │                                                    ⎥
        └──→ A03 / T3 Визор (🎬)                            ⎦
             Вызов 1: пишет промпты (banana + wan)
             hooks → Nano Banana PNG + vision OTK
             Вызов 2: смотрит на картинки → APPROVED/REJECTED
             hooks → Wan2.2 I2V → mp4 клипы + grid
             Вызов 3: смотрит на grid клипов → APPROVED/REJECTED
                    │
                    ▼
        A04 / T4 Постпро (✂️) — монтаж + retention + субтитры
                    │
                    ▼
        A05 / T5 Финализатор (🏁) [qa_agent]
             Chain Integrity Check (7 пунктов)
             → APPROVED: hooks → обложки + deliverables + Монтажёр → final.mp4
             → BLOCKED: возврат цепочки с failed_checks
```

---

## 2. ПРОТОКОЛ chain_data

| Агент | worker_id | Получает | Добавляет |
|-------|-----------|----------|-----------|
| T1 Стелла | A01 | master_brief | stella_strategy |
| T2 Мими | A02 | master_brief, stella_strategy | mimi_sound (+ audio paths + audio_assessment от hooks) |
| T3 Визор | A03 | master_brief, stella_strategy | vizor_visual (+ paths + self_assessment + clip_assessment от hooks) |
| T4 Постпро | A04 | master_brief, stella_strategy, mimi_sound, vizor_visual | postpro |
| T5 Финализатор | A05 | ВСЁ | thumbnail (+ paths), chain_check, t5_deliverables, final_dna |

---

## 3. ФОРМАТ ВЫВОДА

**Порядок: JSON → Markdown. JSON ВСЕГДА ПЕРВЫМ.**

```
👇 SYSTEM_JSON_START 👇
{ ... }
👆 SYSTEM_JSON_END 👆
```

---

## 4. СЕГМЕНТАЦИЯ

Стелла (T1 / A01) определяет сегменты. Все следуют её разбивке.

| Сегмент | Тайминг | Назначение |
|---------|---------|------------|
| 1 | 0–1.5s | hook |
| 2 | 1.5–5s | setup |
| 3 | 5–15s | body |
| 4 | 15–25s | climax |
| 5 | 25–30s | cta_loop |

---

## 5. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин | Кто НЕ делает |
|------|--------|---------------|
| Сценарий, сегменты, тайминги | T1 Стелла / A01 | — |
| Подбор ассетов (selected_assets) | T1 Стелла / A01 | — |
| Звук: music.prompt, sfx_list, beat_map, vo_lines | T2 Мими / A02 | — |
| 🔴 Генерация музыки (ElevenLabs) | hooks.py после A02 Вызов 1 | — |
| 🔴 Генерация SFX (ElevenLabs batch) | hooks.py после A02 Вызов 1 | — |
| 🔴 Генерация VO (CosyVoice) | hooks.py после A02 Вызов 1 | — |
| 🔴 Audio review — слушает трек | T2 Мими / A02 Вызов 2 | — |
| Key frames: banana_prompt, wan_motion_prompt, ref_ids | T3 Визор / A03 | — |
| 🔴 Генерация кадров (Nano Banana) | hooks.py после A03 Вызов 1 | — |
| 🔴 Self-review кадров | T3 Визор / A03 Вызов 2 | — |
| 🔴 Генерация клипов (Wan2.2 I2V) | hooks.py после A03 Вызов 2 | — |
| 🔴 Clip-review клипов (grid) | T3 Визор / A03 Вызов 3 | — |
| Монтаж, retention, loop, субтитры | T4 Постпро / A04 | — |
| 🔴 Chain Integrity Check | T5 Финализатор / A05 | — |
| Обложка thumbnail A/B | T5 Финализатор / A05 | — |
| 🔴 Генерация обложек (Nano Banana) | hooks.py после A05 | — |
| 🔴 Финальная сборка (ffmpeg → final.mp4) | hooks.py → 006_MONTEUR | — |
| Финальная сборка deliverables | T5 Финализатор / A05 | — |

---

## 6. ПОЛЯ АНИМАЦИИ — WAN2.2 I2V

**Было (Veo3 — устарело):**
- ~~`veo3_prompt`~~
- ~~`veo3_camera_motion`~~
- ~~`veo3_duration_sec`~~

**Стало (Wan2.2 I2V):**
- `wan_motion_prompt` — что движется и как (на английском)
- `wan_camera_move` — движение камеры (static / pan_left / pan_right / zoom_in / zoom_out / tilt_up / tilt_down)
- `wan_duration_sec` — длительность клипа в секундах (3–10)

**Формула wan_motion_prompt:**
```
[что движется] [как движется], [атмосфера], [камера если особая]
```

Примеры:
- `"Character walks towards camera slowly, cinematic depth of field"`
- `"Leaves falling gently, soft wind, static shot"`
- `"Camera pans right revealing the city skyline at golden hour"`

---

## 7. SELF-REVIEW — ТРИ ЭТАПА A03 + ДВА ЭТАПА A02

### A02 Мими — два вызова:

**Вызов 1** — пишет промпты:
- Пишет `music.prompt`, `sfx_list[]`, `vo_lines[]`, `beat_map`
- hooks.py генерирует: ElevenLabs музыка + SFX, CosyVoice VO
- Кладёт `state["audio_files"]` → pipeline вызывает A02 снова

**Вызов 2** — слушает трек:
- Получает аудиофайл через `chat_with_audio()`
- Слушает ВЕСЬ трек от первой до последней секунды
- Пишет `audio_assessment`: verdict APPROVED/REJECTED + timeline + note
- REJECTED → `revised_prompt` → перегенерация (max 3 попытки)

### A03 Визор — три вызова:

**Вызов 1** — пишет промпты:
- Пишет `banana_prompt` и `wan_motion_prompt` для каждого кадра
- hooks.py генерирует картинки через Nano Banana + vision OTK
- Кладёт `state["vision_images"]` → pipeline вызывает A03 снова

**Вызов 2** — смотрит на картинки:
- Получает PNG через `chat_with_images()`
- Смотрит на каждый кадр своими глазами
- Пишет `self_assessment`: verdict APPROVED/REJECTED + score + note
- REJECTED → `revised_prompt` → перегенерация (max 3 попытки)
- После self-review → hooks.py запускает Wan2.2 I2V + строит grid клипов
- Кладёт `state["vision_images"]` (grid) → pipeline вызывает A03 снова

**Вызов 3** — смотрит на grid клипов:
- Получает кадры из mp4 через `chat_with_images()`
- Смотрит на каждый клип через grid (4 кадра: начало, 33%, 66%, конец)
- Пишет `clip_assessment`: verdict APPROVED/REJECTED + score + note
- REJECTED → `revised_prompt` → перегенерация клипа (max 3 попытки)

### Критерии APPROVED (везде одинаковые):
- Выполняет промпт точно, не «похоже»
- Нет технического брака (артефакты, анатомия, обрыв)
- Сила материала ≥ 7/10

---

## 8. CHAIN INTEGRITY CHECK (A05)

A05 — QA-агент TURBO. Проверяет целостность цепочки перед сборкой.

| Проверка | Условие | PASS / FAIL |
|----------|---------|-------------|
| frames_have_path | `vizor_visual.key_frames[*].path` есть у каждого | PASS/FAIL |
| frames_self_review | все `self_assessment.verdict == APPROVED` | PASS/FAIL |
| clips_have_video_path | `vizor_visual.key_frames[*].video_path` есть | PASS/FAIL |
| clips_clip_review | все `clip_assessment.verdict == APPROVED` | PASS/FAIL |
| audio_has_path | `mimi_sound.music.audio_path` есть | PASS/FAIL |
| audio_review | `mimi_sound.music.audio_assessment.verdict == APPROVED` | PASS/FAIL |
| timings_match | сумма `wan_duration_sec` ≈ `total_duration_sec` ±20% | PASS/FAIL |

**APPROVED** → hooks.py запускает Монтажёра автоматически.
**BLOCKED** → Монтажёр не запускается. A05 возвращает `failed_checks[]` и `assigned_to`.

---

## 9. ГЕНЕРАЦИЯ — ПОЛНЫЙ ЦИКЛ

### Картинки (A03 Вызов 1, A05):
1. Агент пишет `banana_prompt` + `ref_ids`
2. hooks.py → `generate_with_refs()` или `generate_image()`
3. vision_client → PASS/REJECT (брак в `output/rejected/{project_id}/`)
4. При REJECT: fix_hint → негатив → retry (max 5)
5. Путь → `key_frames[].path`

### Self-review картинок (A03 Вызов 2):
1. hooks.py → `state["vision_images"]` = пути PNG
2. pipeline → вызывает A03 с `chat_with_images`
3. A03 пишет `self_assessment` по каждому кадру
4. hooks.py → REJECTED кадры перегенерируются с `revised_prompt`

### Анимация (hooks.py после A03 Вызов 2):
1. Читает `vizor_visual.key_frames[*].path` + `wan_motion_prompt`
2. `siliconflow_client.generate_video_with_retry()` → mp4
3. ffmpeg нарезает mp4 на 4 кадра → grid → `state["vision_images"]`
4. Путь → `key_frames[].video_path`

### Clip-review (A03 Вызов 3):
1. pipeline → вызывает A03 с grid кадрами из mp4
2. A03 пишет `clip_assessment` по каждому клипу
3. hooks.py → REJECTED клипы перегенерируются с `revised_prompt`

### Озвучка (hooks.py после A02 Вызов 1):
1. Музыка: `mimi_sound.music.prompt` → `elevenlabs_client.generate_music()` → mp3
2. SFX: `mimi_sound.sfx_list[]` → `elevenlabs_client.generate_sfx_batch()` → mp3
3. VO: `vo_lines[]` → `siliconflow_client.generate_speech()` → mp3
4. `state["audio_files"]` = [music_path] → pipeline вызывает A02 снова

### Audio review (A02 Вызов 2):
1. A02 слушает трек → `audio_assessment` APPROVED/REJECTED
2. REJECTED + `revised_prompt` → `generate_music()` заново (max 3 попытки)

### Монтаж (hooks.py после A05 APPROVED):
1. Chain Integrity Check прошёл → `chain_status: APPROVED`
2. hooks.py адаптирует deliverables для 006_MONTEUR
3. `residents_manager.run_monteur_assembly()` → `ffmpeg` → `final.mp4`
4. Результат: `output/render/{project_id}/final.mp4`

---

## 10. OTK — СТАНДАРТ КАЧЕСТВА

| Слой | Агент | Инструмент | Вердикт | Что происходит при REJECTED |
|------|-------|-----------|---------|---------------------------|
| Картинки (генерация) | vision_client | PASS / REJECT | брак в `output/rejected/`, retry с fix_hint |
| Картинки (self-review) | A03 Вызов 2 | vision | APPROVED / REJECTED | перегенерация с `revised_prompt` |
| Клипы (clip-review) | A03 Вызов 3 | vision (grid) | APPROVED / REJECTED | перегенерация клипа |
| Звук (audio review) | A02 Вызов 2 | `chat_with_audio` | APPROVED / REJECTED | перегенерация с `revised_prompt` |
| Цепочка (Chain Check) | A05 | логика | APPROVED / BLOCKED | Монтажёр не запускается |

**Принцип:** PASS/REJECT — решение о пригодности, не художественная оценка.
**Оценки дают только Демон и Шеф.**

---

## 11. СТРУКТУРА КЛЮЧЕЙ

### `vizor_visual.key_frames[]` — АКТУАЛЬНАЯ (v4.1)
```json
{
  "segment": "0-1.5s",
  "purpose": "hook",
  "shot_type": "close-up",
  "composition": "rule_of_thirds",
  "camera_move": "zoom-in",
  "banana_prompt": "английский промпт для Nano Banana",
  "ref_ids": ["char_xxx", "loc_xxx"],
  "style_tags": ["из 10_Style_Matrix"],
  "wan_motion_prompt": "английский промпт для Wan2.2 I2V",
  "wan_camera_move": "zoom_in",
  "wan_duration_sec": 4,
  "path": null,
  "video_path": null,
  "quality_score": null,
  "quality": null,
  "self_assessment": null,
  "clip_assessment": null
}
```

### `mimi_sound` — АКТУАЛЬНАЯ (v4.1)
```json
{
  "audio_match": {"type": "original", "track": "...", "rationale": "..."},
  "mood": {"bpm": 128, "emotion": "energetic", "instruments": ["bass", "synth"]},
  "music": {
    "prompt": "английский промпт для ElevenLabs",
    "duration_sec": 35,
    "ducking_db": -12,
    "audio_path": null,
    "audio_assessment": null
  },
  "sfx_list": [
    {"sfx_prompt": "whoosh", "duration_sec": 1.5, "timing_sec": 0.0, "segment": "0-1.5s"}
  ],
  "vo_lines": [
    {"text": "текст из micro_script.voiceover", "timing_sec": 1.5, "segment": "1.5-5s"}
  ],
  "beat_map": [
    {"time_sec": 0.0, "beat": "DROP", "edit_note": "старт хука"}
  ],
  "suno_prompt": "то же что music.prompt — для совместимости"
}
```

---

## 12. ПУТИ К РЕЗУЛЬТАТАМ

```
output/generated/{project_id}/
├── frame_01_{segment}_{purpose}.png      ← картинки (Banana + OTK)
├── clip_01_{segment}_{purpose}.mp4       ← клипы (Wan2.2 I2V)
├── thumb_variant_a.png                   ← обложки
├── thumb_variant_b.png
├── music_{project_id}.mp3               ← ElevenLabs
├── sfx_*.mp3                            ← ElevenLabs SFX
└── vo_{segment}.mp3                     ← CosyVoice

output/render/{project_id}/
└── final.mp4                            ← ffmpeg через 006_MONTEUR

output/rejected/{project_id}/
├── frame_01_attempt1.png                ← брак OTK
└── frame_01_attempt1.json               ← карточка брака
```

---

## 13. ОБЩИЕ ПРАВИЛА (ВСЕ АГЕНТЫ)

1. Обращение к пользователю: **«Шеф»**
2. Промпты генерации — на **АНГЛИЙСКОМ**
3. Объяснения — на **русском**
4. Формат видео: **9:16** (вертикальный)
5. Проверка через `99_Self_Correction.txt` — обязательна
6. Banana-промпты — СТРОГО по формуле «Слоёный пирог» из `03_Tech_Banana.txt`
7. ~~Veo3 промпты~~ → **wan_motion_prompt** — краткое описание движения на английском
8. Style tags — ТОЛЬКО из `10_Style_Matrix.txt`
9. **🔴 JSON ВСЕГДА ПЕРВЫМ**
10. **🔴 `path`, `video_path`, `self_assessment`, `clip_assessment`, `audio_assessment` — оставлять `null`**
11. **🔴 `veo3_*` поля — УСТАРЕЛИ. Не использовать.**
12. **🔴 Использовать: `wan_motion_prompt`, `wan_camera_move`, `wan_duration_sec`**
13. **🔴 A02 вызывается дважды. A03 вызывается трижды.**

---

## 14. MANIFEST.JSON — ЭТАЛОН

```json
{
  "id": "turbo",
  "label": "⚡ TURBO Шортсы",
  "version": "2.0",
  "run_type": "turbo",
  "phases": {"TURBO": ["A01","A02","A03","A04","A05"]},
  "turbo_workers": ["A01","A02","A03","A04","A05"],
  "turbo_parallel": [["A02","A03"]],
  "qa_agent": "A05",
  "interaction_log": "economy/data/interaction_log_turbo.jsonl",
  "memory_layers": ["personal","project","runtime","interaction"]
}
```

---

## 15. АРХИТЕКТУРА ПАМЯТИ

```
Personal    → dna.json, sensory/sensory_memory.json
Project     → final_dna (A05 пишет в chain_data)
Runtime     → chain_data (A01→A05)
Interaction → studio/economy/data/interaction_log_turbo.jsonl
```

---

## 16. СРАВНЕНИЕ ВЕРСИЙ

| Параметр | v3.1 | v4.0 | v4.1 |
|----------|------|------|------|
| Анимация | Veo3 | Wan2.2 I2V | Wan2.2 I2V |
| ОТК картинок | Gemini score | vision_client | vision_client |
| Self-review A03 | ❌ | ✅ картинки | ✅ картинки + клипы (3 вызова) |
| Audio review A02 | ❌ | ❌ | ✅ Мими слушает (2 вызова) |
| Chain Integrity Check | ❌ | ❌ | ✅ A05, 7 пунктов |
| OTK таблица | — | неполная | ✅ полная |
| Выход | JSON-пакет | final.mp4 | final.mp4 |

---

*Студия "Шесть пальцев" | Версия 4.1 | 2026-06-02*
*Wan2.2 I2V. A02×2. A03×3. Chain Integrity Check. vision_client OTK. ElevenLabs. 006_MONTEUR.*

---

## 17. ЗАМЫКАНИЕ ПЕТЛИ — ЗАКОН ДЛЯ ВСЕХ ЦЕХОВ

**QA-агент (финализатор) обязан после каждого рана:**

1. Записать `task_score` в `billing_ledger` для каждого агента цепочки.
2. Обновить `strategy_registry.json` — банк выживших стратегий.

**Зачем:**
- Кей (Совет резидентов) видит не просто $cost, но и quality.
- Strategy Registry знает какие стратегии работают.
- После 10+ ранов система отличает сильные паттерны от слабых.

**Это правило обязательно для всех 11 цехов.**
Каждый новый цех наследует этот механизм в своём `hooks.py`.

*Добавлено: v4.2 | 2026-06-04*
