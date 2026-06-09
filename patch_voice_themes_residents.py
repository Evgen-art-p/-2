"""
patch_voice_themes_residents.py
══════════════════════════════════════════════════════════════
СПРИНТ 42 · Баг #27

ПРОБЛЕМА:
  _compute_voice_themes() в city_traces.py читает только события
  типа "walk" с полем "agent_voice".

  Но log_resident_voice() пишет события типа "resident_voice"
  с полем "voice" и полем "resident" (не "agent").

  Итог: всё что говорят Лока, Джем, Кей, Юст, Виктор, Оле, Финч,
  Сет, Монтажёр — никогда не попадает в voice_themes.
  city_traces.json["voice_themes"] для резидентов всегда пустой.
  morning_checkout читает traces → намерения резидентов строятся
  без учёта их собственных слов. Город не слышит себя.

РЕШЕНИЕ:
  Расширяем _compute_voice_themes() — читает ОБА типа событий:
    • "walk"           → agent_voice, agent
    • "resident_voice" → voice,       resident

  Структура результата не меняется — те же топ-10 слов на агента.
  Резиденты появятся в voice_themes под своими именами.

ФАЙЛ: studio/city_traces.py
ИДЕМПОТЕНТЕН: да (проверяет маркер)
"""

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/city_traces.py")
MARKER = "# PATCH_VOICE_THEMES_RESIDENTS_APPLIED"

# ── Старый код ────────────────────────────────────────────────────
OLD = '''def _compute_voice_themes(events: list[dict]) -> dict:
    """
    Для каждого агента: топ-10 слов из его agent_voice за период.
    Слова короче 4 букв и стоп-слова отфильтрованы.

    Структура:
    {
      "Визор": [
        {"word": "ученики", "count": 7},
        {"word": "обучение", "count": 5},
        ...
      ]
    }
    """
    # agent → Counter слов
    agent_words: dict[str, Counter] = defaultdict(Counter)

    for e in events:
        if e.get("event") != "walk":
            continue
        agent = e.get("agent", "")
        voice = e.get("agent_voice", "")

        if not agent or not voice:
            continue

        # Токенизируем: только буквы, нижний регистр
        words = re.findall(r"[а-яёa-z]{4,}", voice.lower())
        for w in words:
            if w not in _STOP_WORDS:
                agent_words[agent][w] += 1

    result = {}
    for agent, counter in agent_words.items():
        # Только слова которые встречаются 2+ раз — иначе не паттерн
        themes = [
            {"word": word, "count": count}
            for word, count in counter.most_common(10)
            if count >= 2
        ]
        if themes:
            result[agent] = themes

    return result'''

# ── Новый код ─────────────────────────────────────────────────────
NEW = '''# PATCH_VOICE_THEMES_RESIDENTS_APPLIED · Спринт 42
def _compute_voice_themes(events: list[dict]) -> dict:
    """
    Для каждого агента/резидента: топ-10 слов за период.
    Слова короче 4 букв и стоп-слова отфильтрованы.

    Читает ДВА типа событий из city_pulse.jsonl:
      • "walk"           → поле "agent_voice", ключ "agent"
        (обычные агенты во время прогулки)
      • "resident_voice" → поле "voice",       ключ "resident"
        (голоса резидентов: Лока, Джем, Кей, Юст, Виктор, Оле, Финч...)

    Структура результата:
    {
      "Визор":  [{"word": "ученики",  "count": 7}, ...],
      "Лока":   [{"word": "студия",   "count": 5}, ...],
      "Джем":   [{"word": "музыка",   "count": 4}, ...],
    }
    """
    # agent/resident → Counter слов
    agent_words: dict[str, Counter] = defaultdict(Counter)

    for e in events:
        event_type = e.get("event", "")

        # ── Обычные агенты: walk → agent_voice ────────────────
        if event_type == "walk":
            agent = e.get("agent", "")
            voice = e.get("agent_voice", "")
            if not agent or not voice:
                continue

        # ── Резиденты: resident_voice → voice ─────────────────
        elif event_type == "resident_voice":
            agent = e.get("resident", "")
            voice = e.get("voice", "")
            if not agent or not voice:
                continue

        else:
            continue

        # Токенизируем: только буквы, нижний регистр
        words = re.findall(r"[а-яёa-z]{4,}", voice.lower())
        for w in words:
            if w not in _STOP_WORDS:
                agent_words[agent][w] += 1

    result = {}
    for agent, counter in agent_words.items():
        # Только слова которые встречаются 2+ раз — иначе не паттерн
        themes = [
            {"word": word, "count": count}
            for word, count in counter.most_common(10)
            if count >= 2
        ]
        if themes:
            result[agent] = themes

    return result'''


def main():
    if not TARGET.exists():
        print(f"[PATCH] ❌ Файл не найден: {TARGET}")
        print("[PATCH]    Запускай из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)")
        return

    text = TARGET.read_text(encoding="utf-8")

    if MARKER in text:
        print("[PATCH] ✅ Патч уже применён — пропускаю")
        return

    if OLD not in text:
        print("[PATCH] ⚠️  Старый код _compute_voice_themes не найден точно.")
        print("[PATCH]    Возможно файл уже изменён локально.")
        print("[PATCH]    Нужна ручная правка — добавить в цикл for e in events:")
        print()
        print("    # было:")
        print("    if e.get('event') != 'walk': continue")
        print("    agent = e.get('agent', '')")
        print("    voice = e.get('agent_voice', '')")
        print()
        print("    # стало: добавить elif для resident_voice")
        print("    if event_type == 'walk':")
        print("        agent = e.get('agent', '')")
        print("        voice = e.get('agent_voice', '')")
        print("    elif event_type == 'resident_voice':")
        print("        agent = e.get('resident', '')")
        print("        voice = e.get('voice', '')")
        print("    else: continue")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.with_suffix(f".bak_{ts}")
    shutil.copy2(TARGET, bak)
    print(f"[PATCH] 📦 Бэкап: {bak.name}")

    new_text = text.replace(OLD, NEW, 1)
    TARGET.write_text(new_text, encoding="utf-8")

    print(f"[PATCH] ✅ Применён: {TARGET}")
    print()
    print("[PATCH] Что изменилось:")
    print("  _compute_voice_themes() теперь читает:")
    print("    • 'walk'           → agent_voice (агенты на прогулке)")
    print("    • 'resident_voice' → voice       (голоса резидентов)")
    print()
    print("[PATCH] Эффект:")
    print("  Лока, Джем, Кей, Юст, Виктор, Оле, Финч, Сет, Монтажёр")
    print("  теперь появятся в city_traces.json['voice_themes'].")
    print("  morning_checkout будет строить намерения резидентов")
    print("  с учётом их собственных слов из прошлых дней.")
    print()
    print("[PATCH] Заработает на следующем запуске morning_checkout")
    print("  или можно форсировать:")
    print("  python -c \"from studio.city_traces import run_traces; run_traces()\"")


if __name__ == "__main__":
    main()
