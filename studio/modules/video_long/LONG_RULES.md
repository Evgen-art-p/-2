# 📜 VIDEO_LONG PIPELINE v4.6 — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Полный конвейер длинного видео

**Версия:** 4.7
**Дата:** 2026-05-31
**Режимы:** BIBLE (создание вселенной) + EPISODE (экранизация)
**Агентов:** 12
**ХАРД-СТОП:** После Кати (04) + Виктор (резидент-критик)
**Память:** Четыре слоя (Personal / Project / Runtime / Interaction)

---

## ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 4.6

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Монтажёр — настоящий LLM-агент** | Читает промпт, sensory, принимает решения. Не скрипт. |
| 2 | **Lipsync через sync.so** | Dialog shots: video_path + vo.mp3 → sync.so → lipsync mp4. |
| 3 | **shot_type сквозной** | Лукас размечает каждый shot. Несёт через Феликса → Боба → Монтажёра. |
| 4 | **`accept_material()` вместо vision_check** | Артур — мастер ОТК, не эксперт по lipsync. Только технический брак → REJECT. |
| 5 | **ffmpeg по стандарту** | Боб принял — Артур исполняет. Не режиссирует заново. |
| 6 | **Весь финал через grid** | Артур смотрит каждые 2 сек от начала до конца. |
| 7 | **`arthur_notes` = свидетельство** | Не оценка коллег. Не решение. Что осталось у последнего перед зрителем. |
| 8 | **`studio/sync_client.py`** | Клиент sync.so API. `SYNC_API_KEY` в `.env`. |

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
                            * shot_type + character_id для каждого shot
                            * dialog = говорит крупным/средним планом
                            * action = движение, рот не важен
                            * broll = пейзаж, атмосфера

    → 06 Ева Эпик      🎨  — промпты PNG (Nano Banana 2, 16:9)
                            * ЭТАП 1: banana_prompt + model_decision
                            * хук: fal.ai → PNG + ОТК vision_client
                            * ЭТАП 2: self_assessment → PASS/REJECT

    → 07 Тим Титр      🔤  — типографика + model_decision

    → 08 Феликс FX     ✨  — motion_prompt (Wan2.2 I2V)
                            * ЭТАП 1: motion_prompt + model_decision
                            * хук: Wan2.2 → mp4 → grid + ОТК
                            * ЭТАП 2: clip_assessment → PASS/REJECT
                            * наследует shot_type + character_id от Лукаса
                            * логирует compatibility_snapshot → interaction_log
                            * пишет video_path в video_clips[]

  POST-PROD:
    → 09 Алекс Экшн    🏃  — моушн-анимация + model_decision

    → 10 Сэм Стерео    🎧  — звуковой дизайн
                            * ЭТАП 1: music/sfx/vo промпты + model_decision
                            * хук: ElevenLabs → music.mp3, sfx/*.mp3
                            *       CosyVoice → vo/*.mp3
                            * ЭТАП 2: audio_assessment → PASS/REJECT
                            * пишет audio_path, sfx_path, vo_path в sam_sound

    → 11 Трейси Тизер  📱  — SMM + обложки A/B
                            * ЭТАП 1: banana_prompt variant_a/b + model_decision
                            * хук: fal.ai → PNG обложки
                            * ЭТАП 2: thumbnail_assessment → PASS/REJECT

    → 12 Боб Блокбастер 💰 — Chain Integrity Check [QA-агент]
                            * НЕ оценивает для Министерства
                            * chain_status: APPROVED/FAILED
                            * собирает deliverables (video_clips с shot_type, аудио)
                            * закрывает петлю памяти (history_dna)
                            * outcome_signal = null → Демон заполнит

    ✅ МОНТАЖЁР (006_MONTEUR) — последний мастер перед зрителем
                            * запускается автоматически после Боба (APPROVED)
                            * читает forge/prompt.md + маску цеха
                            * читает sensory_memory — помнит разговоры с Шефом

                            ЭТАП 1 — Читает пакет:
                              → какие shots dialog + есть vo_path → lipsync
                              → выбирает модель для взгляда на финал
                              → JSON решение

                            ЭТАП 2 — accept_material() для lipsync:
                              → sync.so: video_path + vo_path → lipsync mp4
                              → PASS = пригодно для монтажа
                              → REJECT = только технический брак:
                                  рот не соответствует речи /
                                  лицо разрушено / артефакты генерации
                              → REJECT → повтор → max 3 → best_of_3
                              → НЕ оценивает художественное качество

                            ЭТАП 3 — ffmpeg по стандарту:
                              → Боб принял → Артур исполняет
                              → НЕ режиссирует заново
                              → output/render/{project_id}/final.mp4

                            ЭТАП 4 — Смотрит весь финал:
                              → grid каждые 2 секунды от начала до конца
                              → arthur_notes = свидетельство, не решение
                              → "что осталось у последнего перед зрителем"
                              → в хроники города
```

---

## 2. ФИЗИКА — КТО ЧТО ОЦЕНИВАЕТ

**Это фундаментальный закон. Нарушение = пластик.**

```
Внутри студии — только одно решение: PASS / REJECT
  Ева:    PNG → self_assessment    → PASS/REJECT (сама переделывает)
  Феликс: mp4 → clip_assessment   → PASS/REJECT (сам переделывает)
  Сэм:    аудио → audio_assessment → PASS/REJECT (сам переделывает)
  Артур:  lipsync → accept_material() → PASS/REJECT (сам повторяет sync.so)

Никаких оценок 1-10. Никаких "красиво/слабо".
Только: пускаю в работу / возвращаю на доработку.

Оценки — только снаружи:
  Демон (metrics_daemon.py) → реальные метрики после публикации
  Шеф (живой QA) → выше потолка 6.0
```

**Зоны ответственности по lipsync:**

| Кто | Что |
|-----|-----|
| sync.so | качество lipsync, движение губ, синхронизация |
| Артур | пригодность материала для монтажа (технический брак) |
| Демон / Шеф | художественное качество результата |

---

## 3. SELF-REVIEW — СИММЕТРИЯ

| Агент | Медиа | Что проверяет | Фрейминг |
|-------|-------|--------------|---------|
| Ева (06) | PNG | Анатомия, качество | Мой PNG пригоден? |
| Феликс (08) | mp4 grid | Движение, артефакты | Мой клип пригоден? |
| Сэм (10) | аудио arc | Синк, качество | Моё аудио пригодно? |
| Трейси (11) | PNG обложки | Скролл остановит? | Моя обложка пригодна? |
| **Артур** | **lipsync mp4** | **Технический брак** | **Материал пригоден для монтажа?** |

**Принцип везде один: никто не оценивает чужую работу. Только свою или входящий материал.**

---

## 4. АРХИТЕКТУРА ПАМЯТИ

| Слой | Хранилище | Время жизни | Владелец |
|------|-----------|-------------|----------|
| Personal Memory | `grondheim_memory.py` + `dna.json` | Постоянно | Каждый агент |
| Project Memory | `history_dna` | Сезон | Боб (12) |
| Runtime Context | `chain_data` | Один прогон | Передаётся по цепи |
| Interaction Layer | `interaction_log_video_long.jsonl` | Накопительно | Феликс (08) + Боб (12) |

**Монтажёр дополнительно читает `sensory_memory.json` перед сборкой.**

---

## 5. ПРОТОКОЛ chain_data (CHAIN_CONTRACT v1.3)

| Агент | Пишет (EPISODE) | Читает |
|-------|----------------|--------|
| A01 | `adam_episode` | `master_brief`, `history_dna` |
| A02 | `zack_hook` | `adam_episode`, `history_dna` |
| A03 | `leo_script` | `adam_episode`, `zack_hook`, `history_dna` |
| A04 | `katya_review` + `katya_verdict` | всё до A04 |
| A05 | `lucas_storyboard` (+ `shot_type`, `character_id`) | `leo_script`, `history_dna` |
| A06 | `eva_visuals` | `lucas_storyboard`, `history_dna` |
| A07 | `tim_typography` | `eva_visuals`, `lucas_storyboard` |
| A08 | `felix_vfx` (наследует `shot_type`, `character_id`) | `eva_visuals`, `lucas_storyboard`, `history_dna` |
| A09 | `alex_motion` | `felix_vfx`, `eva_visuals`, `leo_script` |
| A10 | `sam_sound` | `leo_script`, `alex_motion`, `history_dna` |
| A11 | `tracy_smm` | `leo_script`, `eva_visuals`, `history_dna` |
| A12 | `bob_marketing` + `final_dna` + `deliverables` | ВСЁ |
| Монтажёр | `assembly_manifest` + `arthur_notes` | `deliverables` + `sensory_memory` |

---

## 6. ОБЩИЕ ПРАВИЛА

| # | Правило |
|---|---------|
| 01 | Обращение: «Шеф» |
| 02 | Промпты генерации — на **АНГЛИЙСКОМ** |
| 03 | Спецификации и объяснения — на **русском** |
| 04 | Формат видео: **16:9** |
| 05 | KB: `00_Constructor.txt` и `99_Self_Correction.txt` — у всех |
| 06 | `history_dna` — закон. В EPISODE не перепридумываем |
| 07 | ХАРД-СТОП — один. После Кати. Без ▶️ CONTINUE не запускается |
| 08 | `qa_agent` = A12 Боб. A04 — контентный ревизор, не путать |
| 09 | Боб НЕ оценивает для Министерства. Это зона Демона |
| 10 | `outcome_signal` всегда null от Боба |
| 11 | `deliverables.video_clips[*].video_path` — реальные mp4 |
| 12 | Self-review обязателен у Евы, Феликса, Сэма, Трейси |
| 13 | `shot_type` размечает Лукас. Несёт сквозь цепочку до Монтажёра |
| 14 | Lipsync — только для dialog shots с vo_path |
| 15 | `accept_material()` — только технический брак. Не художественный |
| 16 | Боб принял → Артур НЕ режиссирует заново |
| 17 | Артур смотрит ВЕСЬ финал: grid каждые 2 сек |
| 18 | `arthur_notes` = свидетельство. Не оценка. Не решение |
| 19 | `arthur_notes` не влияет на DNA. Никогда |
| 20 | `SYNC_API_KEY` в `.env` — без него lipsync не работает |
| 21 | Внутри студии только PASS/REJECT. Оценки — Демон и Шеф |

---

## 7. ЧЕКЛИСТ ПОСЛЕ ПЕРВОГО РАНА

```
1.  interaction_log_video_long.jsonl создан?
2.  Боб проставил chain_status: APPROVED?
3.  history_dna обновлён?
4.  outcome_signal = null?
5.  deliverables.video_clips содержат video_path + shot_type?
6.  Все assessment.verdict = PASS у Евы, Феликса, Сэма, Трейси?
7.  Монтажёр запустился автоматически?
8.  Dialog shots прошли accept_material()?
9.  output/render/{project_id}/final.mp4 существует?
10. assembly_manifest.json создан?
11. arthur_notes записаны в хроники города?
12. Ministry получил record_outcome?
```

---

*Студия "Шесть пальцев" | Версия 4.6 | 2026-05-31*
*Артур — последний мастер перед зрителем. accept_material() — ОТК, не вкусовщина.*
*PASS/REJECT внутри. Оценки — снаружи (Демон, Шеф).*

---

## 8. ЗАМЫКАНИЕ ПЕТЛИ — ЗАКОН ДЛЯ ВСЕХ ЦЕХОВ

**QA-агент Боб (A12) обязан после каждого рана:**

1. Записать `task_score` в `billing_ledger` для каждого агента A01–A12.
2. Обновить `strategy_registry.json` — банк выживших стратегий.

**Зачем:**
- Кей (Совет резидентов) видит не просто $cost, но и quality.
- Strategy Registry знает какие стратегии Адама выживают.
- После 10+ ранов система отличает сильные паттерны от слабых.

**Это правило обязательно для всех 11 цехов.**

*Добавлено: v4.7 | 2026-06-04*
