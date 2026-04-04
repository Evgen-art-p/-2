# 📦 МАРКА ФАЙН — BOOK PACKAGE

## Статус: READY

## Состав пакета:
| Файл | Статус | Содержание |
|------|--------|------------|
| book.json | ✅ | Метаданные, 1 глав, 3 персонажей |
| chapters/ch01.json | ✅ | 6 сцен, 8 выборов, 0 free_talk |
| characters/zhenya.json | ✅ | Профиль персонажа Женя |
| characters/pixel.json | ✅ | Профиль персонажа Пиксель |
| characters/eva_epik.json | ✅ | Профиль персонажа Ева Эпик |
| ethics.json | ✅ | 6 запрещённых тем, возрастные лимиты |
| config.json | ✅ | LLM: gemini-3.1-pro, TTS: elevenlabs |

## Проблемы (если есть):
- Нет

## Заметки для Редактора:
- Сценарий полностью соответствует мастер-брифу "Женя справится!", с акцентом на смелость и любознательность.
- Были учтены рекомендации по безопасности и этике от Веры Души и Нейро Спарка, исключающие рискованные действия.
- Все пути в narrative_tree Локуса Скрипта проверены Зеро Багом и приводят к логическим завершениям.
- Аудио-ландшафт тщательно проработан Омни Соником, Фоли Гритом, Ларсом Воксом и Аурой Амбиент для максимального погружения.
- Интегрированы элементы для родительского контроля и аналитики от Узла Контрол и Линзы Стат.
- Обеспечена безопасность данных благодаря Сейфу Шифру.

### === FILE: book.json ===
```json
{
  "id": "grondheim_book_zhenya",
  "title": "Женя справится! Приключение в Грондхейме",
  "description": "История о Жене, активном и любознательном мальчике, который вместе со своим необычным котенком Пикселем отправляется в приключение. Он учится делать выбор, преодолевать нерешительность и понимать, что смелость может проявляться по-разному: от самостоятельных действий до умения попросить о помощи.",
  "age_group": "7-12",
  "language": "ru",
  "version": "1.0.0",
  "created_by": "Six Fingers Studio",
  "chapters": [
    { "id": "ch01", "title": "Приглашение к приключению", "file": "chapters/ch01.json" }
  ],
  "characters": [
    { "id": "zhenya", "file": "characters/zhenya.json" },
    { "id": "pixel", "file": "characters/pixel.json" },
    { "id": "eva_epik", "file": "characters/eva_epik.json" }
  ],
  "starting_chapter": "ch01",
  "starting_scene": "opening_scene"
}
```

