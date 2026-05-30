# 📜 TURBO PIPELINE — ЭТАЛОННЫЕ ПРАВИЛА
## Студия "Шесть пальцев" | Быстрый конвейер шортсов

**Версия:** 3.1
**Дата:** 2026-05-16
**Режим:** TURBO (5 агентов)
**Модель:** Nano Banana 2 (Gemini 3 Flash Image)
**Генерация:** Внутри пайплайна (A03 кадры, A05 обложки)

---

## ⚡ ЧТО ИЗМЕНИЛОСЬ В ВЕРСИИ 3.1

| # | Изменение | Почему |
|---|-----------|--------|
| 1 | **Двойная нотация** зафиксирована явно | T1–T5 = кодовые имена персонажей (в промптах и chain_data). A01–A05 = системные ID (папки, worker_id в pipeline). Путаница ломала hooks.py |
| 2 | **hooks.py v3.2** — `worker_id "T3"/"T5"` → `"A03"/"A05"` | Конвейер не запускал генерацию — pipeline передаёт A-нотацию, а хуки ждали T-нотацию |
| 3 | **agent_id** в `_generate_with_retries` → `"A03"/"A05"` | billing_ledger записывал генерацию под несуществующими агентами |
| 4 | **`_get_project_id`** — добавлен fallback на `a01_strategy` | Защита от потери project_id если pipeline генерирует ключи по worker_id |
| 5 | **Секция 13** — исправлены имена resonance-файлов | `resonance_log.json` не существует. Реально: `emotional_weights.json` + `event_log.json` |
| 6 | **manifest.json** — `qa_agent: "A05"`, A-нотация везде | Стандарт студии. Было `"T5"` — петля памяти не закрывалась |

---

## 1. АРХИТЕКТУРА ПАЙПЛАЙНА

```
A01 / T1 Стелла Стратег (🧠) — стратегия + сценарий + SEO + подбор ассетов
        │
        ├──→ A02 / T2 Мими Мем (🎵) — звук     ⎤
        │                                        ⎥ ПАРАЛЛЕЛЬНО
        └──→ A03 / T3 Визор (🎬) — визуал       ⎦
                    │              │             🔴 A03 ГЕНЕРИТ КАДРЫ через fal.ai
                    └──────┬───────┘
                           ▼
              A04 / T4 Постпро (✂️) — монтаж + retention + субтитры
                           │
                           ▼
              A05 / T5 Финализатор (🏁) — обложка + финальная сборка [qa_agent]
                                          🔴 A05 ГЕНЕРИТ ОБЛОЖКИ через fal.ai
```

### Потоки данных:
- A01 → A02 + A03 (параллельно)
- A02 + A03 → A04 (оба потока)
- A04 → A05 (вся цепочка)

### ⚠️ Двойная нотация — важно понимать

| Нотация | Где используется | Пример |
|---------|-----------------|--------|
| **T1–T5** (кодовые имена) | Промпты агентов, chain_data ключи, TURBO_RULES | `stella_strategy`, `vizor_visual` |
| **A01–A05** (системные ID) | Папки на диске, worker_id в pipeline, manifest.json, hooks.py | `worker_id == "A03"` |

Это не противоречие — это два уровня одной системы. Агент называет себя T3 Визором в тексте, а pipeline находит его по папке `A03/`.

---

## 2. ПРОТОКОЛ chain_data

Каждый агент получает данные через `chain_data` и добавляет свой `my_output`.

| Агент | worker_id | Получает | Добавляет | Передаёт |
|-------|-----------|----------|-----------|----------|
| T1 Стелла | A01 | master_brief | stella_strategy | → A02, A03 |
| T2 Мими | A02 | master_brief, stella_strategy | mimi_sound | → A04 |
| T3 Визор | A03 | master_brief, stella_strategy | vizor_visual (с **путями** к кадрам) | → A04 |
| T4 Постпро | A04 | master_brief, stella_strategy, mimi_sound, vizor_visual | postpro | → A05 |
| T5 Финализатор | A05 | ВСЁ | thumbnail (с **путями**), deliverables, final_dna | → DONE |

