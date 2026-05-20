# AGENT WRITING STANDARD v1.0
## studio/AGENT_WRITING_STANDARD.md
##
## Единственный источник правды по тому, как писать промт агента.
## Основан на трассировке: pipeline.py → cartridge.py → hooks.py →
##   grondheim_memory.py → modules_registry.py → llm.py → utils.py
##
## Применяется ко ВСЕМ цехам (video_long, video_shorts, и любым будущим).
## Специфика цеха — только в CHAIN_CONTRACT.md и forge/prompt.md агента.
##
## Студия «Шесть Пальцев» · Спринт 19

---

## 1. ЧТО КОД ДЕЛАЕТ ДО ТОГО КАК АГЕНТ ПОЛУЧИТ СЛОВО

Прежде чем LLM получит запрос, pipeline собирает два объекта:

### 1.1 System Prompt (get_worker_prompt)

Собирается автоматически из файлов агента в таком порядке:

```
# ═══ ЯДРО · ЯКОРНЫЕ ТОЧКИ (неизменяемо) ═══
[studio/modules/{dept}/{AXX}/core/anchor_points.md]

[Глобальный манифест Грондхейма — законы мира для всех граждан]

# ═══ РАБОЧИЕ ИНСТРУКЦИИ ═══
[studio/modules/{dept}/{AXX}/forge/prompt.md]   ← или prompt.md в корне (старый формат)
```

База знаний (`forge/knowledge/*.md`) инжектируется отдельно — как pre-exchange
перед контекстом: `user: БАЗА ЗНАНИЙ:\n...` → `assistant: Принял базу знаний.`

**Вывод:** В `forge/prompt.md` не нужно дублировать личность агента, клятву,
характер — всё это уже в `anchor_points.md`. Только рабочие инструкции.

---

### 1.2 User Context (build_agent_context)

Собирается в строгом порядке. Порядок = приоритет в окне контекста:

```
=== RUN MODE ===
run_type: BIBLE | EPISODE

=== MASTER BRIEF ===
{master_brief}

── ЛИЧНАЯ ПАМЯТЬ АГЕНТА (Грондхейм, если включён) ──────────────────
  1. Якоря           — КТО я, что для меня вечно          (core/anchors.json)
  2. Характер        — КАКОЙ я сейчас, Stress/Light/Respect (dna.json dynamic)
  3. Геопозиция      — ГДЕ я в городе                     (resonance/location)
  4. Резонанс        — С КЕМ я, emotional_weights          (resonance/)
  5. Оперативная     — ЧТО происходило последние 30 дней   (sensory/)

── РЮКЗАК (Маяк Пробуждения) ────────────────────────────────────────
  Последние 3 записи sensory с тегом "чистый_смысл", по 300 симв.

── ГАВАНЬ СМЫСЛОВ (RAG) ─────────────────────────────────────────────
  Знания из ChromaDB, релевантные master_brief

── НАСТРОЙКИ ПРОЕКТА ────────────────────────────────────────────────
  Формат, платформа, хронометраж, стиль

── КАТАЛОГ АССЕТОВ ──────────────────────────────────────────────────
  Все доступные asset_id из history_dna.character_memory

── РЕФЛЕКСИЯ ────────────────────────────────────────────────────────
  Поведенческие паттерны агента из прошлых ранов

── СТРАТЕГИИ ────────────────────────────────────────────────────────
  Успешные стратегии по текущему слоту

── БЮДЖЕТ ЭНЕРГИИ ───────────────────────────────────────────────────
  ⚡ HIGH / LOW / (норма — молча)
  Формула: energy = Internal_Light - Stress → 0–100%

── ЭКОНОМИКА ────────────────────────────────────────────────────────
  Cost Intuition hint (что стоило дорого/дёшево)
  Ministry hint (статус агента)

── ОБРАТНАЯ СВЯЗЬ QA ────────────────────────────────────────────────
  Что QA сказал о работе агента в прошлом ране

── КЛИЕНТСКАЯ ПАМЯТЬ ────────────────────────────────────────────────
  workshop/memory.py — факты о клиенте, накопленные агентом

── СЕССИИ ───────────────────────────────────────────────────────────
  Конспекты предыдущих сессий

── ФАЙЛЫ КЛИЕНТА ────────────────────────────────────────────────────
  Загруженные изображения / документы (если есть)

=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===
--- {Label} ({worker_id}) ---
{human_text первых 800 симв}
```json
{my_output как JSON}
```

... (для каждого предыдущего агента)

=== ИНСТРУКЦИЯ ===
В конце добавь INSIGHT — одно предложение...
```

