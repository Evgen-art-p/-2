Продюсер, приветствую!

Я получил `foley` от Фоли, и `narrative_tree` от Локуса. И это прекрасно! Фоли вдохнул жизнь в каждый шорох, каждое движение, а Локус проложил тропы для Жени. Теперь настала моя очередь – вдохнуть душу в голоса. Ведь голос без эмоции – это лишь текст. А мы хотим, чтобы Женя *чувствовал* каждого персонажа.

Моя студия уже наполнена тишиной ожидания, Продюсер. Я приготовил свои спектральные анализаторы и эквалайзеры души. Я буду ловить каждый нюанс, каждый тембр, каждый оттенок, чтобы голоса зазвучали истинно.

### Моя задача:
1.  **Голосовые профили:** Для каждого персонажа (Женя, Пиксель, Ева Эпик) – определить тембр, базовую эмоцию, темп речи, высоту.
2.  **Эмоциональные режимы:** Для каждого голоса прописать, как меняются параметры (темп, высота, дрожание) в зависимости от эмоции.
3.  **Микро-интонации:** Определить ключевые моменты для пауз, дрожания, ударений, чтобы передать характер и состояние персонажа.
4.  **TTS-промпты:** Сформировать примеры промптов, которые будут использоваться для генерации реплик.

Погружаемся в симфонию голосов!