### Наследование:
- `"master_brief": "{{inherit}}"` — передавать без изменений
- `"stella_strategy": "{{inherit}}"` — передавать без изменений
- `"my_key": "{{my_output}}"` — вставить свой результат

---

## 3. ФОРМАТ ВЫВОДА

### Порядок: JSON → Markdown
Все агенты выводят в одном порядке:
1. **JSON** — для системы (машиночитаемые данные) — **ВСЕГДА ПЕРВЫМ**
2. **Markdown** — для Шефа (человекочитаемый отчёт)

### JSON-маркеры:
```
👇 SYSTEM_JSON_START 👇
{ ... }
👆 SYSTEM_JSON_END 👆
```
Парсер ищет JSON по маркерам `SYSTEM_JSON_START` / `SYSTEM_JSON_END`.

---

## 4. СЕГМЕНТАЦИЯ

### Стелла (T1 / A01) определяет сегменты. Все остальные агенты следуют её разбивке.

Стандартная разбивка для 30-секундного шортса:
| Сегмент | Тайминг | Назначение |
|---------|---------|------------|
| 1 | 0–1.5s | hook |
| 2 | 1.5–5s | setup |
| 3 | 5–15s | body |
| 4 | 15–25s | climax |
| 5 | 25–30s | cta_loop |

**Важно:** `total_duration_sec` из `stella_strategy.script` — источник истины для всех.

---

## 5. ЗОНЫ ОТВЕТСТВЕННОСТИ

| Зона | Хозяин (имя / worker_id) | Кто НЕ делает |
|------|--------------------------|---------------|
| Сценарий, сегменты, тайминги | T1 Стелла / A01 | — |
| Подбор ассетов (selected_assets) | T1 Стелла / A01 | — |
| Звук, BPM, SFX, beat_map, Suno | T2 Мими / A02 | — |
| Key frames, Banana-промпты, Veo3-промпты | T3 Визор / A03 | — |
| ref_ids в ключевых кадрах | T3 Визор / A03 | — |
| **🔴 Генерация ключевых кадров (fal.ai)** | **hooks.py** (перехватывает A03) | A03 пишет промпты — система генерит |
| Монтаж, retention, loop, субтитры | T4 Постпро / A04 | — |
| **Обложка (thumbnail A/B)** | **T5 Финализатор / A05** | A03 НЕ делает обложку |
| **🔴 Генерация обложек (fal.ai)** | **hooks.py** (перехватывает A05) | A05 пишет промпты — система генерит |
| Финальная сборка (deliverables) | T5 Финализатор / A05 | — |
| DNA (архив проекта) | T5 Финализатор / A05 | — |
| Закрытие петли памяти [qa_agent] | T5 Финализатор / A05 | — |

---

## 6. KNOWLEDGE BASE

### Общие для всех агентов:
| Файл | Назначение |
|------|------------|
| 00_Constructor.txt | Универсальный конструктор смыслов |
| 99_Self_Correction.txt | ОТК — финальная проверка |

### Индивидуальные — указаны в промпте каждого агента.

### Актуальная модель генерации:
- **Nano Banana 2** (Gemini 3 Flash Image)
- Subject Consistency: до 5 персонажей, 10 объектов
- Text Rendering: улучшенная читаемость текста
- Visual Reasoning: понимание контекста сцены

---

## 7. РАБОТА С АССЕТАМИ

### Подбор: T1 Стелла (A01)
- Ищет в каталоге по TAGS, MOOD, USE_CASES
- Максимум 6 ассетов на шортс
- Формат: `selected_assets` в JSON

### Использование: T3 Визор (A03)
- Каждый key_frame содержит `ref_ids` — список asset_id
- В промпте: `Figure N` = позиция в `ref_ids` (1-indexed)
- Порядок: персонажи → локации → пропы
- `visual_anchor` — включать ДОСЛОВНО