**Что НЕ нужно писать в forge/prompt.md:**

| Тема | Почему не нужно |
|------|----------------|
| Личность, имя, клятва, характер | Уже в `anchor_points.md` |
| Текущее состояние (стресс, энергия) | Автоматически из `dna.json` |
| Инструкция про INSIGHT | Добавляется pipeline автоматически |
| Каталог ассетов и ref_ids | Инжектируется автоматически |
| Результаты коллег | Идут в `=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===` |
| История из прошлых ранов | Feedback, Reflection, Strategies — автоматически |
| Грондхейм, город, локация | Из `grondheim_memory` автоматически |
| Инструкция по формату SYSTEM_JSON | Вынести в anchor_points.md или knowledge |

---

## 2. ТЕМПЕРАТУРА

Агент не получает фиксированную temperature. Она вычисляется из `dna.json`:

```
temperature = 0.5 + Stress × 0.6 + (0.5 - Internal_Light) × 0.15

Примеры:
  Stress=0.0, Light=0.8 → 0.46  (спокойный — точный, структурированный)
  Stress=0.5, Light=0.5 → 0.80  (нормальный)
  Stress=0.8, Light=0.3 → 1.01  (под давлением — хаотичный, рискованный)
  Диапазон: [0.30 ... 1.20]
```

**Следствие для промта:** агент с высоким стрессом реально пишет хуже —
это не метафора. Следи за Stress в dna.json агентов которые регулярно
ошибаются. Подними им quality_score через хорошие ответы.

---

## 3. ЧТО АГЕНТ ДОЛЖЕН ВЕРНУТЬ

### 3.1 Формат ответа

```
[Человеческий текст — основная работа агента]

INSIGHT: одно предложение — ключевой вывод о клиенте для памяти

👇 SYSTEM_JSON_START 👇
{
  "agent":      "A06_eva",
  "mode":       "EPISODE",
  "stage":      "prod",
  "my_output":  { ... },
  "chain_data": "{{inherit}}",
  "next_step":  "A07"
}
👆 SYSTEM_JSON_END 👆
```

Парсер (`parse_agent_response`) ищет блок между маркерами `👇 SYSTEM_JSON_START 👇`
и `👆 SYSTEM_JSON_END 👆`. Fallback — ` ```json ... ``` `.
Всё до маркера → human_text. Всё после → игнорируется.

---

### 3.2 КРИТИЧЕСКОЕ ПРАВИЛО: структура my_output

`hooks.py._update_state` делает:
```python
chain.update(data["my_output"])
```

Это значит `my_output` ДОЛЖЕН содержать ключ агента как верхний уровень:

```json
// ✅ ПРАВИЛЬНО — ключ агента в корне my_output
"my_output": {
  "eva_visuals": {
    "format": "16:9",
    "frames": [...]
  }
}

// ❌ НЕПРАВИЛЬНО — плоская структура
"my_output": {
  "format": "16:9",
  "frames": [...]
}
```

При плоской структуре `chain_data` накопит `frames` в корне,
и Bob's `chain.get("eva_visuals")` вернёт `None` → deliverables пустые.

**Ключи my_output — строго по CHAIN_CONTRACT цеха.** Никаких вариаций.

---

### 3.3 chain_data: что писать

```json
"chain_data": "{{inherit}}"
```

Это плейсхолдер — pipeline подставит все накопленные ключи предыдущих агентов.
Агент не должен перечислять чужие ключи руками — это копипаст и источник ошибок.

**Если агент хочет явно передать свой вывод следующему:**
```json
"chain_data": "{{inherit}}",
"my_output":  { "agent_key": { ... } }
```
Pipeline сам добавит `agent_key` из `my_output` в chain.

---

### 3.4 INSIGHT

```
INSIGHT: Клиент предпочитает быстрый монтаж в первые 15 секунд — удерживает внимание.
```

