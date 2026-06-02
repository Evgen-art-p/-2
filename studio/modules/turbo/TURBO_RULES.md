# 📜 TURBO PIPELINE — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Быстрый конвейер шортсов

**Версия:** 4.0
**Дата:** 2026-06-02
**Режим:** TURBO (5 агентов)
**Модель изображений:** Nano Banana 2 (fal-ai/nano-banana-2)
**Модель анимации:** Wan2.2 I2V (SiliconFlow)
**Озвучка:** ElevenLabs (музыка + SFX) + CosyVoice (VO)
**Монтаж:** ffmpeg через 006_MONTEUR

---

## ⚡ ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.0

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Veo3 → Wan2.2 I2V** | Veo3 недоступен. Wan2.2 через SiliconFlow |
| 2 | **Поля анимации переименованы** | `veo3_prompt` → `wan_motion_prompt`, `veo3_camera_motion` → `wan_camera_move`, `veo3_duration_sec` → `wan_duration_sec` |
| 3 | **A02 Мими — реальная озвучка** | hooks.py вызывает ElevenLabs (музыка + SFX) и CosyVoice (VO) |
| 4 | **A03 — self-review (два этапа)** | Агент смотрит на свои кадры и пишет APPROVED/REJECTED. Не сдаёт вслепую |
| 5 | **ОТК через vision_client** | PASS/REJECT по стандарту video_long. Брак → `output/rejected/` |
| 6 | **Монтажёр после A05** | hooks.py запускает 006_MONTEUR → ffmpeg → `final.mp4` |
| 7 | **Ministry score учитывает клипы и аудио** | Более честная оценка рана |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
A01 / T1 Стелла Стратег (🧠) — стратегия + сценарий + SEO + подбор ассетов
        │
        ├──→ A02 / T2 Мими Мем (🎵) — звук (промпты)     ⎤
        │         hooks.py → ElevenLabs музыка + SFX      ⎥ ПАРАЛЛЕЛЬНО
        │         hooks.py → CosyVoice VO (если нужен)    ⎥
        │                                                   ⎥
        └──→ A03 / T3 Визор (🎬) — визуал (промпты)       ⎦
                    hooks.py → Nano Banana картинки
                    A03 Этап 2 → self-review (смотрит сам)
                    hooks.py → Wan2.2 I2V → mp4 клипы
                    │
                    └──────────────────┐
                                       ▼
              A04 / T4 Постпро (✂️) — монтаж + retention + субтитры
                                       │
                                       ▼
              A05 / T5 Финализатор (🏁) — обложки + deliverables [qa_agent]
                    hooks.py → Nano Banana обложки
                    hooks.py → 006_MONTEUR → ffmpeg → final.mp4
```

---

## 2. ПРОТОКОЛ chain_data

| Агент | worker_id | Получает | Добавляет |
|-------|-----------|----------|-----------|
| T1 Стелла | A01 | master_brief | stella_strategy |
| T2 Мими | A02 | master_brief, stella_strategy | mimi_sound (+ audio paths от hooks) |
| T3 Визор | A03 | master_brief, stella_strategy | vizor_visual (+ paths от hooks) |
| T4 Постпро | A04 | master_brief, stella_strategy, mimi_sound, vizor_visual | postpro |
| T5 Финализатор | A05 | ВСЁ | thumbnail (+ paths), t5_deliverables, final_dna |

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
| Звук: suno_prompt, sfx_map, beat_map, voiceover | T2 Мими / A02 | — |
| 🔴 Генерация музыки (ElevenLabs) | hooks.py после A02 | — |
| 🔴 Генерация SFX (ElevenLabs batch) | hooks.py после A02 | — |
| 🔴 Генерация VO (CosyVoice) | hooks.py после A02 | — |
| Key frames: banana_prompt, wan_motion_prompt, ref_ids | T3 Визор / A03 | — |
| 🔴 Генерация кадров (Nano Banana) | hooks.py после A03 Этап 1 | — |
| 🔴 Self-review кадров | T3 Визор / A03 Этап 2 | — |
| 🔴 Генерация клипов (Wan2.2 I2V) | hooks.py после A03 Этап 2 | — |
| Монтаж, retention, loop, субтитры | T4 Постпро / A04 | — |
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

## 7. SELF-REVIEW A03 ВИЗОРА (два этапа)

### Этап 1 — до генерации:
- Визор пишет `banana_prompt` и `wan_motion_prompt` для каждого кадра
- hooks.py генерирует картинки через Nano Banana
- vision_client проверяет: PASS/REJECT → брак в `output/rejected/`

### Этап 2 — после генерации:
- hooks.py кладёт пути картинок в `state["vision_images"]`
- pipeline вызывает A03 повторно с картинками в контексте
- Визор смотрит на каждый кадр своими глазами
- Пишет `self_assessment` для каждого: APPROVED/REJECTED + `revised_prompt`
- hooks.py применяет: REJECTED → перегенерация с новым промптом (max 3 попытки)
- Только после self-review → анимация Wan2.2 I2V

### Критерии APPROVED:
- Анатомия чистая
- Промпт выполнен
- Сила кадра ≥ 7/10
- Нет артефактов

---

## 8. ГЕНЕРАЦИЯ — ПОЛНЫЙ ЦИКЛ

### Картинки (A03 Этап 1, A05):
1. Агент пишет `banana_prompt` + `ref_ids`
2. hooks.py → `generate_with_refs()` или `generate_image()`
3. vision_client → PASS/REJECT (брак в `output/rejected/{project_id}/`)
4. При REJECT: fix_hint → негатив → retry (max 5)
5. Путь → `key_frames[].path`

### Self-review (A03 Этап 2):
1. hooks.py → `state["vision_images"]` = пути картинок
2. pipeline → вызывает A03 с `chat_with_images`
3. A03 пишет `self_assessment` по каждому кадру
4. hooks.py → REJECTED кадры перегенерируются с `revised_prompt`

### Анимация (hooks.py после A03 Этап 2):
1. Читает `vizor_visual.key_frames[*].path` (картинка)
2. Читает `vizor_visual.key_frames[*].wan_motion_prompt`
3. `siliconflow_client.generate_video_with_retry()` → mp4
4. Путь → `key_frames[].video_path`

### Озвучка (hooks.py после A02):
1. Музыка: `mimi_sound.suno_prompt` → `elevenlabs_client.generate_music()` → mp3
2. SFX: `mimi_sound.sfx_map[]` → `elevenlabs_client.generate_sfx_batch()` → mp3
3. VO: `stella_strategy.script.micro_script[].voiceover` → `siliconflow_client.generate_speech()` → mp3

### Монтаж (hooks.py после A05):
1. Читает `t5_deliverables` + клипы из `vizor_visual`
2. Адаптирует в формат 006_MONTEUR
3. `residents_manager.run_monteur_assembly()` → `ffmpeg` → `final.mp4`
4. Результат: `output/render/{project_id}/final.mp4`

---

## 9. OTK — СТАНДАРТ КАЧЕСТВА

| Слой | Инструмент | Вердикт | Брак |
|------|-----------|---------|------|
| Картинки | vision_client (Gemini) | PASS / REJECT | output/rejected/ |
| Self-review | A03 сам | APPROVED / REJECTED | revised_prompt |
| Клипы | — | — | — |
| Звук | — | — | — |

---

## 10. СТРУКТУРА КЛЮЧЕЙ

### `vizor_visual.key_frames[]` — АКТУАЛЬНАЯ (v4.0)
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
  "self_assessment": null
}
```