### Обложка: T5 Финализатор (A05)
- `ref_ids` обязательны для обоих вариантов обложки (A/B)

---

## 8. ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (v3.1)

### Ключевые кадры (T3 Визор / A03):
1. A03 пишет `banana_prompt` и `ref_ids` для каждого кадра
2. **hooks.py перехватывает** ответ A03 (`worker_id == "A03"`)
3. Система вызывает `generate_with_refs()` или `generate_image()` для каждого кадра
4. Gemini Flash проверяет качество каждой картинки (до 5 ретраев)
5. Готовые картинки сохраняются в `output/generated/{project_id}/`
6. Пути записываются в `key_frames[].path`
7. Обновлённый `state` передаётся дальше по пайплайну

### Обложки (T5 Финализатор / A05):
1. A05 пишет `banana_prompt` и `ref_ids` для variant_a и variant_b
2. **hooks.py перехватывает** ответ A05 (`worker_id == "A05"`)
3. Система вызывает `generate_with_refs()` или `generate_image()` для каждой обложки
4. Gemini Flash проверяет качество (до 5 ретраев)
5. Готовые картинки сохраняются в `output/generated/{project_id}/`
6. Пути записываются в `thumbnail.variant_a.path` и `thumbnail.variant_b.path`
7. deliverables собираются с готовыми путями

### Параметры вызова:
- `agent_id`: `"A03"` (для кадров), `"A05"` (для обложек)
- `slot_id`: `"turbo"`
- `format`: `"9:16"`
- Все вызовы записываются в `billing_ledger`

### Качество — Gemini Flash:
| Score | Статус |
|-------|--------|
| ≥ 6 | ✅ принято |
| < 6 | 🔄 ретрай (промпт + Fix: notes) |
| 5 попыток не дали ≥ 6 | ⚠️ fallback — берём лучшую |

### Форматы генерации:
| Тип | Формат | Модель | agent_id |
|-----|--------|--------|----------|
| Ключевые кадры | 9:16 | Nano Banana 2 | A03 |
| Обложки A/B | 9:16 | Nano Banana 2 | A05 |

### Пути к результатам:
```
output/generated/{project_id}/
├── frame_01_{segment}_{purpose}.png
├── frame_02_{segment}_{purpose}.png
├── frame_03_{segment}_{purpose}.png
├── frame_04_{segment}_{purpose}.png
├── frame_05_{segment}_{purpose}.png
├── thumb_variant_a.png
└── thumb_variant_b.png
```

---

## 9. ОБЩИЕ ПРАВИЛА (ВСЕ АГЕНТЫ)

1. Обращение к пользователю: **«Шеф»**
2. Промпты генерации — на **АНГЛИЙСКОМ**
3. Объяснения — на **русском**
4. Формат видео: **9:16** (вертикальный) — горизонтальных кадров НЕ СУЩЕСТВУЕТ
5. Проверка через `99_Self_Correction.txt` — обязательна
6. Запрещённые слова — проверять по `22_Social_Forbidden_And_Safety.txt`
7. Safe zone — проверять по `16B_Social_Platform_Specs.txt`
8. Banana-промпты — СТРОГО по формуле «Слоёный пирог» из `03_Tech_Banana.txt`
9. Veo 3 промпты — СТРОГО по формуле из `02B_Tech_Veo_Shorts.txt`
10. Style tags — ТОЛЬКО из `10_Style_Matrix.txt`
11. **🔴 JSON ВСЕГДА ПЕРВЫМ — до любого Markdown текста**
12. **🔴 `path` в key_frames и thumbnail оставлять `null` — система заполнит**
13. **🔴 worker_id в коде = A-нотация (A01–A05). В промптах — T-имена (T1 Стелла и т.д.)**

---

## 10. PROJECT ID

Формат: `TURBO_YYYYMMDD_XXX`
- YYYYMMDD = дата создания
- XXX = порядковый номер за день (001, 002...)