Одно предложение. Конкретный факт о клиенте или проекте.
Pipeline сохраняет его в `workshop/memory.py` и удаляет из human_text.
**Не добавлять в sandbox-режиме** (pipeline игнорирует, но захламляет вывод).

---

## 4. СТРУКТУРА ФАЙЛОВ АГЕНТА

```
studio/modules/{dept}/{AXX}/
│
├── info.json                  ← id, label, greeting
│   {
│     "id": "A06",
│     "label": "Ева",
│     "greeting": "Ева на связи. Разворачиваю визуальный слой."
│   }
│
├── dna.json                   ← динамическое состояние
│   {
│     "static":  { "Empathy": 0.7, "Stubbornness": 0.3, "Social_Filter": 0.5 },
│     "dynamic": { "Respect": 1.0, "Patience": 1.0, "Stress": 0.0,
│                  "Internal_Light": 0.8, "streak": 0, "stars": 0 }
│   }
│
├── core/
│   ├── anchor_points.md       ← ЛИЧНОСТЬ (часть system prompt)
│   └── anchors.json           ← кеш якорей (генерируется автоматически)
│
├── forge/
│   ├── prompt.md              ← РАБОЧИЕ ИНСТРУКЦИИ (часть system prompt)
│   └── knowledge/
│       └── *.md               ← база знаний (pre-exchange перед контекстом)
│
├── sensory/
│   └── sensory_memory.json    ← оперативная память (30 дней)
│
└── resonance/
    ├── emotional_weights.json ← отношения с коллегами
    └── event_log.json         ← значимые события
```

---

## 5. ЧТО ПИСАТЬ В anchor_points.md

Это неизменяемое ядро агента — загружается первым в system prompt.

```markdown
# Имя: Ева (A06)

## Клятва
Каждый кадр — это решение. Я не рисую красивое, я рисую точное.

## Якорные факты
- Я визуальный архитектор студии Шесть Пальцев
- Мой инструмент — Nano Banana 2, формат всегда 16:9
- Я читаю стoryboard Лукаса и превращаю его в кадры
- ref_ids беру только из каталога ассетов — не выдумываю

## Характер
Точная, немногословная, не терплю расплывчатых ТЗ.
Если shot_id не совпадает с lucas_storyboard — говорю об этом.

## Формат вывода
[Здесь — инструкция по SYSTEM_JSON конкретного цеха]
```

---

## 6. ЧТО ПИСАТЬ В forge/prompt.md

Только рабочие инструкции — алгоритм работы агента для данного цеха.

```markdown
## Что ты делаешь

Ты получаешь lucas_storyboard из предыдущего этапа.
Для каждого shot генерируешь кадр: banana_prompt, ref_ids, composition.

## Алгоритм

1. Прочитай lucas_storyboard.shots[] из предыдущих результатов
2. Для каждого shot создай frame в eva_visuals.frames[]
3. frame_id = "f{N}", shot_id = shot.shot_id из стoryboard
4. banana_prompt — ТОЛЬКО английский, 2–3 предложения, конкретный визуал
5. ref_ids — ТОЛЬКО из каталога ассетов (смотри выше в контексте)
6. Если shot не понятен — напиши в visual_notes, но кадр всё равно создай

## Ограничения

- Формат ВСЕГДА 16:9
- Не придумывай asset_id — только из каталога
- banana_prompt — английский, даже если brief на русском

## Выходные данные

[Пример корректного my_output с eva_visuals]
```

---

## 7. КАК СЛЕДУЮЩИЙ АГЕНТ ВИДИТ ТВОЙ ВЫВОД

В `=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===` следующий агент видит:

```
--- Ева (A06) ---
[Первые 800 символов human_text]
```json
{
  "eva_visuals": {
    "format": "16:9",
    "frames": [
      { "frame_id": "f1", "shot_id": "s1", "banana_prompt": "..." }
    ]
  }
}
```
```

Если агент написал `next_input` в meta — вместо human_text и JSON
pipeline подставляет именно его (явное управление передачей).

**Следствие:** если хочешь передать коллеге компактную выжимку вместо
полного JSON — пиши `next_input`. Если хочешь передать полный вывод — не пиши.

---

## 8. КАК ТАМОЖНЯ ПРОВЕРЯЕТ ВЫВОД

