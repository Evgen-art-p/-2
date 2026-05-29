# 📜 VIDEO_LONG PIPELINE v4.3 — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Полный конвейер длинного видео

**Версия:** 4.3
**Дата:** 2026-05-29
**Режимы:** BIBLE (создание вселенной) + EPISODE (экранизация)
**Агентов:** 12
**ХАРД-СТОП:** После Кати (04) + Виктор (резидент-критик)
**Память:** Четыре слоя (Personal / Project / Runtime / Interaction)

---

## ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.3

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Боб = Chain Integrity, НЕ оценщик** | Боб проверяет структурную целостность цепочки (`chain_status: APPROVED/FAILED`). Оценку метрик делает Демон после публикации. Путаница ломала физику экономики |
| 2 | **`outcome_signal` всегда null от Боба** | Реальные метрики (просмотры, лайки, retention) собирает `metrics_daemon.py`. Боб их не знает — ролик ещё не опубликован |
| 3 | **`deliverables.video_clips` содержат `video_path`** | Феликс генерирует реальные `.mp4` через Wan2.2 I2V. Боб собирает файлы, не промпты. `veo3_prompts` — устаревшее поле старого сборочного |
| 4 | **Self-review у всех генераторов** | Ева (PNG), Феликс (grid mp4), Сэм (полный аудио arc), Трейси (PNG обложки) — каждый проверяет свой результат сам перед сдачей |
| 5 | **Монтажёр — следующий спринт, резидент на все цеха** | Сейчас Боб сдаёт разрозненные файлы. Финальная склейка (ffmpeg) — задача Монтажёра-резидента |
| 6 | **`model_decision` у каждого агента PROD/POST-PROD** | A05–A12 выбирают модель сами из DNA. Flash по умолчанию, Pro/Sonnet для сложных задач |

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
                            * хук: fal.ai → PNG
                            * ЭТАП 2: self_assessment (PNG) → APPROVED/REJECTED
    → 07 Тим Титр      🔤  — типографика
                            * model_decision
    → 08 Феликс FX     ✨  — motion_prompt (Wan2.2 I2V)
                            * ЭТАП 1: motion_prompt + model_decision
                            * хук: Wan2.2 → mp4 → grid (матрица кадров)
                            * ЭТАП 2: clip_assessment (grid) → APPROVED/REJECTED
                            * логирует compatibility_snapshot → interaction_log

  POST-PROD:
    → 09 Алекс Экшн    🏃  — моушн-анимация поверх клипов
                            * model_decision
    → 10 Сэм Стерео    🎧  — звуковой дизайн
                            * ЭТАП 1: music/sfx/vo промпты + model_decision
                            * хук: ElevenLabs/CosyVoice → аудио (полный файл)
                            * ЭТАП 2: audio_assessment (полный arc) → APPROVED/REJECTED
                            * mutations → Лавочка Артефактов
    → 11 Трейси Тизер  📱  — SMM + обложки A/B
                            * ЭТАП 1: banana_prompt variant_a/b + model_decision
                            * хук: fal.ai → PNG обложки
                            * ЭТАП 2: thumbnail_assessment (PNG) → APPROVED/REJECTED
    → 12 Боб Блокбастер 💰 — Chain Integrity Check + финальная сборка [QA-агент]
                            * НЕ оценивает для Министерства — это зона Демона
                            * chain_status: APPROVED/FAILED
                            * собирает deliverables (реальные файлы: PNG + mp4 + аудио)
                            * закрывает петлю памяти (history_dna, client_relationship)
                            * append-only лог в Министерство (факт транзакции)
                            * outcome_signal = null → Демон заполнит после публикации

    ⏳ МОНТАЖЁР (следующий спринт) — резидент на все цеха
                            * берёт video_clips[*].video_path от Феликса
                            * берёт аудио от Сэма
                            * склеивает через ffmpeg → финальный mp4
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

Демон (metrics_daemon.py) — внешний мир:
  → Активируется после публикации
  → Собирает реальные метрики: просмотры, удержание, лайки
  → Формирует feedback_scores
  → pipeline.py через _sync_feedback_scores_to_dna() → history_dna
```

**Боб не знает сколько просмотров будет. Демон не знает структуру цепочки.**
**Это разные роли. Смешивать нельзя.**

---

## 3. SELF-REVIEW — СИММЕТРИЯ АРХИТЕКТУРЫ

Все четыре генератора проверяют свой результат сами:

| Агент | Медиа | Как проверяет | Критерий |
|-------|-------|--------------|----------|
| Ева (06) | PNG кадр | vision → `self_assessment` | Мурашки есть? Анатомия чистая? |
| Феликс (08) | grid mp4 | vision → `clip_assessment` | Движение плавное? Grid слева направо |
| Сэм (10) | полный аудио arc | audio → `audio_assessment` | Посекундная разметка. Фальшь = REJECTED |
| Трейси (11) | PNG обложки | vision → `thumbnail_assessment` | Скролл остановит? |

**Принцип: никто не сдаёт вслепую. Никаких огрызков.**

- Ева: PNG целиком
- Феликс: grid — все кадры клипа, слева направо, сверху вниз
- Сэм: полный файл от первой до последней секунды
- Трейси: оба варианта A и B независимо

Максимум 3 попытки на каждый элемент. После трёх — `best_of_3`.

---

## 4. АРХИТЕКТУРА ПАМЯТИ — ЧЕТЫРЕ СЛОЯ

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal Memory | `grondheim_memory.py` + `dna.json` | Постоянно | Каждый агент |
| Project Memory | `history_dna` | Сезон | Боб (12) |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer | `interaction_log_video_long.jsonl` | Накопительно | Феликс (08) + Боб (12) |

*(Детальное описание слоёв — без изменений относительно v4.2)*

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

## 6. ПРОТОКОЛ chain_data (CHAIN_CONTRACT v1.1)

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
| Финальная склейка в mp4 | Монтажёр (резидент, след. спринт) | ffmpeg: клипы + аудио → ролик |
| `history_dna` | Боб (12) | Единственный источник |
| `client_relationship` | Боб (12) | Единственный источник |
| `model_decision` | Каждый агент A05–A12 | Из DNA, не из глобального конфига |
| `interaction_log` | Феликс (08) пишет, Боб (12) закрывает | append-only |

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
| 19 | **Монтажёр — резидент следующего спринта. Один на все цеха** |

---

## 9. ЧЕКЛИСТ ПОСЛЕ ПЕРВОГО РАНА

```
1. interaction_log_video_long.jsonl создан?
2. Боб проставил chain_status: APPROVED?
3. history_dna обновлён — narrative_entry, client_relationship?
4. outcome_signal = null (Демон заполнит)?
5. deliverables.video_clips содержат video_path (mp4)?
6. deliverables.key_frames содержат path (PNG)?
7. Все self_assessment.verdict = APPROVED у Евы, Феликса, Сэма, Трейси?
8. CulturalFieldTracker записал поле video_long?
9. client_relationship обновился в dna.json Боба?
10. victor_critique появился в chain_data?
```

---

*Студия "Шесть пальцев" | Версия 4.3 | 2026-05-29*
*Chain Integrity Боба. Демон считает лайки. Self-review у всех генераторов. Монтажёр — следующий спринт.*
