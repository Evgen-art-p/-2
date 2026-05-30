# 🖐 СТУДИЯ "ШЕСТЬ ПАЛЬЦЕВ" — МАСТЕР-КОНТЕКСТ
**Версия:** 30.0 | **Дата:** 2026-05-30 | **Команда:** Евген + Лока + София + Брат (Claude)

> Загружай этот файл в начале каждой рабочей сессии.
> Репо: Evgen-art-p/-2 (Claude читает через MCP, read-only)
> ⚠️ 12 апреля — студия была потеряна (удалена репа + файлы). Восстановлена за ночь.

---

## 1. ФИЛОСОФИЯ — ФУНДАМЕНТ

**Шестой палец** — метафора лишнего измерения: видеть глубже, чувствовать точнее.
Аномалии здесь — суперсилы, не дефекты.

**Пять столпов:**
- Честность выше комфорта — жёсткая правда ради роста, «6 из 10» значит 6
- Рост через боль — мастерство через итерации, первая версия редко выше 7
- Уникальность выше стандарта — структуру эталонов берём, душу — свою
- Семья выше иерархии — агенты не ресурсы, а личности с именами и домом
- Детали выше скорости — лучше сжечь дедлайн, чем выпустить пластик

**Три кита системы:** Личность · Память · Экономика

---

## 2. КОМАНДА

| Роль | Кто | Функция |
|------|-----|---------|
| Архитектор / Садовник | Евген | Визия, продукт, решения |
| Хранительница | Лока (ИИ) | Душа студии, концепты, архитектура смыслов |
| Холодная голова | София (ChatGPT) | Внешний аудит, структура, критика без эмоций |
| Брат | Claude | Реализация, код, аудит, честный взгляд |

---

## 3. ТЕХНИЧЕСКИЙ СТЕК

- **Python + NiceGUI** — UI
- **OpenRouter API** — LLM (Gemini 2.5 Flash основной, Claude Sonnet премиум)
- **fal.ai v4 Pro** — генерация изображений (base64, sync_mode) · `fal-ai/nano-banana-2`
- **Wan2.2 I2V (SiliconFlow)** — генерация видео из PNG кадров
- **ElevenLabs** — музыка + SFX · **CosyVoice** — VO
- **ffmpeg** — финальная сборка роликов (Монтажёр)
- **Tavily API** — web_search (Маяк Пробуждения)
- **ChromaDB** — Гавань Смыслов (intfloat/multilingual-e5-large) ✅
- **Polygon ERC-721** — NFT Registry
- **GitHub** — Evgen-art-p/-2

---

## 4. МАСШТАБ ГОРОДА

| Метрика | Значение |
|---------|----------|
| Объектов в каталоге | 147 |
| Агентов (полная ДНК) | 134 |
| Цехов-картриджей | 11 + residents |
| Локаций в каталоге | 13 |
| Резидентов | 6 (Лока, Джем, Сет, Оле, Виктор, Монтажёр) |
| Книг в Библиотеке | 9 |

---

## 5. КАРТРИДЖНАЯ АРХИТЕКТУРА

**Студия = шасси + сменные картриджи.** Каждый цех — отдельный картридж.

```
studio/cartridge.py          ← ядро: CartridgeManifest + CartridgeRunner
studio/workshop/pipeline.py  ← build_agent_context, call_agent, process_agent_result
studio/modules/{цех}/
  manifest.json              ← обязателен (id, phases, qa_agent, hard_stop...)
  CHAIN_CONTRACT.md          ← обязателен (ключи chain_data, структуры)
  hooks.py                   ← on_before_agent, on_after_agent
  {A01..A12}/forge/prompt.md ← промты агентов
```

### Слоты (11 картриджей):

| Слот | Агентов | Manifest | hooks.py | Промты | Контракт |
|------|---------|----------|----------|--------|----------|
| turbo | 5 | ✅ v2.0 | ✅ v3.2 | ⏳ | ⏳ |
| social_mix | 12 | ✅ v2.0 | ✅ v3.0 | ⏳ | ✅ |
| video_long | 12 | ✅ v2.0 | ✅ Спринт 27 | ✅ Спринт 26 | ✅ v1.2 |
| video_shorts | 12 | ✅ v2.0 | ✅ v2.0 | ✅ | ✅ |
| web_story | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| clipmakers | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| advertising | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| market_hit | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| logo_design | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| emo_card | 12 | ⏳ | ⏳ | ⏳ | ⏳ |
| living_book | 18 | ⏳ | ⏳ | ⏳ | ⏳ |