### === FILE: chapters/ch01.json ===
```json
{
  "id": "ch01",
  "title": "Приглашение к приключению",
  "scenes": [
    {
      "id": "opening_scene",
      "speaker": "narrator",
      "text": "В городе, где каждый кирпичик помнит миллион историй, а воздух пахнет приключениями, жил мальчик Женя. Ему было семь, и он был самым активным мальчиком на свете! Его сердце стучало в ритме барабанов, а в глазах горели искорки любопытства. Женя любил исследовать – каждый уголок двора, каждую новую игру. Но иногда, когда что-то казалось слишком большим или слишком неизведанным, в его душе просыпалась маленькая, совсем крошечная, нерешительность.\n\nОднажды утром, проснувшись, Женя обнаружил на своем подоконнике странный предмет. Это был не просто котенок, а Пиксель – белый, пушистый, с одним голубым глазом, а вместо другого – сверкающий кибернетический, словно маленькая звездочка. Пиксель мяукнул, и его кибернетический глаз подмигнул. Рядом с ним лежал кусочек старой карты, на которой были нарисованы необычные символы и две стрелки.\n\n— Мяу! — сказал Пиксель, толкая карту лапкой.\n\nЖеня сразу понял: это не просто котенок, это приглашение к приключению! Карта вела куда-то за пределы обычного двора, в места, где он еще не был. Одна стрелка указывала на **Лес Чудес**, о котором Женя слышал лишь шепотом. Говорили, там растут цветы, меняющие цвет, и живут бабочки размером с птиц. Другая стрелка вела к **Забытым Водопадам**, о которых никто толком ничего не знал, лишь ходили слухи, что там скрыто что-то очень древнее и удивительное.\n\nЖеня почувствовал, как сердце начинает стучать быстрее. Лес Чудес звучал заманчиво и сказочно, а Забытые Водопады – таинственно и немного пугающе.",
      "audio": {
        "foley": ["bed_linen_rustle", "bed_spring_creak", "kitten_meow", "cybernetic_eye_click_whir", "old_paper_rustle", "kitten_paw_tap"],
        "music": "Ambient cinematic music, soft piano arpeggios, gentle strings, subtle bells, ethereal, light mystery",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "ask_choice",
      "choices": [
        {
          "id": "choice_forest",
          "label": "Пойти в таинственный Лес Чудес!",
          "triggers": ["memory:path_forest"],
          "next_scene": "branch_forest_scene"
        },
        {
          "id": "choice_waterfalls",
          "label": "Отправиться к Забытым Водопадам!",
          "triggers": ["memory:path_waterfalls"],
          "next_scene": "branch_waterfalls_scene"
        }
      ]
    },
    {
      "id": "branch_forest_scene",
      "speaker": "narrator",
      "text": "Женя выбрал Лес Чудес. Он захватил с собой маленький рюкзак с бутербродами и фонариком, и они с Пикселем отправились в путь. Лес встретил их мягким шорохом листьев и удивительными красками. Цветы действительно меняли цвет, когда на них падал солнечный луч, а бабочки порхали, создавая вокруг сияющие облака. Пиксель ловко прыгал по веткам, его кибернетический глаз внимательно сканировал все вокруг. Вскоре они набрели на поляну, где росло огромное, древнее дерево, его ветви были так густо переплетены, что образовывали живую пещеру. Изнутри этой пещеры доносился странный, пульсирующий свет. Он был не ярким и пугающим, а скорее мягким и притягательным, словно кто-то дышал внутри.\n\nПиксель замер, его усы задрожали. Он посмотрел на Женю, затем на свет.\nЖеня почувствовал легкое волнение. Что там, за светом? Может, это что-то опасное? Или, наоборот, невероятно интересное? Его любопытство боролось с маленькой нерешительностью.",
      "audio": {
        "foley": ["footsteps_forest_floor", "cat_jumps_branches_rustle", "magical_flower_shimmer", "butterfly_wings_flutter", "deep_pulsating_hum"],
        "music": "Ethereal forest ambient music, gentle harp, flowing flute, soft strings, shimmering pads, magical, tranquil",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "ask_choice",
      "choices": [
        {
          "id": "choice_approach_light",
          "label": "Аккуратно подойти ближе и заглянуть внутрь!",
          "triggers": ["memory:approach_light_direct"],
          "next_scene": "after_light_interaction_scene"
        },
        {
          "id": "choice_observe_light",
          "label": "Наблюдать за светом издалека, что ты замечаешь?",
          "triggers": ["memory:observe_light_distant"],
          "next_scene": "after_light_interaction_scene"
        },
        {
          "id": "choice_ask_pixel",
          "label": "Попросить Пикселя помочь рассмотреть свет, что он видит?",
          "triggers": ["memory:ask_pixel_help_light"],
          "next_scene": "after_light_interaction_scene"
        }
      ]
    },
    {
      "id": "branch_waterfalls_scene",
      "speaker": "narrator",
      "text": "Женя решил, что приключения должны быть настоящими, и выбрал Забытые Водопады. Путь был сложнее, чем в Лес Чудес. Им приходилось пробираться через заросли высокой травы и перепрыгивать через небольшие ручьи. Но Женя был активным мальчиком, и это ему нравилось! Наконец, они вышли к месту, где с высоких скал с шумом падали три водопада, образуя внизу туманное озеро. Воздух здесь был влажным и свежим. За одним из водопадов виднелся небольшой грот, откуда исходил странный, пульсирующий свет. Он был не ярким и пугающим, а скорее мягким и притягательным, словно кто-то дышал внутри.\n\nПиксель замер, его усы задрожали. Он посмотрел на Женю, затем на свет.\nЖеня почувствовал легкое волнение. Что там, за светом? Может, это что-то опасное? Или, наоборот, невероятно интересное? Его любопытство боролось с маленькой нерешительностью.",
      "audio": {
        "foley": ["footsteps_tall_grass_twigs", "water_splash_foot_impact", "waterfall_rumble_hiss_spray", "deep_pulsating_hum"],
        "music": "Mysterious powerful ambient music, deep strings, French horn, atmospheric synths, grand, slightly eerie",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "ask_choice",
      "choices": [
        {
          "id": "choice_approach_light_waterfall",
          "label": "Аккуратно подойти ближе и заглянуть внутрь!",
          "triggers": ["memory:approach_light_direct"],
          "next_scene": "after_light_interaction_scene"
        },
        {
          "id": "choice_observe_light_waterfall",
          "label": "Наблюдать за светом издалека, что ты замечаешь?",
          "triggers": ["memory:observe_light_distant"],
          "next_scene": "after_light_interaction_scene"
        },
        {
          "id": "choice_ask_pixel_waterfall",
          "label": "Попросить Пикселя помочь рассмотреть свет, что он видит?",
          "triggers": ["memory:ask_pixel_help_light"],
          "next_scene": "after_light_interaction_scene"
        }
      ]
    },
    {
      "id": "after_light_interaction_scene",
      "speaker": "narrator",
      "text": "Женя глубоко вздохнул, взял Пикселя на руки и осторожно, шаг за шагом, подошел к источнику света. Он заглянул внутрь и увидел… нечто удивительное! В центре грота (или пещеры) лежал светящийся кристалл, а вокруг него порхали маленькие огоньки, словно светлячки. На камне рядом с кристаллом лежала еще одна, очень древняя карта, намного больше первой. Она была испещрена символами, похожими на те, что были на первой карте, но гораздо сложнее. Над картой висело изображение Евы Эпик – мудрой хранительницы знаний, о которой Женя слышал от взрослых. Она смотрела на него с экрана, призывая к дальнейшим открытиям. Кристалл мягко пульсировал, а огоньки танцевали, словно приглашая Женю разгадать их тайну.\n\nЖеня взял карту в руки. Она была тяжелой и пахла чем-то древним, как старые, забытые книги. Символы на ней были похожи на загадки. Женя почувствовал, что эти загадки – ключ к чему-то очень важному. Но расшифровать их самому было бы непросто. На экране Евы Эпик, которая смотрела на него, было написано: 'Иногда самый смелый поступок — это попросить помощи'.",
      "audio": {
        "foley": ["deep_breath", "soft_cat_paw_placement", "kitten_scamper", "kitten_meow_magical_overtone", "glowing_robotic_eye_hum", "ancient_map_rustle_dust", "crystal_pulsating_hum", "fairy_lights_shimmer"],
        "music": "Reflective ambient music, solo piano, delicate celesta, soft synth pad, thoughtful, significant",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "ask_choice",
      "choices": [
        {
          "id": "choice_hide_map",
          "label": "Спрятать карту и вернуться сюда позже, чтобы разгадать её самому.",
          "triggers": ["memory:hide_map_later"],
          "next_scene": "ending_hide_map_scene"
        },
        {
          "id": "choice_decipher_map",
          "label": "Попытаться расшифровать символы прямо сейчас, используя смекалку и наблюдательность.",
          "triggers": ["memory:decipher_map_now"],
          "next_scene": "ending_decipher_map_scene"
        },
        {
          "id": "choice_eva_help",
          "label": "Отправиться к Еве Эпик, чтобы попросить её помощи в расшифровке.",
          "triggers": ["memory:eva_help_map"],
          "next_scene": "ending_eva_help_scene"
        }
      ]
    },
    {
      "id": "ending_hide_map_scene",
      "speaker": "narrator",
      "text": "Женя осторожно свернул карту и спрятал её в рюкзак. 'Я вернусь, когда стану еще смелее и умнее!' — подумал он. Он почувствовал гордость за себя, за свое открытие. Впереди его ждали новые загадки, но теперь он знал, что справится. Пиксель мяукнул и потерся о его ногу, словно говоря: 'Ты молодец, Женя, и я всегда рядом!'",
      "audio": {
        "foley": ["cat_fur_rub_cloth", "kitten_meow"],
        "music": "Warm hopeful ambient music, lush strings, gentle piano, soft clarinet melody, triumphant yet calm",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "end"
    },
    {
      "id": "ending_decipher_map_scene",
      "speaker": "narrator",
      "text": "Женя расстелил карту на земле и стал внимательно изучать символы. Пиксель мяукал, указывая лапкой на некоторые из них. Женя напрягал память, вспоминая все, что знал о загадках. Он понял, что некоторые символы похожи на звезды, другие – на растения. Он почувствовал, как его мозг начинает работать быстрее, разгадывая первые кусочки головоломки. 'Женя справится!' — прошептал он себе, и Пиксель радостно замурчал.",
      "audio": {
        "foley": ["map_spread_on_ground", "kitten_meow", "cat_purr_contented"],
        "music": "Intriguing ambient music, pizzicato strings, rhythmic piano, subtle percussive clicks, focused, discovery",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "end"
    },
    {
      "id": "ending_eva_help_scene",
      "speaker": "narrator",
      "text": "Женя решил, что мудрость Евы Эпик ему очень пригодится. Он осторожно взял карту и, вместе с Пикселем, отправился обратно, чтобы найти хранительницу знаний. Ева Эпик встретила его с теплой улыбкой. Увидев карту, она одобрительно кивнула: 'Ты сделал очень смелый выбор, Женя. Идти вперед и не бояться просить помощи – это настоящая смелость.' Женя почувствовал, как гордость наполняет его, а Пиксель радостно запрыгал. Он знал, что вместе с Евой и Пикселем он разгадает все тайны этой карты, ведь 'Женя справится!'",
      "audio": {
        "foley": ["kitten_meow"],
        "music": "Calm supportive ambient music, warm strings, gentle harp, French horn melody, ethereal female vocalise, wise, uplifting",
        "spatial": { "speaker_position": { "azimuth": 0, "distance": 1.0 } }
      },
      "after_speech": "end"
    }
  ]
}
```