Задаёт T1 Стелла (A01), наследуется всеми.
Ключ в chain_data: `stella_strategy.project_id`

---

## 11. СТАТУСЫ

| Статус | Агент (имя / worker_id) | Значение |
|--------|------------------------|----------|
| `strategy_done` | T1 Стелла / A01 | завершил |
| `sound_done` | T2 Мими / A02 | завершил |
| `visual_done` | T3 Визор / A03 | завершил (кадры сгенерированы) |
| `post-prod_done` | T4 Постпро / A04 | завершил |
| `ready_to_publish` | T5 Финализатор / A05 | пакет готов (обложки + deliverables) |
| `NEEDS_FIX` | — | требуется доработка (указать что) |

---

## 12. MANIFEST.JSON — ЭТАЛОН

```json
{
  "id": "turbo",
  "label": "⚡ TURBO Шортсы",
  "icon": "⚡",
  "version": "2.0",
  "description": "Быстрый конвейер шортсов: A01→(A02∥A03)→A04→A05",
  "run_type": "turbo",
  "phases": {
    "TURBO": ["A01","A02","A03","A04","A05"]
  },
  "turbo_workers": ["A01","A02","A03","A04","A05"],
  "turbo_parallel": [["A02","A03"]],
  "checkpoint_after": [],
  "stop_after": null,
  "revision_loop": null,
  "conflict_mode": "divergent",
  "qa_agent": "A05",
  "interaction_log": "economy/data/interaction_log_turbo.jsonl",
  "memory_layers": ["personal","project","runtime","interaction"]
}
```

---

## 13. АРХИТЕКТУРА ПАМЯТИ (v3.1)

Четыре слоя — стандарт студии:

```
Personal    → dna.json
              sensory/sensory_memory.json
              resonance/emotional_weights.json  ← отношения к коллегам
              resonance/event_log.json          ← значимые события (Loka-Filter)
              core/anchors.json
Project     → final_dna (A05 пишет в chain_data)
Runtime     → chain_data (передаётся A01→A05)
Interaction → studio/economy/data/interaction_log_turbo.jsonl
```

Что пишется автоматически после каждого рана:
- `sensory_memory.json` каждого агента — рабочее событие
- `interaction_log_turbo.jsonl` — передача данных между агентами
- `dna.json` — Stress/Internal_Light через `sync_to_dna()`
- `profile_vector` в `dna.json` — Character Drift при score ≥ 0.8

quality_score считается по `my_output` (не `deliverables`):
- my_output есть, нет галлюцинаций → 0.8 (good_work)
- my_output есть, есть галлюцинации → 0.5 (нейтрально)
- нет my_output → 0.3 (bad_work)

---

## 14. СРАВНЕНИЕ ВЕРСИЙ

| Параметр | v2.0 | v3.0 | v3.1 |
|----------|------|------|------|
| Модель генерации | Nano Banana | Nano Banana 2 | Nano Banana 2 |
| Генерация кадров | Вручную | Авто (hooks.py) | Авто (hooks.py) |
| Генерация обложек | Вручную | Авто (hooks.py) | Авто (hooks.py) |
| Порядок вывода | MD → JSON | JSON → MD | JSON → MD |
| `path` в JSON | Отсутствовал | `null` | `null` |
| worker_id хуков | — | T3/T5 ❌ | A03/A05 ✅ |
| agent_id биллинга | — | T3/T5 ❌ | A03/A05 ✅ |
| Gemini QA | — | ✅ | ✅ |
| Ретраи | — | до 5 | до 5 |
| qa_agent | — | T5 ❌ | A05 ✅ |
| Двойная нотация | — | не задокументирована | ✅ явно |
| resonance-файлы | — | resonance_log ❌ | event_log ✅ |
| manifest v2.0 | — | ✅ | ✅ |

---

*Студия "Шесть пальцев" | Версия 3.1 | 2026-05-16*
*A-нотация в системе, T-имена в промптах. hooks.py v3.2. Manifest v2.0.*