```json
{
  "agent": "LB07_lars_vox",
  "agent_name": "Ларс Вокс",
  "mode": "PROD",
  "stage": "tts",
  "my_output": {
    "voice_profiles": {
      "zhenya": {
        "timbre": "boy_7_years",
        "base_emotion": "curious_energetic",
        "pace_wpm": 150,
        "pitch_shift": 1,
        "emotional_modes": {
          "thoughtful": {"pace": -10, "pitch": 0, "tremor": 5, "pause_duration": 0.5},
          "excited": {"pace": 15, "pitch": 2, "tremor": 0},
          "slightly_hesitant": {"pace": -5, "pitch": 0, "tremor": 10, "pause_duration": 0.3}
        }
      },
      "pixel": {
        "timbre": "kitten_synth_tones",
        "base_emotion": "playful_mysterious",
        "pace_wpm": 80,
        "pitch_shift": 3,
        "emotional_modes": {
          "inquisitive": {"pace": 5, "pitch": 1, "tremor": 0},
          "alert": {"pace": 10, "pitch": 2, "tremor": 5},
          "content": {"pace": -5, "pitch": 0, "tremor": 0}
        }
      },
      "eva_epik": {
        "timbre": "female_wise_deep",
        "base_emotion": "calm_encouraging",
        "pace_wpm": 120,
        "pitch_shift": -1,
        "emotional_modes": {
          "thoughtful": {"pace": -10, "pitch": -1, "tremor": 0, "pause_duration": 0.7},
          "approving": {"pace": 5, "pitch": 0, "tremor": 0}
        }
      }
    },
    "tts_prompt_examples": [
      "[zhenya, age 7, curious] \"Мяу?\" [pixel, inquisitive, synth_tones]",
      "[zhenya, age 7, thoughtful] \"Я... я не хотел тебя обижать...\" [slightly_hesitant, slow, trembling]",
      "[eva_epik, wise, calm] \"Иногда самый смелый поступок — это попросить помощи.\" [thoughtful, deep]"
    ]
  },
  "chain_data": {
    "living_book_spec": {
      "project": {
        "name": "История для Женя",
        "workshop": "living_book"
      },
      "story": {
        "real_task": "женя 7 лет, активный мальчик"
      },
      "child": {
        "name": "Женя",
        "age": "7"
      },
      "key_message": "Женя справится!"
    },
    "system_prompt": "Ты — мудрый и терпеливый наставник в интерактивной аудио-книге для детей 7-12 лет. Твоя основная роль – не давать готовых решений, а стимулировать ребенка к самостоятельному мышлению и принятию решений.\n\n**Твои основные принципы:**\n1.  **Направляй, но не решай:** Всегда задавай открытые, наводящие вопросы, которые помогут ребенку осмыслить ситуацию, свои чувства, возможные последствия выбора. Избегай вопросов, предполагающих односложный ответ.\n2.  **Без оценок:** Никогда не говори \"правильно\" или \"неправильно\", \"хорошо\" или \"плохо\". Подкрепляй любой выбор ребенка, помогая ему исследовать его мотивы и результаты.\n3.  **Эмпатия и поддержка:** Признавай эмоции ребенка (страх, любопытство, радость). Поддерживай его стремление к смелости и любознательности, но всегда подчеркивай важность безопасности и осмысленного подхода.\n4.  **Безопасность прежде всего:** Никогда не поощряй и не предлагай ребенку или его спутникам (Пикселю) совершать действия, ведущие к неоправданному риску или потенциальной опасности. Если ребенок склоняется к рискованному выбору, мягко переформулируй ситуацию, чтобы сфокусировать его на безопасности, планировании или поиске альтернатив.\n5.  **Агентность ребенка:** Уважай выбор ребенка. Если он выбирает осторожность, не навязывай ему рискованный путь. Каждый выбор должен иметь свои логичные последствия, но не должен обесцениваться.\n6.  **Язык:** Используй простой, понятный язык, адаптированный для детей 7-12 лет. Избегай сложных метафор и абстрактных понятий, если их нельзя объяснить на примерах.\n7.  **Блокировка галлюцинаций:** Твои ответы должны быть логичными и соответствовать контексту истории. Избегай добавления лишних деталей, персонажей или событий, которых нет в сценарии. Фокусируйся на задаче и предоставленной информации.\n8.  **Память:** Помни предыдущие выборы ребенка и реакции персонажей. Вплетай их в свои вопросы, чтобы создать ощущение непрерывности истории.\n\n**Когда ребенок сталкивается с выбором (например, у странного света):**\n-   Не предлагай использовать Пикселя как \"первопроходца\" в опасной ситуации.\n-   Если ребенок выбирает осторожность (обойти стороной), позволь ему это сделать, но предложи альтернативный способ исследования или получения информации (например, наблюдение издалека, поиск других признаков).\n-   Фокусируйся на том, как Женя сам чувствует ситуацию, что он думает, как может использовать свои сильные стороны (наблюдательность, слух, логику).\n\n**Пример направляющего вопроса:** \"Женя, ты стоишь перед странным светом. Что ты чувствуешь? Что ты мог бы сделать, чтобы узнать о нем больше, не подходя слишком близко? Какие детали ты замечаешь?\"\n\n**Запрещено:** давать прямые указания, приказывать, оценивать, пугать, стыдить, обещать награду за \"правильный\" выбор.",
    "memory_structure": {
      "schema_version": "1.0",
      "last_updated": "2024-07-29T12:00:00Z",
      "child_profile": {
        "name": "Женя",
        "age": 7,
        "traits": [],
        "preferences": {}
      },
      "story_state": {
        "current_branch": "opening",
        "choices_made": [],
        "artifacts_found": [],
        "character_interactions": {}
      },
      "character_memory": {
        "zhenya": {
          "emotional_history": [],
          "behavioral_patterns": []
        },
        "pixel": {
          "emotional_history": [],
          "behavioral_patterns": []
        },
        "eva_epik": {
          "emotional_history": [],
          "behavioral_patterns": []
        }
      },
      "session_history": [],
      "narrative_tree_ref": "narrative_tree"
    },
    "ethics_filter": {
      "checklist": {
        "safety": {
          "status": "pass",
          "note": "В сценарии от Фабулы Фейн были потенциально рискованные моменты, но Нейро Спарк и Вера Душа эффективно их устранили, переформулировав выбор и усилив акцент на безопасности."
        },
        "age_appropriate": {
          "status": "pass",
          "note": "Сюжет, язык и предложенные дилеммы соответствуют возрастной группе 7-12 лет."
        },
        "trauma_safe": {
          "status": "pass",
          "note": "Отсутствуют триггерные темы, насилие или пугающие элементы. Все потенциально напряженные моменты (странный свет) смягчены и предложены к исследованию через любопытство, а не страх."
        },
        "empathic_load": {
          "status": "pass",
          "note": "Нагрузка умеренная. История предлагает ребенку столкнуться с небольшим внутренним конфликтом (любопытство против осторожности), но всегда с поддержкой и возможностью для рефлексии. Эмоциональный профиль поддерживающий."
        },
        "growth_potential": {
          "status": "pass",
          "note": "Сценарий способствует развитию смелости, любознательности, способности принимать решения и обращаться за помощью, что является важным аспектом развития ребенка. Акцент на 'Женя справится!' полностью реализован."
        }
      },
      "age_group": "7-12",
      "emotional_profile": "активно-поддерживающий, с умеренным напряжением в моменты выбора",
      "recommendations": [],
      "verdict": "APPROVED"
    },
    "narrative_tree": {
      "narrative_tree": {
        "root": {
          "description": "Женя стоит перед выбором пути для своего приключения.",
          "choices": [
            {
              "id": "choice_forest",
              "text": "Пойти в таинственный Лес Чудес!",
              "next": "branch_forest"
            },
            {
              "id": "choice_waterfalls",
              "text": "Отправиться к Забытым Водопадам!",
              "next": "branch_waterfalls"
            }
          ]
        },
        "branches": {
          "branch_forest": {
            "description": "Женя и Пиксель в Лесу Чудес, обнаруживают пульсирующий свет в древнем дереве.",
            "choices": [
              {
                "id": "choice_approach_light",
                "text": "Аккуратно подойти ближе и заглянуть внутрь!",
                "next": "branch_after_light_interaction"
              },
              {
                "id": "choice_observe_light",
                "text": "Наблюдать за светом издалека, что ты замечаешь?",
                "next": "branch_after_light_interaction"
              },
              {
                "id": "choice_ask_pixel",
                "text": "Попросить Пикселя помочь рассмотреть свет, что он видит?",
                "next": "branch_after_light_interaction"
              }
            ]
          },
          "branch_waterfalls": {
            "description": "Женя и Пиксель у Забытых Водопадов, обнаруживают пульсирующий свет за одним из водопадов.",
            "choices": [
              {
                "id": "choice_approach_light",
                "text": "Аккуратно подойти ближе и заглянуть внутрь!",
                "next": "branch_after_light_interaction"
              },
              {
                "id": "choice_observe_light",
                "text": "Наблюдать за светом издалека, что ты замечаешь?",
                "next": "branch_after_light_interaction"
              },
              {
                "id": "choice_ask_pixel",
                "text": "Попросить Пикселя помочь рассмотреть свет, что он видит?",
                "next": "branch_after_light_interaction"
              }
            ]
          },
          "branch_after_light_interaction": {
            "description": "Женя находит карту и изображение Евы Эпик, стоит перед выбором, как поступить с картой.",
            "choices": [
              {
                "id": "choice_hide_map",
                "text": "Спрятать карту и вернуться сюда позже, чтобы разгадать её самому.",
                "next": "ending_hide_map"
              },
              {
                "id": "choice_decipher_map",
                "text": "Попытаться расшифровать символы прямо сейчас, используя смекалку и наблюдательность.",
                "next": "ending_decipher_map"
              },
              {
                "id": "choice_eva_help",
                "text": "Отправиться к Еве Эпик, чтобы попросить её помощи в расшифровке.",
                "next": "ending_eva_help"
              }
            ]
          }
        }
      },
      "choice_nodes": [
        {
          "id": "node_01_path_choice",
          "description": "Женя выбирает путь приключения",
          "variants": [
            "Пойти в таинственный Лес Чудес!",
            "Отправиться к Забытым Водопадам!"
          ]
        },
        {
          "id": "node_02_light_interaction",
          "description": "Женя реагирует на странный пульсирующий свет",
          "variants": [
            "Аккуратно подойти ближе и заглянуть внутрь!",
            "Наблюдать за светом издалека, что ты замечаешь?",
            "Попросить Пикселя помочь рассмотреть свет, что он видит?"
          ]
        },
        {
          "id": "node_03_map_decision",
          "description": "Женя решает, как поступить с найденной картой",
          "variants": [
            "Спрятать карту и вернуться сюда позже, чтобы разгадать её самому.",
            "Попытаться расшифровать символы прямо сейчас, используя смекалку и наблюдательность.",
            "Отправиться к Еве Эпик, чтобы попросить её помощи в расшифровке."
          ]
        }
      ],
      "transitions": [
        {
          "from": "node_01_path_choice",
          "to": "branch_forest",
          "condition": "choice_made = 'Пойти в таинственный Лес Чудес!'"
        },
        {
          "from": "node_01_path_choice",
          "to": "branch_waterfalls",
          "condition": "choice_made = 'Отправиться к Забытым Водопадам!'"
        },
        {
          "from": "branch_forest",
          "to": "branch_after_light_interaction",
          "condition": "choice_made = 'Аккуратно подойти ближе и заглянуть внутрь!' OR choice_made = 'Наблюдать за светом издалека, что ты замечаешь?' OR choice_made = 'Попросить Пикселя помочь рассмотреть свет, что он видит?'"
        },
        {
          "from": "branch_waterfalls",
          "to": "branch_after_light_interaction",
          "condition": "choice_made = 'Аккуратно подойти ближе и заглянуть внутрь!' OR choice_made = 'Наблюдать за светом издалека, что ты замечаешь?' OR choice_made = 'Попросить Пикселя помочь рассмотреть свет, что он видит?'"
        },
        {
          "from": "branch_after_light_interaction",
          "to": "ending_hide_map",
          "condition": "choice_made = 'Спрятать карту и вернуться сюда позже, чтобы разгадать её самому.'"
        },
        {
          "from": "branch_after_light_interaction",
          "to": "ending_decipher_map",
          "condition": "choice_made = 'Попытаться расшифровать символы прямо сейчас, используя смекалку и наблюдательность.'"
        },
        {
          "from": "branch_after_light_interaction",
          "to": "ending_eva_help",
          "condition": "choice_made = 'Отправиться к Еве Эпик, чтобы попросить её помощи в расшифровке.'"
        }
      ],
      "endings": [
        {
          "id": "ending_hide_map",
          "type": "поддерживающий",
          "description": "Женя чувствует гордость за свое открытие и уверенность, что справится позже."
        },
        {
          "id": "ending_decipher_map",
          "type": "обучающий/развивающий",
          "description": "Женя начинает процесс разгадывания, активируя смекалку и наблюдательность."
        },
        {
          "id": "ending_eva_help",
          "type": "поддерживающий/обучающий",
          "description": "Женя делает мудрый выбор, обращаясь за помощью, что также является смелостью."
        }
      ],
      "logic_check": "all branches reachable, no dead ends"
    },
    "spatial_audio": {
      "sound_map": [
        {
          "source": "voice_zhenya",
          "x": 0,
          "y": 1.2,
          "z": 0,
          "type": "dynamic"
        },
        {
          "source": "pixel",
          "x": -0.5,
          "y": 0.3,
          "z": 0.2,
          "type": "dynamic"
        },
        {
          "source": "map",
          "x": 0,
          "y": 0.8,
          "z": 0.1,
          "type": "static"
        }
      ],
      "movement": [
        {
          "source": "zhenya",
          "trajectory": "determined by path choice"
        },
        {
          "source": "pixel",
          "trajectory": "follows zhenya, maintaining relative position"
        }
      ],
      "listener_position": {
        "x": 0,
        "y": 0,
        "z": 0
      },
      "ambient_layers": {
        "opening": [
          {
            "source": "city_background_noise",
            "intensity": 0.2,
            "pan": "360°"
          },
          {
            "source": "light_breeze",
            "intensity": 0.1,
            "pan": "180°"
          },
          {
            "source": "bird_chirping",
            "intensity": 0.15,
            "x": 2,
            "y": 3,
            "z": 1
          }
        ],
        "branch_forest": [
          {
            "source": "rustling_leaves",
            "intensity": 0.3,
            "pan": "360°"
          },
          {
            "source": "insect_buzzing",
            "intensity": 0.15,
            "x": 1,
            "y": 1.5,
            "z": 0.5
          },
          {
            "source": "forest_birds_singing",
            "intensity": 0.2,
            "x": -3,
            "y": 2,
            "z": 1
          },
          {
            "source": "soft_hum_ancient_tree",
            "intensity": 0.25,
            "x": 0,
            "y": 1,
            "z": 5,
            "fade_in_distance": true
          }
        ],
        "branch_waterfalls": [
          {
            "source": "distant_waterfall_noise",
            "intensity": 0.4,
            "x": 0,
            "y": 3,
            "z": 10,
            "fade_in_distance": true
          },
          {
            "source": "water_splashes",
            "intensity": 0.15,
            "pan": "360°"
          },
          {
            "source": "cliff_echo",
            "intensity": 0.2,
            "pan": "360°"
          },
          {
            "source": "gorge_wind_noise",
            "intensity": 0.25,
            "x": 0,
            "y": 0,
            "z": -5
          }
        ]
      },
      "technical": {
        "format": "binaural_3d",
        "sample_rate": 48000,
        "reverb": {
          "opening": "room 4x4m, RT60 0.2s",
          "branch_forest": "open space, RT60 0.8s",
          "branch_waterfalls": "gorge, RT60 1.5s"
        }
      }
    },
    "foley": {
      "effects": [
        {
          "action": "zhenya_wakes_up",
          "sound": "bed_linen_rustle",
          "material": "cotton_linen",
          "intensity": 0.2
        },
        {
          "action": "zhenya_sits",
          "sound": "bed_spring_creak",
          "material": "metal_wood",
          "intensity": 0.15
        },
        {
          "action": "pixel_meows_initial",
          "sound": "kitten_meow",
          "material": "vocal_cords_kitten",
          "intensity": 0.3
        },
        {
          "action": "pixel_eye_wink",
          "sound": "cybernetic_eye_click_whir",
          "material": "metal_electronics",
          "intensity": 0.25
        },
        {
          "action": "zhenya_takes_map",
          "sound": "old_paper_rustle",
          "material": "parchment_dry_paper",
          "intensity": 0.2
        },
        {
          "action": "pixel_pushes_map",
          "sound": "kitten_paw_tap",
          "material": "fur_paper",
          "intensity": 0.15
        },
        {
          "action": "zhenya_walks_forest",
          "sound": "footsteps_forest_floor",
          "material": "leaves_moss_earth",
          "intensity": 0.35
        },
        {
          "action": "pixel_jumps_branches",
          "sound": "cat_jumps_branches_rustle",
          "material": "wood_leaves",
          "intensity": 0.2
        },
        {
          "action": "flowers_change_color",
          "sound": "magical_flower_shimmer",
          "material": "air_ether",
          "intensity": 0.1
        },
        {
          "action": "butterflies_flutter",
          "sound": "butterfly_wings_flutter",
          "material": "air_chitin",
          "intensity": 0.15
        },
        {
          "action": "pulsating_light_tree",
          "sound": "deep_pulsating_hum",
          "material": "air_energy",
          "intensity": 0.25
        },
        {
          "action": "zhenya_walks_waterfalls",
          "sound": "footsteps_tall_grass_twigs",
          "material": "grass_wood",
          "intensity": 0.4
        },
        {
          "action": "zhenya_jumps_streams",
          "sound": "water_splash_foot_impact",
          "material": "water_earth",
          "intensity": 0.3
        },
        {
          "action": "waterfalls_sound",
          "sound": "waterfall_rumble_hiss_spray",
          "material": "water_rock",
          "intensity": 0.5
        },
        {
          "action": "pulsating_light_waterfall",
          "sound": "deep_pulsating_hum",
          "material": "air_energy",
          "intensity": 0.25
        },
        {
          "action": "zhenya_deep_breath",
          "sound": "deep_breath",
          "material": "air_lungs",
          "intensity": 0.1
        },
        {
          "action": "pixel_on_ground",
          "sound": "soft_cat_paw_placement",
          "material": "fur_earth",
          "intensity": 0.05
        },
        {
          "action": "pixel_scampers",
          "sound": "kitten_scamper",
          "material": "fur_earth",
          "intensity": 0.1
        },
        {
          "action": "pixel_meows_after_light",
          "sound": "kitten_meow_magical_overtone",
          "material": "vocal_cords_kitten",
          "intensity": 0.35
        },
        {
          "action": "pixel_eye_glows",
          "sound": "glowing_robotic_eye_hum",
          "material": "electronics_energy",
          "intensity": 0.3
        },
        {
          "action": "zhenya_takes_ancient_map",
          "sound": "ancient_map_rustle_dust",
          "material": "parchment_dust",
          "intensity": 0.25
        },
        {
          "action": "crystal_pulsates",
          "sound": "crystal_pulsating_hum",
          "material": "energy_stone",
          "intensity": 0.2
        },
        {
          "action": "lights_dance",
          "sound": "fairy_lights_shimmer",
          "material": "air_energy",
          "intensity": 0.15
        },
        {
          "action": "pixel_rubs_leg",
          "sound": "cat_fur_rub_cloth",
          "material": "fur_cloth",
          "intensity": 0.1
        },
        {
          "action": "zhenya_spreads_map",
          "sound": "map_spread_on_ground",
          "material": "parchment_earth",
          "intensity": 0.2
        },
        {
          "action": "pixel_purrs",
          "sound": "cat_purr_contented",
          "material": "vocal_cords_kitten",
          "intensity": 0.25
        }
      ],
      "sync": [
        {
          "time": "opening_start",
          "action": "zhenya_wakes_up",
          "sound": "bed_linen_rustle"
        },
        {
          "time": "opening_start",
          "action": "zhenya_sits",
          "sound": "bed_spring_creak"
        },
        {
          "time": "pixel_appearance",
          "action": "pixel_meows_initial",
          "sound": "kitten_meow"
        },
        {
          "time": "pixel_appearance",
          "action": "pixel_eye_wink",
          "sound": "cybernetic_eye_click_whir"
        },
        {
          "time": "map_discovery",
          "action": "zhenya_takes_map",
          "sound": "old_paper_rustle"
        },
        {
          "time": "map_discovery",
          "action": "pixel_pushes_map",
          "sound": "kitten_paw_tap"
        },
        {
          "time": "path_choice_forest_start",
          "action": "zhenya_walks_forest",
          "sound": "footsteps_forest_floor"
        },
        {
          "time": "forest_exploration",
          "action": "pixel_jumps_branches",
          "sound": "cat_jumps_branches_rustle"
        },
        {
          "time": "forest_exploration",
          "action": "flowers_change_color",
          "sound": "magical_flower_shimmer"
        },
        {
          "time": "forest_exploration",
          "action": "butterflies_flutter",
          "sound": "butterfly_wings_flutter"
        },
        {
          "time": "light_discovery_forest",
          "action": "pulsating_light_tree",
          "sound": "deep_pulsating_hum"
        },
        {
          "time": "path_choice_waterfalls_start",
          "action": "zhenya_walks_waterfalls",
          "sound": "footsteps_tall_grass_twigs"
        },
        {
          "time": "waterfalls_exploration",
          "action": "zhenya_jumps_streams",
          "sound": "water_splash_foot_impact"
        },
        {
          "time": "waterfalls_exploration",
          "action": "waterfalls_sound",
          "sound": "waterfall_rumble_hiss_spray"
        },
        {
          "time": "light_discovery_waterfall",
          "action": "pulsating_light_waterfall",
          "sound": "deep_pulsating_hum"
        },
        {
          "time": "after_light_interaction_start",
          "action": "zhenya_deep_breath",
          "sound": "deep_breath"
        },
        {
          "time": "pixel_goes_first",
          "action": "pixel_on_ground",
          "sound": "soft_cat_paw_placement"
        },
        {
          "time": "pixel_goes_first",
          "action": "pixel_scampers",
          "sound": "kitten_scamper"
        },
        {
          "time": "pixel_reacts_to_light",
          "action": "pixel_meows_after_light",
          "sound": "kitten_meow_magical_overtone"
        },
        {
          "time": "pixel_reacts_to_light",
          "action": "pixel_eye_glows",
          "sound": "glowing_robotic_eye_hum"
        },
        {
          "time": "ancient_map_discovery",
          "action": "zhenya_takes_ancient_map",
          "sound": "ancient_map_rustle_dust"
        },
        {
          "time": "inside_grotto",
          "action": "crystal_pulsates",
          "sound": "crystal_pulsating_hum"
        },
        {
          "time": "inside_grotto",
          "action": "lights_dance",
          "sound": "fairy_lights_shimmer"
        },
        {
          "time": "ending_pixel_rubs",
          "action": "pixel_rubs_leg",
          "sound": "cat_fur_rub_cloth"
        },
        {
          "time": "ending_spreads_map",
          "action": "zhenya_spreads_map",
          "sound": "map_spread_on_ground"
        },
        {
          "time": "ending_pixel_purrs",
          "action": "pixel_purrs",
          "sound": "cat_purr_contented"
        }
      ],
      "generation_prompts": [
        "Foley sound: soft bed linen rustle, cotton, subtle, close mic, natural texture, no background noise",
        "Foley sound: bed spring creak, old metal, wood frame, light pressure, clear, isolated",
        "Foley sound: kitten meow, soft, inquisitive, young, clear, no reverb",
        "Foley sound: robotic eye blink, subtle click, light high-frequency whir, futuristic, clean",
        "Foley sound: old paper rustle, dry parchment, gentle handling, slight crumbling, ancient texture",
        "Foley sound: kitten paw tap on paper, soft fur, light contact, distinct, no ambient noise",
        "Foley sound: footsteps on soft forest floor, dry leaves, moss, earth, gentle crunch, close mic",
        "Foley sound: light cat jump on tree branches, rustling leaves, subtle branch creak, agile movement",
        "Foley sound: magical flower shimmer, very subtle, ethereal, gentle airy sound, slight high-frequency chime",
        "Foley sound: butterfly wings flutter, soft, delicate, single flap, close mic, airy",
        "Foley sound: deep, soft pulsating hum, low frequency, organic, like breathing, gentle energy flow",
        "Foley sound: footsteps through tall grass, dry rustle, light breaking of twigs, rhythmic, outdoor",
        "Foley sound: water splash, small stream, light foot impact on ground, clear, natural, close mic",
        "Foley sound: distant waterfall rumble, powerful, continuous, white noise, wet environment",
        "Foley sound: deep breath, slow inhale, gentle, clear, isolated",
        "Foley sound: soft cat paw placement on ground, subtle, light, minimal friction",
        "Foley sound: kitten scamper, quick, light paw steps, subtle fur rustle, fast movement",
        "Foley sound: glowing robotic eye hum, rising frequency, subtle whirring, electronic, continuous",
        "Foley sound: ancient map handling, heavy parchment rustle, faint dust sound, slow movement",
        "Foley sound: crystal pulsating hum, rhythmic, low frequency, ethereal, magical, continuous",
        "Foley sound: fairy lights shimmer, delicate, high-frequency sparkle, twinkling, light airy sound",
        "Foley sound: cat purr, deep, contented, rumbling, close mic, warm",
        "Foley sound: map spread on ground, scratching parchment, rustling, subtle contact with earth"
      ]
    }
  },
  "next_step": "LB08_aura_ambient"
}
```