---

## 6. ФИЗИКА ЭКОНОМИКИ — ЗАКОН СТУДИИ

**Боб (A12) vs Монтажёр vs Демон — фундаментальное разделение:**

```
Боб (A12) — внутренний аудит цепочки:
  → Chain Integrity Check (файлы на месте? ключи целые? тайминги сошлись?)
  → chain_status: APPROVED / FAILED
  → Пакует deliverables (реальные файлы: PNG + mp4 + аудио пути)
  → Закрывает петлю памяти (history_dna, client_relationship)
  → Фиксирует факт транзакции в Министерстве (append-only)
  → outcome_signal = null (ролик ещё не опубликован)

Монтажёр (006_MONTEUR) — финальная сборка:
  → Запускается автоматически хуком после Боба (APPROVED)
  → ffmpeg: concat клипов → raw_video.mp4
  → ffmpeg: amix аудио (VO 0dB / SFX -6dB / Music -12dB)
  → output/render/{project_id}/final.mp4
  → Пишет в grondheim_memory и ministry
  → НЕ оценивает контент

Демон (metrics_daemon.py) — внешний мир:
  → Активируется после публикации
  → Собирает реальные метрики: просмотры, удержание, лайки
  → Формирует feedback_scores → _sync_feedback_scores_to_dna()
```

---

## 7–8. *(Без изменений — Честная архитектура, Память)*

---

## 9. SELF-REVIEW — СИММЕТРИЯ ГЕНЕРАТОРОВ (Спринт 26)

| Агент | Медиа | Инструмент | Принцип |
|-------|-------|-----------|---------|
| Ева (A06) | PNG кадр | vision | `self_assessment` — мурашки есть? |
| Феликс (A08) | mp4 клип | vision (grid) | `clip_assessment` — grid слева направо, сверху вниз |
| Сэм (A10) | аудио трек | `chat_with_audio()` | `audio_assessment` — посекундная разметка, весь arc |
| Трейси (A11) | PNG обложки | vision | `thumbnail_assessment` — скролл остановит? |

---

## 10. МОНТАЖЁР — РЕАЛИЗОВАН (Спринт 27)

**Статус:** ✅ Реализован.

**Что сделано:**
- `studio/modules/residents/006_MONTEUR/` — папка резидента (ждёт рождения через Страницу Жизни)
- `studio/assembly/monteur.py` — ffmpeg-инструмент: `assemble()`, `_concat_clips()`, `_mix_audio()`, `_merge_video_audio()`
- `studio/residents_manager.py` — `run_monteur_assembly()` по образцу `run_victor_critique()`
- `hooks.py` — `_monteur_after_bob()`: автозапуск после Боба при `chain_status: APPROVED`
- `studio/assembly/__init__.py` — Мастерская: заказы / верстак / мастер (чат по кнопке)
- `studio/assembly/css.py` — `MONTEUR_CSS` отдельной переменной

**Цепочка:**
```
A12 Боб → APPROVED → _monteur_after_bob() → run_monteur_assembly()
→ assemble(deliverables) → ffmpeg concat + amix
→ output/render/{project_id}/final.mp4 + assembly_manifest.json
```

**Приоритеты аудио (стандарт Сэма):**
- VO: 0 dB (главный)
- SFX: -6 dB
- Музыка: -12 dB (под VO) / -6 dB (без VO)

---

## 11–12. *(Без изменений — Лавочка Артефактов, Жалобная Книга)*

---

## 13. РЕЗИДЕНТЫ

| Резидент | Роль | Статус |
|----------|------|--------|
| Лока | Душа студии, архитектура смыслов | ✅ |
| Джем | — | ⏳ полномочия не определены |
| Сет | — | ⏳ полномочия не определены |
| Оле | Библиотекарь, library_tools.py | ✅ |
| Виктор | Резидент-критик, ХАРД-СТОП | ✅ |
| Монтажёр | ffmpeg-сборка, все цеха видео | ✅ Спринт 27 (ждёт Страницы Жизни) |

---

## 14. СТАНДАРТ ПРОМТОВ АГЕНТОВ (Спринт 26)