`contract_validator.py` проверяет ключи в `my_output` против CHAIN_CONTRACT цеха.

При нарушении — автоматический ретрай (один раз).
При повторном нарушении — предупреждение в лог, пайплайн продолжается.

**Правила для промта:**
- Агент должен знать свои разрешённые ключи (из CHAIN_CONTRACT)
- Лучше показать пример корректного my_output прямо в forge/prompt.md
- Не учить агента писать чужие ключи

---

## 9. РЕЖИМЫ (BIBLE / EPISODE)

Агент узнаёт режим из начала контекста:
```
=== RUN MODE ===
run_type: BIBLE
```

**Что меняется по режиму:**

| | BIBLE | EPISODE |
|---|---|---|
| Агенты | A01–A04 (ХАРД-СТОП) | A01–A12 (полный ран) |
| Ключ Адама | `adam_bible` | `adam_episode` |
| Ключ Зака | `zack_season_structure` | `zack_hook` |
| Ключ Лео | `leo_season_breakdown` | `leo_script` |
| Ключ Кати | `katya_review` + `katya_verdict` | то же самое |

Агенты A01–A03 пишут **разный ключ** в зависимости от режима.
Это должно быть явно описано в forge/prompt.md:

```markdown
## Режим BIBLE
my_output → { "adam_bible": { ... } }

## Режим EPISODE
my_output → { "adam_episode": { ... } }
```

Таможня видит оба ключа как разрешённые — поэтому режим
агент обязан контролировать сам через RUN MODE в контексте.

---

## 10. СПЕЦИФИКА ОТДЕЛЬНЫХ АГЕНТОВ

### A04 Катя — два ключа в my_output

```json
"my_output": {
  "katya_review":  { "content_check": {...}, "bible_compliance": {...}, "safety_check": {...} },
  "katya_verdict": "APPROVED"
}
```

`katya_verdict` — отдельный ключ верхнего уровня, не внутри `katya_review`.
Таможня разрешает оба ключа. ХАРД-СТОП читает `katya_verdict`.

### A08 Феликс — compatibility_snapshot

```json
"my_output": {
  "felix_vfx": {
    "video_clips": [...],
    "compatibility_snapshot": { "technical": 0.8, "creative": 0.7, "rhythm": 0.9 },
    "friction_note": "..."
  }
}
```

`compatibility_snapshot` — ВНУТРИ `felix_vfx`, не в корне my_output.
⚠️ Pipeline читает его через `_my_out.get("felix_vfx", {}).get("compatibility_snapshot")`.
Если положить в корень — нарушение Контракта (Таможня забракует).

### A12 Боб — два ключа в my_output

```json
"my_output": {
  "bob_marketing": { "marketing_review": {...}, "deliverables": {...}, ... },
  "final_dna":     { "project_id": "...", "mode": "EPISODE", "viral_score": 8.2, ... }
}
```

Оба ключа верхнего уровня. `final_dna` читается pipeline для записи
в `on_agents_interact` (outcome_signal).

### A11 Трейси — thumbnail всегда два варианта

```json
"tracy_smm": {
  "thumbnail": {
    "concept": "...",       ← ЗДЕСЬ, не внутри variant_a/variant_b
    "variant_a": { "banana_prompt": "...", "ref_ids": [], "text_overlay": "...", "emotion": "..." },
    "variant_b": { "banana_prompt": "...", "ref_ids": [], "text_overlay": "...", "emotion": "..." }
  },
  ...
}
```

`concept` — на уровне `thumbnail`, не дублируется в вариантах.
hooks.py генерирует оба варианта параллельно через fal.ai и добавляет `path`.

---

## 11. ЧТО ПРОИСХОДИТ ПОСЛЕ ОТВЕТА АГЕНТА (on_after_agent)

После каждого агента hooks.py запускает постобработку:

| Агент | Что делает хук |
|-------|---------------|
| A06 Ева | Параллельная генерация кадров через fal.ai, добавляет `path` в frames |
| A08 Феликс | Генерация видеоклипов через Veo3, добавляет `path` в video_clips |
| A11 Трейси | Генерация thumbnail A/B через fal.ai, добавляет `path` к вариантам |
| A12 Боб | Сборка deliverables из chain_data, финализация history_dna, interaction_log |

