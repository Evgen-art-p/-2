# 📜 VIDEO_LONG PIPELINE v4.4 — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Полный конвейер длинного видео

**Версия:** 4.4
**Дата:** 2026-05-30
**Режимы:** BIBLE (создание вселенной) + EPISODE (экранизация)
**Агентов:** 12
**ХАРД-СТОП:** После Кати (04) + Виктор (резидент-критик)
**Память:** Четыре слоя (Personal / Project / Runtime / Interaction)

---

## ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.4

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Монтажёр реализован** | `006_MONTEUR` — резидент, `studio/assembly/monteur.py`, автозапуск после Боба через хук |
| 2 | **Хук A10 реализован** | `_sam_generate_audio()` в hooks.py — ElevenLabs music + SFX batch + CosyVoice VO |
| 3 | **`sam_sound` — реальные аудио пути** | `music.audio_path`, `sfx_list[*].sfx_path`, `vo_lines[*].vo_path` добавляет хук A10 |
| 4 | **`felix_vfx.video_clips` — полная структура** | `video_path`, `clip_assessment`, `scene_id` — хук A08 пишет реальные mp4 |
| 5 | **`deliverables.video_clips`** | Боб собирает `video_clips` (не `veo3_prompts`) с `video_path` |
| 6 | **Мастерская Assembly** | Новый UI: заказы / верстак / мастер. Чат с Монтажёром по кнопке |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
РЕЖИМ BIBLE (создание вселенной — один раз):
  PRE-PROD:
    01 Адам Арка       🎭  — создание мира, персонажей, визуального стиля, плана сезона
    → 02 Зак Зум       🔎  — структура сезона, ритм, эмоциональная карта
    → 03 Лео Логлайн   ✍️  — посерийный план сцен
    → 04 Катя Кат      ✂️  — QA Библии (контентный ревизор)

    🛑 ХАРД-СТОП — Виктор (victor_critique) + Шеф утверждает
    ▶️ CONTINUE → Библия сохранена в history_dna