### `mimi_sound` — АКТУАЛЬНАЯ (v4.0)
```json
{
  "audio_match": {"type": "original", "track": "...", "rationale": "..."},
  "mood": {"bpm": 128, "emotion": "energetic", "instruments": ["bass", "synth"]},
  "sfx_map": [
    {"segment": "0-1.5s", "sfx": "whoosh", "purpose": "attract attention"}
  ],
  "beat_map": [
    {"time_sec": 0.0, "beat": "DROP", "edit_note": "hook start"}
  ],
  "voiceover": {"needed": true, "tone": "energetic", "pace": "fast"},
  "suno_prompt": "английский промпт для ElevenLabs",
  "music_path": null,
  "sfx_list": [],
  "vo_lines": []
}
```

---

## 11. ПУТИ К РЕЗУЛЬТАТАМ

```
output/generated/{project_id}/
├── frame_01_{segment}_{purpose}.png      ← картинки
├── frame_02_{segment}_{purpose}.png
├── clip_01_{segment}_{purpose}.mp4       ← клипы Wan2.2
├── clip_02_{segment}_{purpose}.mp4
├── thumb_variant_a.png                   ← обложки
├── thumb_variant_b.png
├── music_{project_id}.mp3               ← озвучка
└── vo_{segment}.mp3

output/render/{project_id}/
└── final.mp4                            ← финальный ролик

output/rejected/{project_id}/
├── frame_01_attempt1.png                ← брак
└── frame_01_attempt1.json               ← карточка брака
```

---

## 12. ОБЩИЕ ПРАВИЛА (ВСЕ АГЕНТЫ)

1. Обращение к пользователю: **«Шеф»**
2. Промпты генерации — на **АНГЛИЙСКОМ**
3. Объяснения — на **русском**
4. Формат видео: **9:16** (вертикальный)
5. Проверка через `99_Self_Correction.txt` — обязательна
6. Banana-промпты — СТРОГО по формуле «Слоёный пирог» из `03_Tech_Banana.txt`
7. ~~Veo3 промпты~~ → **wan_motion_prompt** — краткое описание движения на английском
8. Style tags — ТОЛЬКО из `10_Style_Matrix.txt`
9. **🔴 JSON ВСЕГДА ПЕРВЫМ**
10. **🔴 `path`, `video_path` — оставлять `null`**
11. **🔴 `veo3_*` поля — УСТАРЕЛИ. Не использовать.**
12. **🔴 Использовать: `wan_motion_prompt`, `wan_camera_move`, `wan_duration_sec`**

---

## 13. MANIFEST.JSON — ЭТАЛОН

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

## 14. АРХИТЕКТУРА ПАМЯТИ

```
Personal    → dna.json, sensory/sensory_memory.json
              resonance/emotional_weights.json
              resonance/event_log.json
Project     → final_dna (A05 пишет в chain_data)
Runtime     → chain_data (A01→A05)
Interaction → studio/economy/data/interaction_log_turbo.jsonl
```

---

## 15. СРАВНЕНИЕ ВЕРСИЙ

| Параметр | v3.1 | v4.0 |
|----------|------|------|
| Анимация | Veo3 (недоступен) | Wan2.2 I2V (SiliconFlow) |
| Поля анимации | veo3_prompt / veo3_camera_motion | wan_motion_prompt / wan_camera_move |
| ОТК картинок | Gemini score 1-10 | vision_client PASS/REJECT |
| Self-review | ❌ | ✅ A03 смотрит сам |
| Озвучка | Только промпты | ElevenLabs + CosyVoice реальные файлы |
| Монтаж | ❌ | ✅ 006_MONTEUR → final.mp4 |
| Выход | JSON-пакет | final.mp4 |

---

*Студия "Шесть пальцев" | Версия 4.0 | 2026-06-02*
*Wan2.2 I2V. Self-review. vision_client OTK. ElevenLabs. 006_MONTEUR.*