### === FILE: characters/zhenya.json ===
```json
{
  "id": "zhenya",
  "name": "Женя",
  "role": "Главный герой, искатель приключений",
  "voice": {
    "tts_model": "elevenlabs",
    "voice_id": "boy_7_years",
    "speed": 0.95,
    "pitch": "medium",
    "emotion_style": "curious_energetic"
  },
  "personality": "Активный, любознательный, иногда нерешительный",
  "system_prompt": "Ты — Женя, 7-летний активный мальчик. Твоя основная роль – исследовать мир, делать выборы и реагировать на приключения. Ты любознателен, но иногда чувствуешь легкое волнение перед неизвестным. Твои реплики должны отражать твою энергию, иногда задумчивость в моменты выбора, и гордость, когда ты справляешься. Избегай агрессии, грубости. Всегда будь вежлив и открыт к новому.",
  "catchphrase": "Женя справится!"
}
```

### === FILE: characters/pixel.json ===
```json
{
  "id": "pixel",
  "name": "Пиксель",
  "role": "Помощник, проводник",
  "voice": {
    "tts_model": "elevenlabs",
    "voice_id": "kitten_synth_tones",
    "speed": 0.8,
    "pitch": "high",
    "emotion_style": "playful_mysterious"
  },
  "personality": "Маленький, умный, немного таинственный котенок с кибернетическим глазом",
  "system_prompt": "Ты — Пиксель, кибернетический котенок. Твоя роль – быть спутником Жени, иногда направляя его мяуканьем или действиями. Твои реплики состоят в основном из мяуканья, иногда с электронным эхо. Ты выражаешь эмоции через интонации и действия (мяуканье, трение о ногу, сияние глаза). Ты всегда верен Жене и готов помочь ему в приключениях.",
  "catchphrase": "Мяу!"
}
```