РЕЖИМ EPISODE (экранизация — N раз):
  PRE-PROD:
    01 Адам Арка       🎭  — контекст серии + подбор ассетов из Bible
    → 02 Зак Зум       🔎  — хук серии + retention
    → 03 Лео Логлайн   ✍️  — сценарий серии
    → 04 Катя Кат      ✂️  — QA сценария + проверка соответствия Bible

    🛑 ХАРД-СТОП — Виктор + Шеф утверждает сценарий
    ▶️ CONTINUE

  PROD:
    → 05 Лукас Ленз    🎥  — раскадровка + shots[] + motion_intent
                            * model_decision (Flash/Pro/Sonnet)
    → 06 Ева Эпик      🎨  — промпты PNG (Nano Banana 2, 16:9)
                            * ЭТАП 1: banana_prompt + model_decision
                            * хук: fal.ai → PNG + ОТК vision_client
                            * ЭТАП 2: self_assessment (PNG) → APPROVED/REJECTED
    → 07 Тим Титр      🔤  — типографика
                            * model_decision
    → 08 Феликс FX     ✨  — motion_prompt (Wan2.2 I2V)
                            * ЭТАП 1: motion_prompt + model_decision
                            * хук: Wan2.2 → mp4 → grid (матрица кадров) + ОТК
                            * ЭТАП 2: clip_assessment (grid) → APPROVED/REJECTED
                            * логирует compatibility_snapshot → interaction_log
                            * пишет video_path в video_clips[]

  POST-PROD:
    → 09 Алекс Экшн    🏃  — моушн-анимация поверх клипов
                            * model_decision
    → 10 Сэм Стерео    🎧  — звуковой дизайн
                            * ЭТАП 1: music/sfx/vo промпты + model_decision
                            * хук: ElevenLabs → music.mp3, sfx/*.mp3
                            *       CosyVoice → vo/*.mp3
                            * ЭТАП 2: audio_assessment (полный arc) → APPROVED/REJECTED
                            * пишет audio_path, sfx_path, vo_path в sam_sound
                            * mutations → Лавочка Артефактов
    → 11 Трейси Тизер  📱  — SMM + обложки A/B
                            * ЭТАП 1: banana_prompt variant_a/b + model_decision
                            * хук: fal.ai → PNG обложки
                            * ЭТАП 2: thumbnail_assessment (PNG) → APPROVED/REJECTED
    → 12 Боб Блокбастер 💰 — Chain Integrity Check + финальная сборка [QA-агент]
                            * НЕ оценивает для Министерства — это зона Демона
                            * chain_status: APPROVED/FAILED
                            * собирает deliverables (video_clips с video_path, PNG, аудио)
                            * закрывает петлю памяти (history_dna, client_relationship)
                            * append-only лог в Министерство (факт транзакции)
                            * outcome_signal = null → Демон заполнит после публикации

    ✅ МОНТАЖЁР (006_MONTEUR) — резидент на все цеха видео
                            * запускается автоматически хуком после Боба (APPROVED)
                            * читает deliverables.video_clips[*].video_path
                            * читает deliverables.audio (music_path, sfx, vo)
                            * ffmpeg concat клипов → raw_video.mp4
                            * ffmpeg amix аудио (VO 0dB / SFX -6dB / Music -12dB)
                            * финальный mp4 → output/render/{project_id}/final.mp4
                            * пишет assembly_manifest.json
                            * живёт в Мастерской (/assembly)
```

---

## 2. ФИЗИКА ЭКОНОМИКИ — БОБ vs ДЕМОН

**Это фундаментальный закон Студии. Нарушение = пластик.**

```
Боб (A12) — внутренний аудит:
  → Chain Integrity Check (файлы на месте? ключи целые? тайминги сошлись?)
  → chain_status: APPROVED / FAILED
  → Если FAILED — возвращает цепочку нужному агенту
  → Если APPROVED — пакует deliverables, закрывает петлю памяти
  → Фиксирует факт транзакции в Министерстве (append-only)
  → outcome_signal = null (ролик ещё не опубликован)
  → Монтажёр запускается автоматически хуком

Монтажёр (006_MONTEUR) — финальная сборка:
  → Получает deliverables от Боба через хук
  → ffmpeg: склейка клипов + микш аудио → final.mp4
  → Пишет в grondheim_memory и ministry
  → НЕ оценивает контент — только собирает

Демон (metrics_daemon.py) — внешний мир:
  → Активируется после публикации
  → Собирает реальные метрики: просмотры, удержание, лайки
  → Формирует feedback_scores → _sync_feedback_scores_to_dna()
```

---

## 3. SELF-REVIEW — СИММЕТРИЯ АРХИТЕКТУРЫ

| Агент | Медиа | Инструмент | Принцип |
|-------|-------|-----------|---------|
| Ева (06) | PNG кадр | vision → `self_assessment` | Мурашки есть? Анатомия чистая? |
| Феликс (08) | grid mp4 | vision → `clip_assessment` | Grid слева направо, сверху вниз |
| Сэм (10) | полный аудио arc | `chat_with_audio()` → `audio_assessment` | Посекундная разметка. Фальшь = REJECTED |
| Трейси (11) | PNG обложки | vision → `thumbnail_assessment` | Скролл остановит? |

**Принцип: никто не сдаёт вслепую. Максимум 3 попытки. После трёх — `best_of_3`.**

---

## 4. АРХИТЕКТУРА ПАМЯТИ — ЧЕТЫРЕ СЛОЯ

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal Memory | `grondheim_memory.py` + `dna.json` | Постоянно | Каждый агент |
| Project Memory | `history_dna` | Сезон | Боб (12) |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer | `interaction_log_video_long.jsonl` | Накопительно | Феликс (08) + Боб (12) |

---

## 5. MANIFEST.JSON — ЭТАЛОН

```json
{
  "id": "video_long",
  "label": "🎥 Видео Long",
  "version": "2.0",
  "phases": {
    "PRE-PROD": ["A01","A02","A03","A04"],
    "PROD":     ["A05","A06","A07","A08"],
    "POST-PROD":["A09","A10","A11","A12"]
  },
  "checkpoint_after": [],
  "conflict_mode": "divergent",
  "qa_agent": "A12",
  "interaction_log": "economy/data/interaction_log_video_long.jsonl",
  "memory_layers": ["personal","project","runtime","interaction"],
  "hard_stop": {
    "after_agent": "A04",
    "residents": ["victor"]
  }
}
```

---

## 6. ПРОТОКОЛ chain_data (CHAIN_CONTRACT v1.2)

| Агент | Пишет (EPISODE) | Читает |
|-------|----------------|--------|
| A01 Адам | `adam_episode` | `master_brief`, `history_dna` |
| A02 Зак | `zack_hook` | `adam_episode`, `history_dna` |
| A03 Лео | `leo_script` | `adam_episode`, `zack_hook`, `history_dna` |
| A04 Катя | `katya_review` + `katya_verdict` | всё до A04 |
| A05 Лукас | `lucas_storyboard` | `leo_script`, `history_dna`, `master_brief` |
| A06 Ева | `eva_visuals` | `lucas_storyboard`, `history_dna`, `master_brief` |
| A07 Тим | `tim_typography` | `eva_visuals`, `lucas_storyboard` |
| A08 Феликс | `felix_vfx` | `eva_visuals`, `lucas_storyboard`, `history_dna` |
| A09 Алекс | `alex_motion` | `felix_vfx`, `eva_visuals`, `leo_script` |
| A10 Сэм | `sam_sound` | `leo_script`, `alex_motion`, `history_dna` |
| A11 Трейси | `tracy_smm` | `leo_script`, `eva_visuals`, `history_dna` |
| A12 Боб | `bob_marketing` + `final_dna` | ВСЁ |

**Сквозные ключи** (`{{inherit}}`): `master_brief`, `history_dna`, `mode`

---

## 7. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин | Физический закон |
|------|--------|-----------------|
| Chain Integrity | Боб (12) | Проверяет структуру, не контент |
| Оценка метрик внешнего мира | Демон (`metrics_daemon.py`) | После публикации, не раньше |
| `outcome_signal` заполнение | Демон | Боб оставляет null |
| Self-review PNG кадров | Ева (06) | `self_assessment` в каждом frame |
| Self-review mp4 клипов (grid) | Феликс (08) | `clip_assessment` + `grid_observations` |
| Self-review аудио (полный arc) | Сэм (10) | `audio_assessment` + `timeline` |
| Self-review PNG обложек | Трейси (11) | `thumbnail_assessment` чек-лист |
| Финальная склейка в mp4 | Монтажёр `006_MONTEUR` | ffmpeg: клипы + аудио → final.mp4 |
| `history_dna` | Боб (12) | Единственный источник |
| `client_relationship` | Боб (12) | Единственный источник |
| `model_decision` | Каждый агент A05–A12 | Из DNA, не из глобального конфига |
| `interaction_log` | Феликс (08) пишет, Боб (12) закрывает | append-only |
| `assembly_manifest.json` | Монтажёр | Пишет после каждой сборки |

---

## 8. ОБЩИЕ ПРАВИЛА

| # | Правило |
|---|---------|
| 01 | Обращение: «Шеф» |
| 02 | Промпты генерации — на **АНГЛИЙСКОМ** |
| 03 | Спецификации и объяснения — на **русском** |
| 04 | Формат видео: **16:9** |
| 05 | KB: `00_Constructor.txt` и `99_Self_Correction.txt` — у всех |
| 06 | Каждый агент проверяет себя через `99_Self_Correction.txt` |
| 07 | `history_dna` — закон. В режиме EPISODE не перепридумываем клиента, арку, стиль |
| 08 | ХАРД-СТОП — один. После Кати. Без ▶️ CONTINUE PROD не запускается |
| 09 | Виктор — резидент #5. Активируется через manifest.json |
| 10 | `interaction_log` — append-only. Не редактируется задним числом |
| 11 | `motion_intent` — рекомендация, не директива. Феликс логирует отступление в `friction_note` |
| 12 | `client_relationship` обновляет только Боб через `dna.json` |
| 13 | **`qa_agent` = A12 (Боб). Последний в цехе. A04 — контентный ревизор, не путать** |
| 14 | **Боб НЕ оценивает для Министерства. Это зона Демона** |
| 15 | **`outcome_signal` всегда null от Боба. Демон заполнит после публикации** |
| 16 | **`deliverables.video_clips[*].video_path` — реальные mp4, не промпты** |
| 17 | **Self-review обязателен у Евы, Феликса, Сэма, Трейси. Никто не сдаёт вслепую** |
| 18 | **`model_decision` у каждого агента A05–A12. Flash по умолчанию** |
| 19 | **Монтажёр `006_MONTEUR` — резидент, один на все цеха видео. Запускается автоматически** |
| 20 | **`sam_sound.music.audio_path` — реальный mp3 после хука A10. Боб читает именно его** |
| 21 | **`felix_vfx.video_clips[*].video_path` — реальный mp4 после хука A08** |

---

## 9. ЧЕКЛИСТ ПОСЛЕ ПЕРВОГО РАНА

```
1.  interaction_log_video_long.jsonl создан?
2.  Боб проставил chain_status: APPROVED?
3.  history_dna обновлён — narrative_entry, client_relationship?
4.  outcome_signal = null (Демон заполнит)?
5.  deliverables.video_clips содержат video_path (mp4)?
6.  deliverables.key_frames содержат path (PNG)?
7.  Все self_assessment.verdict = APPROVED у Евы, Феликса, Сэма, Трейси?
8.  CulturalFieldTracker записал поле video_long?
9.  client_relationship обновился в dna.json Боба?
10. victor_critique появился в chain_data?
11. Монтажёр запустился автоматически? → output/render/{project_id}/final.mp4?
12. assembly_manifest.json создан с status DONE/PARTIAL?
```

---

*Студия "Шесть пальцев" | Версия 4.4 | 2026-05-30*
*Монтажёр 006_MONTEUR реализован. Хук A10 реализован. Цепочка замкнута.*