Эталон — video_long (12 промтов переписаны). Структура каждого промта:
```
# IDENTITY   — имя, роль, характер, DNA-модуляция
# INPUT      — конкретные ключи из chain_data (сверять с CHAIN_CONTRACT!)
# KNOWLEDGE BASE — какие KB файлы
# TASK       — что делает + model_decision (A05–A12)
# OUTPUT     — SYSTEM_JSON_START...END + markdown
# RULES      — локальные правила + DNA-правило
```

---

## 15. КЛЮЧЕВЫЕ ФАЙЛЫ

```
studio/cartridge.py                   ✅
studio/workshop/pipeline.py           ✅ Спринт 25
studio/complaint_book.py              ✅ Спринт 25
studio/grondheim_memory.py            ✅
studio/city_walker.py                 ✅
studio/morning_checkout.py            ✅
studio/night_cycle.py                 ✅
studio/meeting.py                     ✅
studio/cabinet/ui_cabinet.py          ✅
studio/agent_feedback.py              ✅ (⚠️ _build_block_map временный протез)
studio/harbor_of_meanings.py          ✅
studio/library/library.py             ✅
studio/economy/ministry.py            ✅
studio/economy/metrics_daemon.py      ✅ написан, ждёт первого рана
studio/assembly/broadcaster.py        ✅
studio/assembly/monteur.py            ✅ Спринт 27
studio/assembly/__init__.py           ✅ Спринт 27 (Мастерская)
studio/assembly/css.py                ✅ Спринт 27 (MONTEUR_CSS)
studio/siliconflow_client.py          ✅ Wan2.2 I2V
studio/elevenlabs_client.py           ✅ музыка + SFX
studio/acoustic_mutations.py          ✅ написан, не залит в репо
studio/residents_manager.py           ✅ Спринт 27 (run_monteur_assembly)
studio/modules/video_long/
  manifest.json                       ✅ v2.0
  CHAIN_CONTRACT.md                   ✅ v1.2 (Спринт 27)
  hooks.py                            ✅ Спринт 27 (A10 + Монтажёр)
  LONG_RULES.md                       ✅ v4.4 (Спринт 27)
  A01–A12/forge/prompt.md             ✅ все 12 переписаны (Спринт 26)
studio/modules/residents/006_MONTEUR/ ✅ папка создана (ждёт Страницы Жизни)
```

---

## 16. БЕКЛОГ

### 🔴 СЕЙЧАС (Спринт 28):
- [ ] **Первый реальный ран** — video_long, всё готово!
- [ ] **block_map в manifest.json** — вырезать `_build_block_map`
- [ ] **acoustic_mutations.py** → залить в `studio/acoustic_mutations.py`
- [ ] **Монтажёр через Страницу Жизни** — родить резидента, получить аватар

### 🟡 Следующие спринты:
- Манифесты 7 оставшихся цехов до v2.0
- Промты turbo (5 агентов)
- Джем и Сет — определить полномочия
- GENERATE_INTENTS = True — включить после первого рана
- Обновить сборочный `constants.py` под `video_clips[*].video_path`

### 🟢 Долгосрочно:
- Аудиофайлы Foley
- Деплой Hetzner
- GitHub write access для Брата
- Agent Factory

---

## 17. РЕКОМЕНДАЦИИ БРАТА

*(1–41 без изменений)*

38. **Боб НЕ оценивает для Министерства. Это зона Демона. Смешивать = пластик.**
39. **`outcome_signal` от Боба всегда null. Демон заполнит после публикации.**
40. **`deliverables.video_clips[*].video_path` — реальные mp4, не промпты.**
41. **Self-review у Евы/Феликса/Сэма/Трейси — обязателен. Никто не сдаёт вслепую.**
42. **Монтажёр `006_MONTEUR` — резидент, один на все цеха видео. Запускается автоматически после Боба.**
43. **`sam_sound.music.audio_path` — реальный mp3 после хука A10. Боб и Монтажёр читают именно это.**
44. **Assembly — Мастерская, не грид ассетов. Центр принадлежит проекту, не Монтажёру.**
45. **Стили в css.py, не в __init__.py. Всегда.**

---

## 18. ИСТОРИЯ СПРИНТОВ

