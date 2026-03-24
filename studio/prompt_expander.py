# studio/prompt_expander.py
"""
Prompt Expansion — автоматическое обогащение промптов Новы
пространственной логикой перед генерацией.

Два режима:
  1. FAST: словарь физических паттернов (мгновенно, 0 токенов)
  2. LLM:  Gemini Flash переписывает промпт (200-300ms, ~100 токенов)

Использование:
  from studio.prompt_expander import expand_prompt
  expanded = expand_prompt(raw_prompt, mode="fast")  # или "llm" или "auto"
"""

import re

# ════════════════════════════════════════════════════════════
# РЕЖИМ 1: FAST — словарь пространственных паттернов
# ════════════════════════════════════════════════════════════

SPATIAL_RULES = [
    # (условие: все слова должны быть в тексте, замена/дополнение)
    {
        "match_all": ["candle", "window"],
        "match_none": ["windowsill", "sill", "standing on"],
        "append": ", the candle is standing firmly ON the windowsill inside the room, not floating in mid-air, window frame visible in the background",
    },
    {
        "match_all": ["candle", "flame"],
        "match_none": ["wick", "wax"],
        "append": ", detailed wax candle with visible wick, realistic flame glow, melted wax drips",
    },
    {
        "match_all": ["person", "window"],
        "match_none": ["standing beside", "next to", "looking through"],
        "append": ", person standing beside the window on the floor level, feet on the ground, natural perspective",
    },
    {
        "match_all": ["furniture", "room"],
        "match_none": ["on the floor", "resting"],
        "append": ", furniture resting firmly on the floor, realistic shadows and contact shadows, proper occlusion",
    },
    {
        "match_all": ["person", "door"],
        "match_none": ["doorway", "framed by", "standing in"],
        "append": ", person framed by the doorway, standing on the threshold, proper perspective with door frame",
    },
    {
        "match_all": ["tool", "hand"],
        "match_none": ["gripping", "holding", "grasping"],
        "append": ", tool firmly gripped in hand with proper finger placement, realistic hand anatomy",
    },
    {
        "match_all": ["measuring", "tape"],
        "match_none": ["stretched", "extended"],
        "append": ", measuring tape stretched and held taut, proper perspective foreshortening",
    },
    {
        "match_all": ["construction", "site"],
        "match_none": ["ground level", "floor"],
        "append": ", construction materials on the ground level, tools resting on surfaces, proper gravity",
    },
    {
        "match_all": ["window", "installation"],
        "match_none": ["frame", "opening"],
        "append": ", window frame being fitted into the wall opening, proper architectural perspective",
    },
    {
        "match_all": ["close-up", "object"],
        "match_none": ["macro", "detail"],
        "append": ", extreme close-up macro detail shot, shallow depth of field, surface texture visible",
    },
]

# Глобальные улучшения — всегда добавляются
GLOBAL_SUFFIX = (
    ". Physically accurate spatial relationships between all objects. "
    "Correct gravity, perspective, and occlusion. "
    "No floating objects."
)


def _fast_expand(prompt: str) -> str:
    """Применяет словарь пространственных правил."""
    lower = prompt.lower()
    additions = []

    for rule in SPATIAL_RULES:
        match_all = rule["match_all"]
        match_none = rule.get("match_none", [])

        # Все ключевые слова должны быть в тексте
        if all(w in lower for w in match_all):
            # Ни одно исключение не должно быть
            if not any(w in lower for w in match_none):
                additions.append(rule["append"])

    if additions:
        expanded = prompt.rstrip(". ") + "".join(additions) + GLOBAL_SUFFIX
        print(f"  🔧 Prompt expanded: +{len(additions)} spatial rules")
        return expanded

    # Даже без правил — добавляем глобальный суффикс
    return prompt.rstrip(". ") + GLOBAL_SUFFIX


# ════════════════════════════════════════════════════════════
# РЕЖИМ 2: LLM — Gemini Flash переписывает промпт
# ════════════════════════════════════════════════════════════

_LLM_SYSTEM = """You are a Prompt Engineer for AI image generation (Seedream/Flux/DALL-E).

Your task: take a creative/literary prompt from a story agent and rewrite it as a 
TECHNICALLY PRECISE image generation prompt.

Rules:
1. SPATIAL: Every object must have explicit position (ON the table, BESIDE the window, IN FRONT OF the door)
2. GRAVITY: Nothing floats. Specify "standing on floor", "resting on surface", "mounted on wall"
3. LAYERS: Define Foreground / Subject / Background explicitly
4. CAMERA: Keep the original camera angle but make it explicit (close-up, medium shot, wide shot)
5. STYLE: Preserve the original style tags (Pixar, cinematic, etc.)
6. ANATOMY: If humans present, specify correct hand/body positioning
7. NO floating candles, no objects merged into surfaces, no physics violations
8. Keep the prompt under 200 words
9. Output ONLY the rewritten prompt, nothing else
10. Write in ENGLISH only
11. CRITICAL — PRESERVE ALL ASSET IDs: Any token that looks like an asset reference 
    (char_XXX, loc_XXX, objekt_XXX, сайт_окна_XXX, or any ID with underscores and numbers) 
    MUST be kept EXACTLY as-is at the START of the prompt. These are reference image tags 
    that the generator uses for visual consistency. NEVER remove, rename or translate them."""


def _llm_expand(prompt: str) -> str:
    """Переписывает промпт через Gemini Flash."""
    try:
        from studio.llm import chat
        result = chat(_LLM_SYSTEM, f"Rewrite this prompt:\n\n{prompt}", "")
        if result and len(result) > 20:
            print(f"  🤖 Prompt expanded via LLM ({len(prompt)} → {len(result)} chars)")
            return result.strip()
    except Exception as e:
        print(f"  ⚠️ LLM expand failed: {e}")

    # Фоллбэк на fast
    return _fast_expand(prompt)


# ════════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API
# ════════════════════════════════════════════════════════════

def expand_prompt(prompt: str, mode: str = "fast") -> str:
    """
    Расширяет промпт пространственной логикой.

    mode:
      "fast" — только словарь (мгновенно, бесплатно)
      "llm"  — Gemini Flash переписывает (200ms, ~100 токенов)
      "auto" — fast + если есть физические аномалии → llm
      "off"  — без изменений
    """
    if mode == "off" or not prompt:
        return prompt

    if mode == "fast":
        return _fast_expand(prompt)

    if mode == "llm":
        return _llm_expand(prompt)

    if mode == "auto":
        # Проверяем есть ли потенциальные аномалии
        lower = prompt.lower()
        risky = any(
            all(w in lower for w in rule["match_all"])
            and not any(w in lower for w in rule.get("match_none", []))
            for rule in SPATIAL_RULES
        )
        if risky:
            return _llm_expand(prompt)
        return _fast_expand(prompt)

    return prompt