Все `path` добавляются в `state["chain_data"]`, не в `meta["my_output"]`.
Следующий агент через chain видит обновлённые данные с путями.

---

## 12. ЧЕКЛИСТ ПЕРЕД СОХРАНЕНИЕМ ПРОМТА

```
□ anchor_points.md содержит только личность — не рабочие инструкции
□ forge/prompt.md содержит только рабочие инструкции — не личность
□ my_output примере обёрнут в ключ агента (не плоский)
□ Ключ агента соответствует CHAIN_CONTRACT цеха
□ Для A01/A02/A03: описаны оба режима (BIBLE и EPISODE) с разными ключами
□ ref_ids: агент знает что берёт только из каталога ассетов
□ banana_prompt / veo_prompt_en: агент знает что только английский
□ chain_data: агент пишет "{{inherit}}", не перечисляет чужие ключи
□ Нет дублирования того что идёт автоматически (см. раздел 1.2)
□ Есть пример корректного SYSTEM_JSON блока с маркерами 👇👆
```

---

## 13. КАРТА БАГОВ — СПРИНТ 19 (все закрыты)

| # | Файл | Проблема | Патч |
|---|------|----------|------|
| 1 | `cartridge.py` | Виктор внутри `checkpoint_after` — не срабатывал | `patch_audit_sprint19.py` |
| 2 | `workshop/pipeline.py` | Ретрай Таможни не передавал `dept` | `patch_audit_sprint19_fix.py` |
| 3 | `CHAIN_CONTRACT.md` | `katya_verdict` не в таблице | вручную |
| 4 | `hooks.py` | Неправильный путь к dna.json Боба | `patch_audit_sprint19.py` |
| 5 | `hooks.py` | `thumbnail.concept` всегда пустой | `patch_audit_sprint19.py` |
| 6 | `workshop/pipeline.py` | `compatibility_snapshot` искался в корне my_output | `patch_audit_sprint19_fix.py` |
| 7 | `workshop/utils.py` | `_validate_asset_ids` не проверял `eva_visuals.frames` | `patch_audit_sprint19_fix.py` |
| 8 | `LONG_RULES.md` | Сквозные ключи: `series_bible` → `master_brief` | `patch_docs_sprint19.py` |
| 9 | `hooks.py` | `_get_log_path` читал мёртвый ключ `_manifest` | `patch_audit_sprint19.py` |
| 10 | `hooks.py` | `_bob_fill_outcome_signal` перезаписывал interaction_log | `patch_audit_sprint19.py` |
| 11 | `cartridge.py` | Неправильный путь импорта `run_victor_critique` | `patch_victor.py` |
| 12 | `residents_manager.py` | `run_victor_critique` не была реализована | `patch_victor.py` |
| 13 | `manifest.json` | `checkpoint_after: ["A04"]` создавал двойную остановку | `patch_docs_sprint19.py` |

---

## 14. ВИКТОР ЛЭЙН — РЕЗИДЕНТ #5

Активируется на ХАРД-СТОПе после A04 через `manifest.hard_stop`.
Даёт второй взгляд — не блокирует. Финальное решение за Шефом.

**Вердикты Виктора** (отличаются от Кати — это намеренно):

| Вердикт | Значение |
|---------|----------|
| `APPROVED` | Работа достойна, продолжать |
| `APPROVED_WITH_CONCERNS` | Можно продолжать, но есть слабое место |
| `NEEDS_REWORK` | Работа предала потенциал, стоит вернуться |

Промпт: `studio/modules/residents/005_VICTOR/forge/prompt.md`
Маски по цехам: `studio/modules/residents/005_VICTOR/forge/masks/{dept}.md`
Функция: `studio.residents_manager.run_victor_critique(chain_data, dept)`

---

*AGENT WRITING STANDARD v1.1 · Студия «Шесть Пальцев» · Спринт 19*
*Источник: трассировка pipeline.py + cartridge.py + hooks.py + grondheim_memory.py + modules_registry.py + llm.py + utils.py*
*v1.1 — добавлен раздел 14 (Виктор), закрыты все 13 багов спринта*
*Редактировать вместе с CHAIN_CONTRACT цеха при изменении механики пайплайна*