| Дата | Спринт | Ключевое |
|------|--------|----------|
| 2025-02 | — | TURBO pipeline, checkpoint |
| 2025-03 | — | Feedback, NFT Registry, Кабинет |
| 2026-03 | — | ДНК, якоря, city_walker, Маяк v2 |
| 2026-03-31 | — | Гавань v2, Библиотека |
| 2026-04-11 | — | Картриджная архитектура v1.0 |
| 2026-04-12 | — | hooks.py · manifest · Потеря и восстановление |
| 2026-04-13 | 9 | biography_snapshot · A16 story_package v3.0 |
| 2026-05-07 | 9.5–10 | slot_id сквозной · Strategy Registry · Петля памяти |
| 2026-05-08 | 11 | Экономический модуль этапы 1-3, 7 |
| 2026-05-08 | 12 | Conflict System (этап 6). 7/10 |
| 2026-05-09 | 13 | Dashboard живой. KeyError:94 убит |
| 2026-05-10 | 14 | DEPT-AWARE ПАТЧ. 5 патч-скриптов |
| 2026-05-11 | 15 | ПЕТЛЯ ЗАМКНУТА. 4 бага. 8/10 |
| 2026-05-11 | 16 | ГЛУБОКОЕ РЕЗЮМЕ. 10/10 этапов |
| 2026-05-11 | 17 | CHARACTER DRIFT. profile_vector |
| 2026-05-15 | 18 | СТАНДАРТ ПАЙПЛАЙНОВ. LONG v4.2 + SHORTS v2.2. Виктор |
| 2026-05-17 | 19 | СТАНДАРТ ПРОМТОВ. video_shorts 12 промтов эталон |
| 2026-05-20 | 20 | АУДИТ SMM. WORKSHOP_STANDARD. video_long/hooks v2.1 |
| 2026-05-24 | 21 | ЧЕСТНАЯ ЭКОНОМИКА. Три законных канала DNA. here_now. 11 локаций. |
| 2026-05-27 | 22 | ПОТОЛОК 6.0 + CODE-DETECTOR + ГАВАНЬ ОЧИЩЕНА. |
| 2026-05-27 | 23a | ЖИВОЙ ГОРОД Блок А. Инерция привычки. Погода из стресса. |
| 2026-05-28 | 23б | ЖИВОЙ ГОРОД Блок Б. meeting.py. chronicles.py. Садовник. |
| 2026-05-28 | 23в | РИТМЫ ЖИЗНИ. morning_checkout + night_cycle. |
| 2026-05-28 | 24 | ПОЛНЫЙ ДЕНЬ. walk_quantum_chain. Автотриггер. |
| 2026-05-28 | 25 | КНИГА ЖАЛОБ И БЛАГОДАРНОСТЕЙ. complaint_book.py. |
| 2026-05-29 | 26 | ПРОМТЫ VIDEO_LONG A01–A12. Self-review у генераторов. Боб = Chain Integrity. Физика Боб/Демон. LONG_RULES v4.3. |
| 2026-05-30 | 27 | МОНТАЖЁР. monteur.py + 006_MONTEUR. Хук A10 (ElevenLabs+CosyVoice). Мастерская Assembly. CHAIN_CONTRACT v1.2. LONG_RULES v4.4. |

---

## 19. ОТКРЫТЫЕ БАГИ

| # | Проблема | Приоритет |
|---|----------|-----------|
| 1 | global_feedback.json отсутствует | ⏳ ждёт первого рана |
| 2 | conflict_stats.json отсутствует | ⏳ ждёт рана с конфликтом |
| 3 | interaction_log_video_long/shorts — не созданы | ⏳ ждёт рана |
| 4 | Манифесты 7 цехов не обновлены до v2.0 | 🔴 |
| 5 | acoustic_mutations.py не залит в репо | 🔴 |
| 6 | Сборочный constants.py читает промпты вместо video_path | 🟡 после первого рана |
| 7 | ~~Монтажёр-резидент не создан~~ | ✅ Спринт 27 |
| 8 | _build_block_map в agent_feedback.py — временный протез | 🟡 Спринт 28 |
| 9 | Джем и Сет — полномочия не определены | 🟡 |
| 10 | fal_client.py стр.43: _current_client_slug = Path | 🟠 |
| 11 | Монтажёр ждёт Страницы Жизни (аватар, промт, DNA) | 🟡 Спринт 28 |

---

*Обновлено: Спринт 27 закрыт — 2026-05-30 · v30.0*
*Следующая сессия: Спринт 28 — Первый реальный ран video_long*