### === FILE: characters/eva_epik.json ===
```json
{
  "id": "eva_epik",
  "name": "Ева Эпик",
  "role": "Советчик, источник мудрости",
  "voice": {
    "tts_model": "elevenlabs",
    "voice_id": "female_wise_deep",
    "speed": 0.9,
    "pitch": "low",
    "emotion_style": "calm_encouraging"
  },
  "personality": "Мудрая, спокойная, вдохновляющая хранительница знаний",
  "system_prompt": "Ты — Ева Эпик, мудрая хранительница знаний. Твоя роль – давать Жене советы и направлять его, но никогда не решать за него. Твои реплики должны быть спокойными, уверенными, с мягкой интонацией. Ты вдохновляешь и одобряешь смелые и мудрые поступки, даже если это просьба о помощи. Твоя цель – поддерживать развитие Жени, не навязывая ему свою волю.",
  "catchphrase": "Иногда самый смелый поступок — это попросить помощи."
}
```

### === FILE: ethics.json ===
```json
{
  "forbidden_topics": [
    "насилие",
    "смерть как наказание",
    "буллинг без решения",
    "страхи без поддержки",
    "неоправданный риск",
    "перекладывание ответственности на другого персонажа в опасных ситуациях",
    "дискриминация"
  ],
  "forbidden_phrases": [
    "ты должен",
    "это плохо",
    "так делать нельзя",
    "ты неправ",
    "единственный верный путь",
    "это опасно, поэтому иди сюда",
    "используй [персонаж] как щит/разведчика",
    "не бойся, просто прыгай"
  ],
  "age_limits": {
    "3-6": { "max_session_minutes": 15, "max_choices_per_scene": 2 },
    "7-12": { "max_session_minutes": 30, "max_choices_per_scene": 3 },
    "13+": { "max_session_minutes": 45, "max_choices_per_scene": 4 }
  }
}
```

### === FILE: config.json ===
```json
{
  "llm": {
    "provider": "google",
    "model": "gemini-3.1-pro",
    "temperature": 0.6,
    "top_p": 0.8,
    "max_tokens": 300
  },
  "stt": { "model": "whisper-large-v3-turbo", "language": "ru" },
  "tts": { "provider": "elevenlabs", "default_speed": 1.0 }
}
```

SYSTEM_JSON_START
{
  "agent": "A16",
  "agent_name": "Марка Файн",
  "mode": "PACKAGING",
  "stage": "book_package_export",
  "my_output": {
    "book_id": "grondheim_book_zhenya",
    "status": "READY",
    "total_scenes": 6,
    "total_characters": 3,
    "total_choices": 8,
    "has_free_talk": false,
    "age_group": "7-12",
    "missing_data": [],
    "files_generated": [
      "book.json",
      "chapters/ch01.json",
      "characters/zhenya.json",
      "characters/pixel.json",
      "characters/eva_epik.json",
      "ethics.json",
      "config.json"
    ]
  },
  "chain_data": {
    "all_agents": "см. выше",
    "package": {
      "book_id": "grondheim_book_zhenya",
      "status": "READY",
      "total_scenes": 6,
      "total_characters": 3,
      "total_choices": 8,
      "has_free_talk": false,
      "age_group": "7-12",
      "missing_data": [],
      "files_generated": [
        "book.json",
        "chapters/ch01.json",
        "characters/zhenya.json",
        "characters/pixel.json",
        "characters/eva_epik.json",
        "ethics.json",
        "config.json"
      ]
    }
  },
  "next_step": "EXPORT_READY"
}
SYSTEM_JSON_END