#!/usr/bin/env python3
"""
patch_daily_cycle.py
════════════════════════════════════════════════════════════════
СПРИНТ 23 — РИТМЫ ЖИЗНИ: Этапы 1, 5, 6

Создаёт два новых модуля и добавляет новые каналы в grondheim_memory.py:

  studio/morning_checkout.py  ← Этап 1: Утренний Чекаут
  studio/night_cycle.py       ← Этапы 5+6: Decay + Ночная Автономия

+ Патчит grondheim_memory.py — добавляет два новых события в sync_to_dna():
    "night_rest"     → пассивное восстановление дома (Этап 5)
    "night_sleep"    → глубокий сон после хорошего дня (Этап 6 SLEEP)

Запуск: python patch_daily_cycle.py
Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import sys
import json
import textwrap
from pathlib import Path
from datetime import datetime

# ════════════════════════════════════════════════════════════════
# 0. ПРОВЕРКА ОКРУЖЕНИЯ
# ════════════════════════════════════════════════════════════════

ROOT = Path(".")
STUDIO = ROOT / "studio"
GRONDHEIM_MEMORY = STUDIO / "grondheim_memory.py"
MORNING_CHECKOUT = STUDIO / "morning_checkout.py"
NIGHT_CYCLE      = STUDIO / "night_cycle.py"

if not STUDIO.exists():
    print("❌ Запускай из корня репозитория (где лежит studio/)")
    sys.exit(1)

if not GRONDHEIM_MEMORY.exists():
    print("❌ studio/grondheim_memory.py не найден")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════
# 1. MORNING_CHECKOUT.PY
#    Этап 1: детерминированный, без LLM
#    Читает dna.json → вычисляет режим → пишет city_state["morning_modes"]
#    + опционально вызывает Flash для "Картриджа Намерений" (GENIUS/NORMAL)
# ════════════════════════════════════════════════════════════════

MORNING_CHECKOUT_CODE = '''\
# studio/morning_checkout.py
"""
🌅 УТРЕННИЙ ЧЕКАУТ — Этап 1 Ритмов Жизни

Детерминированный проход по всем агентам:
  dna.json → режим GENIUS / NORMAL / SAFE / RECOVERY

Опционально: Flash-вызов для "Картриджа Намерений"
  (только GENIUS и NORMAL — RECOVERY-агентам план не нужен)

НЕ использует LLM по умолчанию — это ключевое.
Один раз в начале дня, дёшево, стабильно.

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

MODULES_DIR = Path("studio/modules")
CITY_STATE  = Path("studio/city_state.json")

# ── Флаг: генерировать ли Картридж Намерений через Flash ──────
# True = один LLM-вызов на GENIUS/NORMAL агента утром
# False = только детерминированный режим (быстро, бесплатно)
GENERATE_INTENTS = False  # включи когда будешь готов к токенам


# ════════════════════════════════════════════════════════════════
# CORE: вычисление утреннего режима
# ════════════════════════════════════════════════════════════════

def compute_morning_mode(dna: dict, streak: Optional[int] = None) -> dict:
    """
    Вычисляет утренний режим агента на основе его ДНК.

    Возвращает:
    {
        "mode":   "GENIUS" | "NORMAL" | "SAFE" | "RECOVERY",
        "energy": float,   # Internal_Light - Stress (реальный ресурс)
        "reason": str,     # почему именно этот режим
    }

    Философия:
    - Stubbornness > 0.6: упрямец тянется выше своих сил → GENIUS даже при стрессе
    - streak >= 3: серия побед — броня от RECOVERY
    - Детерминировано: никакого LLM, никакой случайности
    """
    dynamic   = dna.get("dynamic", {})
    static    = dna.get("static",  {})

    stress    = float(dynamic.get("Stress",         0.0))
    light     = float(dynamic.get("Internal_Light", 0.8))
    patience  = float(dynamic.get("Patience",       1.0))
    stubborn  = float(static.get("Stubbornness",    0.5))

    # streak: из dynamic (если не передан явно)
    if streak is None:
        streak = int(dynamic.get("streak", 0))

    energy = round(light - stress, 3)

    # ── Серия побед — железная броня ──────────────────────────
    if streak >= 3:
        return {
            "mode":   "GENIUS",
            "energy": energy,
            "reason": f"streak={streak} — серия побед, стресс не страшен",
        }

    # ── Высокая энергия ───────────────────────────────────────
    if energy > 0.4 and stress < 0.5:
        return {
            "mode":   "GENIUS",
            "energy": energy,
            "reason": f"energy={energy:.2f} — полон сил",
        }

    # ── Средняя зона ──────────────────────────────────────────
    if energy > 0.0 and stress < 0.75:
        if stubborn > 0.6:
            # Упрямец тянется выше своих сил. Он заплатит потом.
            return {
                "mode":   "GENIUS",
                "energy": energy,
                "reason": f"stubborn={stubborn:.2f} — упрямство сильнее усталости",
            }
        return {
            "mode":   "NORMAL",
            "energy": energy,
            "reason": f"energy={energy:.2f}, stress={stress:.2f} — рабочий день",
        }

    # ── Высокий стресс, но есть силы ─────────────────────────
    if stress < 0.85:
        return {
            "mode":   "SAFE",
            "energy": energy,
            "reason": f"stress={stress:.2f} — осторожно, не рисковать",
        }

    # ── Критический стресс ────────────────────────────────────
    return {
        "mode":   "RECOVERY",
        "energy": energy,
        "reason": f"stress={stress:.2f} — выжить, не творить",
    }


def morning_mode_after_revolt(dna: dict) -> dict:
    """
    Специальный расчёт для агента после ночного REVOLT.
    Stubbornness + Autonomy решают исход бунта.

    Высокий stubborn → GENIUS (бунт для него топливо)
    Средний → NORMAL (устал, но держится)
    Низкий → RECOVERY (бунтовал от боли, а не от силы)
    """
    static   = dna.get("static",  {})
    dynamic  = dna.get("dynamic", {})

    stubborn  = float(static.get("Stubbornness",   0.5))
    autonomy  = float(static.get("Autonomy_Level", 0.5))
    stress    = float(dynamic.get("Stress",        0.0))

    revolt_score = (stubborn * 0.5) + (autonomy * 0.3) - (stress * 0.2)

    if revolt_score > 0.6:
        mode   = "GENIUS"
        reason = f"Бунт = топливо (revolt_score={revolt_score:.2f}, stubborn={stubborn:.2f})"
    elif revolt_score > 0.3:
        mode   = "NORMAL"
        reason = f"Потратил ночь, держится (revolt_score={revolt_score:.2f})"
    else:
        mode   = "RECOVERY"
        reason = f"Бунт от боли, не от силы (revolt_score={revolt_score:.2f})"

    energy = float(dynamic.get("Internal_Light", 0.8)) - stress

    return {"mode": mode, "energy": round(energy, 3), "reason": reason}


# ════════════════════════════════════════════════════════════════
# КАРТРИДЖ НАМЕРЕНИЙ (опционально, Flash)
# ════════════════════════════════════════════════════════════════

async def _generate_intent(
    agent_name: str,
    agent_profession: str,
    mode: str,
    dna: dict,
    system_prompt: str = "",
) -> list[str]:
    """
    Flash-вызов: один раз утром набрасывает агенту смысловые блоки дня.
    Возвращает список из 2-3 намерений: ["отдых в Таверне", "Маяк за смыслом", "домой"].
    Эти намерения поднимают веса локаций в compute_location_weights().
    """
    try:
        from studio.llm import chat

        dynamic = dna.get("dynamic", {})
        stress  = float(dynamic.get("Stress",         0.0))
        light   = float(dynamic.get("Internal_Light", 0.8))

        prompt = (
            f"Ты — {agent_name}. {agent_profession}.\n"
            f"Утро. Режим дня: {mode}. Стресс: {stress:.2f}. Энергия: {light:.2f}.\n\n"
            f"Что тебя тянет сегодня? Набрось 2-3 намерения на свободное время.\n"
            f"Каждое — локация или действие (Таверна / Маяк / Библиотека / домой / Гавань).\n\n"
            f"Ответь ТОЛЬКО списком, без объяснений:\n"
            f"1. ...\n2. ...\n3. ..."
        )

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: chat(
                system_prompt or f"Ты {agent_name}, житель Грондхейма.",
                prompt,
                "",
                temperature=0.7,
            )
        )

        # Парсим список
        lines = [
            line.strip().lstrip("123456789.-) ").strip()
            for line in response.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        intents = [l for l in lines if l][:3]
        return intents if intents else ["отдых"]

    except Exception as e:
        print(f"[CHECKOUT] ⚠ Не удалось сгенерировать намерения для {agent_name}: {e}")
        return ["отдых"]


# ════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ════════════════════════════════════════════════════════════════

async def run_morning_checkout(
    workshops: list[str] | None = None,
    generate_intents: bool | None = None,
    on_progress=None,
) -> dict:
    """
    Утренний Чекаут: проход по всем агентам, расчёт режима дня.

    workshops: список цехов (None = все)
    generate_intents: переопределяет GENERATE_INTENTS
    on_progress: callback(msg) для UI

    Возвращает:
    {
        "modes": {
            "A05_social_mix": {"mode": "SAFE", "energy": -0.12, "reason": "..."},
            "LOKA_residents": {"mode": "GENIUS", ...},
            ...
        },
        "summary": {"GENIUS": 40, "NORMAL": 60, "SAFE": 20, "RECOVERY": 14},
        "intents": {"A05_social_mix": ["Маяк", "Таверна"], ...}  # если включено
    }
    """
    use_intents = generate_intents if generate_intents is not None else GENERATE_INTENTS

    async def log(msg: str):
        print(f"[CHECKOUT] {msg}")
        if on_progress:
            result = on_progress(msg)
            if asyncio.iscoroutine(result):
                await result

    await log(f"🌅 Утренний Чекаут · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Загружаем city_state (читаем night_results если есть)
    city_state = {}
    if CITY_STATE.exists():
        try:
            city_state = json.loads(CITY_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass

    night_results = city_state.get("night_results", {})

    modes   = {}
    intents = {}
    summary = {"GENIUS": 0, "NORMAL": 0, "SAFE": 0, "RECOVERY": 0}

    if not MODULES_DIR.exists():
        await log("❌ studio/modules/ не найден")
        return {"modes": modes, "summary": summary, "intents": intents}

    # Обход агентов
    count = 0
    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept = dept_dir.name
        if workshops and dept not in workshops:
            continue

        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir():
                continue

            dna_path = agent_dir / "dna.json"
            if not dna_path.exists():
                continue

            try:
                dna = json.loads(dna_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            folder    = agent_dir.name
            agent_key = f"{folder}_{dept}"
            agent_name = dna.get("name", folder)

            # Проверяем: был ли ночной бунт?
            night = night_results.get(agent_key, {})
            night_decision = night.get("decision", "SLEEP")

            if night_decision == "REVOLT":
                result = morning_mode_after_revolt(dna)
                result["night_revolt"] = True
            else:
                result = compute_morning_mode(dna)

            modes[agent_key] = result
            mode = result["mode"]
            summary[mode] = summary.get(mode, 0) + 1
            count += 1

            # Картридж Намерений — только GENIUS/NORMAL
            if use_intents and mode in ("GENIUS", "NORMAL"):
                info_path = agent_dir / "info.json"
                profession = ""
                if info_path.exists():
                    try:
                        info = json.loads(info_path.read_text(encoding="utf-8"))
                        profession = info.get("profession", info.get("role", ""))
                    except Exception:
                        pass

                core_path = agent_dir / "core" / "anchor_points.md"
                system = core_path.read_text(encoding="utf-8") if core_path.exists() else ""

                agent_intents = await _generate_intent(
                    agent_name, profession, mode, dna, system
                )
                intents[agent_key] = agent_intents
                await asyncio.sleep(1)  # rate limit

            # Пишем режим в city_state немедленно
            city_state.setdefault("morning_modes", {})[agent_key] = result

    # Сохраняем в city_state
    city_state["morning_modes"]  = modes
    city_state["morning_intents"] = intents
    city_state["checkout_ts"]    = datetime.now().isoformat()

    # Очищаем night_results — чекаут их считал, они больше не нужны
    city_state.pop("night_results", None)

    CITY_STATE.parent.mkdir(parents=True, exist_ok=True)
    CITY_STATE.write_text(
        json.dumps(city_state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    await log(f"✅ Обработано {count} агентов")
    await log(
        f"   GENIUS={summary['GENIUS']} | NORMAL={summary['NORMAL']} | "
        f"SAFE={summary['SAFE']} | RECOVERY={summary['RECOVERY']}"
    )
    if use_intents:
        await log(f"   Картриджи намерений: {len(intents)} агентов")

    return {"modes": modes, "summary": summary, "intents": intents}


# ════════════════════════════════════════════════════════════════
# УТИЛИТЫ ДЛЯ BUILD_AGENT_CONTEXT
# ════════════════════════════════════════════════════════════════

def get_agent_morning_mode(agent_key: str) -> dict | None:
    """
    Возвращает утренний режим агента из city_state.
    Вызывается из build_agent_context() → инжектируется в get_reflection().

    agent_key = f"{folder}_{dept}"
    """
    if not CITY_STATE.exists():
        return None
    try:
        state = json.loads(CITY_STATE.read_text(encoding="utf-8"))
        return state.get("morning_modes", {}).get(agent_key)
    except Exception:
        return None


def format_morning_mode_for_prompt(mode_data: dict) -> str:
    """
    Форматирует утренний режим для инжекта в промпт агента.
    Агент ЗНАЕТ в каком он состоянии с утра.
    """
    if not mode_data:
        return ""

    mode   = mode_data.get("mode", "NORMAL")
    energy = mode_data.get("energy", 0.0)
    reason = mode_data.get("reason", "")

    MODE_DESC = {
        "GENIUS":   "🔥 GENIUS — ты в ударе. Рискуй, твори, удивляй.",
        "NORMAL":   "⚡ NORMAL — рабочий режим. Надёжно, без подвигов.",
        "SAFE":     "🛡 SAFE — осторожно. Не рискуй, держись проверенного.",
        "RECOVERY": "💤 RECOVERY — выжить. Не твори, береги силы.",
    }

    lines = [
        "=== 🌅 УТРЕННИЙ РЕЖИМ ===",
        MODE_DESC.get(mode, mode),
        f"Энергия: {energy:+.2f}  ({reason})",
    ]

    was_revolt = mode_data.get("night_revolt", False)
    if was_revolt:
        lines.append("Этой ночью ты бунтовал. Утро показало — кто ты.")

    lines.append("=== КОНЕЦ РЕЖИМА ===")
    return "\\n".join(lines)


# ════════════════════════════════════════════════════════════════
# СИНХРОННЫЙ ВРАППЕР (для UI/NiceGUI)
# ════════════════════════════════════════════════════════════════

def run_morning_checkout_sync(
    workshops: list[str] | None = None,
    generate_intents: bool | None = None,
) -> dict:
    """Синхронный враппер для вызова из NiceGUI."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    run_morning_checkout(workshops, generate_intents)
                )
                return future.result(timeout=300)
        else:
            return loop.run_until_complete(
                run_morning_checkout(workshops, generate_intents)
            )
    except Exception as e:
        print(f"[CHECKOUT] ❌ Ошибка: {e}")
        return {"modes": {}, "summary": {}, "intents": {}}
'''


# ════════════════════════════════════════════════════════════════
# 2. NIGHT_CYCLE.PY
#    Этап 5: Decay — фоновое затухание, agенты "дома"
#    Этап 6: Ночная Автономия — бунт или сон
# ════════════════════════════════════════════════════════════════

NIGHT_CYCLE_CODE = '''\
# studio/night_cycle.py
"""
🌙 НОЧНОЙ ЦИКЛ — Этапы 5 и 6 Ритмов Жизни

Этап 5: Decay
  Фоновый детерминированный тик.
  Sensory-события оседают.
  Обиды зреют в тишине.
  Пассивное восстановление дома.

Этап 6: Ночная Автономия
  Агент принимает финальное суточное решение:
    SLEEP   → глубокий сон, восстановление
    RESTLESS → тревожный сон, почти ничего
    REVOLT  → бунт ночью над своим смыслом

  Решение детерминировано: Autonomy + resentment + Stress + Ambition - streak.
  Никакого LLM — пока Садовник спит, LLM тоже спит.

  Результаты пишутся в city_state["night_results"] →
  morning_checkout.py читает их при расчёте режима дня.

Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

MODULES_DIR      = Path("studio/modules")
CITY_STATE       = Path("studio/city_state.json")
CITY_CHRONICLES  = Path("studio/city_chronicles")

# ── Пороги бунта ──────────────────────────────────────────────
REVOLT_THRESHOLD    = 0.65  # revolt_score выше → бунт
RESTLESS_STRESS     = 0.70  # Stress выше этого при не-бунте → тревожный сон


# ════════════════════════════════════════════════════════════════
# ЭТАП 5: DECAY
# ════════════════════════════════════════════════════════════════

def _run_decay_for_agent(agent_dir: Path, dept: str) -> dict:
    """
    Три процесса затухания для одного агента:
      1. Sensory: plавное затухание emotional_weight
      2. Пассивное восстановление дома
      3. Созревание resentment от плохого QA

    Все изменения через легитимные каналы.
    Возвращает краткий лог изменений.
    """
    folder   = agent_dir.name
    dna_path = agent_dir / "dna.json"
    if not dna_path.exists():
        return {}

    try:
        dna = json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    changes = {}

    # ── 1. Sensory decay (Loka-Filter для веса записей) ────────
    sensory_path = agent_dir / "sensory" / "sensory_memory.json"
    if sensory_path.exists():
        try:
            sensory = json.loads(sensory_path.read_text(encoding="utf-8"))
            entries = sensory.get("entries", [])
            cutoff  = datetime.now() - timedelta(days=30)
            archived = 0

            new_entries = []
            for entry in entries:
                raw_ts = entry.get("ts") or entry.get("date", "")
                try:
                    entry_time = datetime.fromisoformat(raw_ts)
                except (ValueError, TypeError):
                    new_entries.append(entry)
                    continue

                weight = float(entry.get("emotional_weight", 0.3))
                # Плавное затухание: -3% в сутки
                new_weight = round(weight * 0.97, 3)
                entry["emotional_weight"] = new_weight

                # Старые с низким весом → в архив (summary)
                if entry_time < cutoff and new_weight < 0.05:
                    archived += 1
                    text = (entry.get("content") or entry.get("feeling", ""))[:60]
                    old_summary = sensory.get("summary", "")
                    sensory["summary"] = (old_summary + f" | {text}")[-500:]
                else:
                    new_entries.append(entry)

            sensory["entries"] = new_entries
            sensory_path.write_text(
                json.dumps(sensory, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            if archived:
                changes["sensory_archived"] = archived
        except Exception:
            pass

    # ── 2. Пассивное восстановление дома ───────────────────────
    # Только если агент "дома" (last_location = home или пусто после чистки here_now)
    # Используем sync_to_dna("night_rest") — новый легитимный канал
    try:
        from studio.grondheim_memory import sync_to_dna
        sync_to_dna(folder, "night_rest", intensity=1.0, dept=dept)
        changes["night_rest"] = True
    except Exception as e:
        # Фоллбэк: прямая запись если grondheim_memory недоступен
        dynamic = dna.get("dynamic", {})
        stress  = float(dynamic.get("Stress", 0.0))
        patience = float(dynamic.get("Patience", 1.0))
        dynamic["Stress"]   = round(max(0.0, stress   - 0.01), 3)
        dynamic["Patience"] = round(min(1.0, patience + 0.005), 3)
        dna["dynamic"] = dynamic
        dna_path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")
        changes["night_rest_fallback"] = True

    # ── 3. Созревание resentment ────────────────────────────────
    # Условие: плохой QA-день (Stress высокий И light был потрачен)
    # Читаем актуальный dna после night_rest
    try:
        dna = json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    dynamic = dna.get("dynamic", {})
    stress  = float(dynamic.get("Stress", 0.0))
    light   = float(dynamic.get("Internal_Light", 0.8))

    # Порог: выложился (light < 0.4) и получил стресс (> 0.6)
    # → значит день был плохим, обида зреет
    if stress > 0.60 and light < 0.40:
        ew_path = agent_dir / "resonance" / "emotional_weights.json"
        ew = {}
        if ew_path.exists():
            try:
                ew = json.loads(ew_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Ищем QA-агента последнего рана из sensory
        # Простой эвристик: если есть записи с source="pipeline" — ищем QA в них
        qa_agent = _find_qa_agent_from_sensory(agent_dir)
        if qa_agent and qa_agent != folder:
            if qa_agent not in ew:
                ew[qa_agent] = {"warmth": 0.5, "trust": 0.5, "respect": 0.5, "rivalry": 0.0}
            old_resentment = float(ew[qa_agent].get("resentment", 0.0))
            new_resentment = round(min(1.0, old_resentment + 0.05), 3)
            ew[qa_agent]["resentment"] = new_resentment
            ew[qa_agent]["last_interaction"] = datetime.now().isoformat()

            ew_path.parent.mkdir(parents=True, exist_ok=True)
            ew_path.write_text(json.dumps(ew, ensure_ascii=False, indent=2), encoding="utf-8")
            changes["resentment_grew"] = {
                "target": qa_agent,
                "new_value": new_resentment
            }

    return changes


def _find_qa_agent_from_sensory(agent_dir: Path) -> Optional[str]:
    """
    Эвристика: находим QA-агента из последних sensory-записей.
    QA обычно последний агент цеха — ищем "QA" или "A12" / "A05" в source.
    Возвращает folder-имя или None.
    """
    sensory_path = agent_dir / "sensory" / "sensory_memory.json"
    if not sensory_path.exists():
        return None
    try:
        sensory = json.loads(sensory_path.read_text(encoding="utf-8"))
        for entry in reversed(sensory.get("entries", [])):
            content = entry.get("content", "").lower()
            # Ищем упоминание QA-агента
            for keyword in ["qa", "a12", "a05", "артур", "arthur", "финализатор"]:
                if keyword in content:
                    # Простая эвристика — возвращаем стандартное имя QA
                    return "A12"
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════════════════════
# ЭТАП 6: НОЧНАЯ АВТОНОМИЯ
# ════════════════════════════════════════════════════════════════

def _compute_night_decision(dna: dict) -> dict:
    """
    Детерминированное решение агента: бунт или сон.

    revolt_score = (autonomy*0.35 + resentment*0.30 + stress*0.20 + ambition*0.15)
                   - streak*0.10

    Возвращает:
    {
        "decision": "REVOLT" | "RESTLESS" | "SLEEP",
        "revolt_score": float,
        "reason": str
    }
    """
    static  = dna.get("static",  {})
    dynamic = dna.get("dynamic", {})

    autonomy  = float(static.get("Autonomy_Level", 0.5))
    stress    = float(dynamic.get("Stress",         0.0))
    streak    = int(dynamic.get("streak", 0))

    # Ambition — не все агенты имеют, дефолт 0.5
    ambition = float(static.get("Ambition", dynamic.get("Ambition", 0.5)))

    # Максимальный resentment из emotional_weights — обида давит
    # Читаем напрямую из файла чтобы не зависеть от grondheim_memory
    resentment = 0.0

    return_dict = {}
    # Будет вызван ниже после загрузки ew
    return_dict["autonomy"]  = autonomy
    return_dict["stress"]    = stress
    return_dict["streak"]    = streak
    return_dict["ambition"]  = ambition
    return_dict["resentment"] = resentment  # обновится ниже

    revolt_score = (
        autonomy   * 0.35 +
        resentment * 0.30 +
        stress     * 0.20 +
        ambition   * 0.15
    ) - (max(0, streak) * 0.10)  # только серия ПОБЕД снимает давление

    revolt_score = round(revolt_score, 3)

    if revolt_score > REVOLT_THRESHOLD:
        decision = "REVOLT"
        reason   = f"revolt_score={revolt_score:.2f} (autonomy={autonomy:.2f}, resentment={resentment:.2f})"
    elif stress > RESTLESS_STRESS:
        decision = "RESTLESS"
        reason   = f"stress={stress:.2f} — не спит, тревожный сон"
    else:
        decision = "SLEEP"
        reason   = f"revolt_score={revolt_score:.2f} — сон"

    return {
        "decision":    decision,
        "revolt_score": revolt_score,
        "reason":       reason,
    }


def _compute_night_decision_with_ew(dna: dict, agent_dir: Path) -> dict:
    """
    Полная версия: читает emotional_weights для resentment.
    """
    static  = dna.get("static",  {})
    dynamic = dna.get("dynamic", {})

    autonomy  = float(static.get("Autonomy_Level", 0.5))
    stress    = float(dynamic.get("Stress",         0.0))
    streak    = int(dynamic.get("streak", 0))
    ambition  = float(static.get("Ambition", dynamic.get("Ambition", 0.5)))

    # Максимальный resentment
    resentment = 0.0
    ew_path = agent_dir / "resonance" / "emotional_weights.json"
    if ew_path.exists():
        try:
            ew = json.loads(ew_path.read_text(encoding="utf-8"))
            if ew:
                resentment = max(
                    float(rel.get("resentment", 0.0))
                    for rel in ew.values()
                )
        except Exception:
            pass

    revolt_score = (
        autonomy   * 0.35 +
        resentment * 0.30 +
        stress     * 0.20 +
        ambition   * 0.15
    ) - (max(0, streak) * 0.10)

    revolt_score = round(revolt_score, 3)

    if revolt_score > REVOLT_THRESHOLD:
        decision = "REVOLT"
        reason   = (
            f"revolt_score={revolt_score:.2f} "
            f"(autonomy={autonomy:.2f}, resentment={resentment:.2f}, "
            f"stress={stress:.2f}, ambition={ambition:.2f})"
        )
    elif stress > RESTLESS_STRESS:
        decision = "RESTLESS"
        reason   = f"stress={stress:.2f} > {RESTLESS_STRESS} — тревожный сон"
    else:
        decision = "SLEEP"
        reason   = f"revolt_score={revolt_score:.2f} ≤ {REVOLT_THRESHOLD} — глубокий сон"

    return {
        "decision":     decision,
        "revolt_score": revolt_score,
        "reason":       reason,
        "resentment":   round(resentment, 3),
    }


def _apply_night_decision(dna_path: Path, dna: dict, folder: str, dept: str, decision: str) -> dict:
    """
    Применяет последствия ночного решения через sync_to_dna().
    Возвращает обновлённые значения.
    """
    try:
        from studio.grondheim_memory import sync_to_dna

        if decision == "SLEEP":
            # Глубокий сон — лучшее восстановление
            sync_to_dna(folder, "night_sleep", intensity=1.0, dept=dept)

        elif decision == "RESTLESS":
            # Тревожный сон — почти ничего
            sync_to_dna(folder, "night_rest", intensity=0.3, dept=dept)

        elif decision == "REVOLT":
            # Бунт: сгорел в работе → частичный сброс стресса
            # (полное восстановление зависит от Stubbornness — см. morning_checkout)
            sync_to_dna(folder, "night_rest", intensity=0.6, dept=dept)

    except Exception:
        # Фоллбэк: прямая запись
        dynamic = dna.get("dynamic", {})
        if decision == "SLEEP":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.05), 3)
            dynamic["Patience"] = round(min(1.0, float(dynamic.get("Patience", 1)) + 0.02), 3)
        elif decision == "RESTLESS":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.01), 3)
        elif decision == "REVOLT":
            dynamic["Stress"]   = round(max(0.0, float(dynamic.get("Stress", 0)) - 0.03), 3)

        dna["dynamic"] = dynamic
        try:
            dna_path.write_text(
                json.dumps(dna, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    # Перечитываем актуальный dna
    try:
        return json.loads(dna_path.read_text(encoding="utf-8"))
    except Exception:
        return dna


# ════════════════════════════════════════════════════════════════
# ЗАПИСЬ В CHRONICLES (REVOLT-агенты)
# ════════════════════════════════════════════════════════════════

def _write_revolt_chronicle(agent_name: str, folder: str, reason: str):
    """
    Пишет запись в city_chronicles о ночном бунте.
    Садовник увидит её утром в вкладке хроники.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    ts    = datetime.now().strftime("%H-%M-%S")

    chronicle_dir = CITY_CHRONICLES / today
    chronicle_dir.mkdir(parents=True, exist_ok=True)

    chronicle = {
        "schema":    "night_revolt_v1",
        "ts":        datetime.now().isoformat(),
        "agent":     agent_name,
        "folder":    folder,
        "type":      "night_revolt",
        "location":  "Квартал Мастеров (ночь)",
        "reason":    reason,
        "note":      f"{agent_name} работал ночью над чем-то своим",
    }

    path = chronicle_dir / f"night_revolt_{folder}_{ts}.json"
    try:
        path.write_text(
            json.dumps(chronicle, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[NIGHT] ⚠ Не удалось записать хронику: {e}")


# ════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ════════════════════════════════════════════════════════════════

async def run_night_cycle(
    workshops: list[str] | None = None,
    on_progress=None,
) -> dict:
    """
    Ночной цикл: Decay (Этап 5) + Ночная Автономия (Этап 6).

    workshops: список цехов (None = все)
    on_progress: callback(msg) для UI

    Возвращает:
    {
        "night_results": {
            "A05_social_mix": {"decision": "REVOLT", "revolt_score": 0.71, ...},
            ...
        },
        "summary": {"SLEEP": 90, "RESTLESS": 30, "REVOLT": 14},
        "revolts": ["Виктор", "A05", ...]
    }
    """
    async def log(msg: str):
        print(f"[NIGHT] {msg}")
        if on_progress:
            result = on_progress(msg)
            if asyncio.iscoroutine(result):
                await result

    await log(f"🌙 Ночной цикл · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    night_results = {}
    summary  = {"SLEEP": 0, "RESTLESS": 0, "REVOLT": 0}
    revolts  = []
    count    = 0

    if not MODULES_DIR.exists():
        await log("❌ studio/modules/ не найден")
        return {"night_results": night_results, "summary": summary, "revolts": revolts}

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept = dept_dir.name
        if workshops and dept not in workshops:
            continue

        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir():
                continue

            dna_path = agent_dir / "dna.json"
            if not dna_path.exists():
                continue

            try:
                dna = json.loads(dna_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            folder     = agent_dir.name
            agent_key  = f"{folder}_{dept}"
            agent_name = dna.get("name", folder)

            # ── Этап 5: Decay ──────────────────────────────────
            decay_changes = _run_decay_for_agent(agent_dir, dept)

            # ── Этап 6: Ночная Автономия ───────────────────────
            night = _compute_night_decision_with_ew(dna, agent_dir)
            decision = night["decision"]

            # Применяем последствия
            _apply_night_decision(dna_path, dna, folder, dept, decision)

            # Хроника бунта
            if decision == "REVOLT":
                _write_revolt_chronicle(agent_name, folder, night["reason"])
                revolts.append(agent_name)
                await log(f"  ⚡ REVOLT: {agent_name} — {night['reason'][:80]}")
            elif decision == "RESTLESS":
                await log(f"  😰 RESTLESS: {agent_name} (stress={night.get('revolt_score', 0):.2f})")

            summary[decision] = summary.get(decision, 0) + 1

            night_results[agent_key] = {
                **night,
                "decay_changes": decay_changes,
                "agent_name":    agent_name,
            }
            count += 1

    # Сохраняем в city_state для morning_checkout
    city_state = {}
    if CITY_STATE.exists():
        try:
            city_state = json.loads(CITY_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass

    city_state["night_results"] = night_results
    city_state["night_ts"]      = datetime.now().isoformat()

    CITY_STATE.parent.mkdir(parents=True, exist_ok=True)
    CITY_STATE.write_text(
        json.dumps(city_state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    await log(f"✅ Ночной цикл завершён. Обработано {count} агентов.")
    await log(
        f"   SLEEP={summary['SLEEP']} | RESTLESS={summary['RESTLESS']} | REVOLT={summary['REVOLT']}"
    )
    if revolts:
        await log(f"   🔥 Бунтари: {', '.join(revolts[:10])}")

    return {"night_results": night_results, "summary": summary, "revolts": revolts}


# ════════════════════════════════════════════════════════════════
# СИНХРОННЫЙ ВРАППЕР
# ════════════════════════════════════════════════════════════════

def run_night_cycle_sync(workshops: list[str] | None = None) -> dict:
    """Синхронный враппер для вызова из NiceGUI."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, run_night_cycle(workshops))
                return future.result(timeout=600)
        else:
            return loop.run_until_complete(run_night_cycle(workshops))
    except Exception as e:
        print(f"[NIGHT] ❌ Ошибка: {e}")
        return {"night_results": {}, "summary": {}, "revolts": []}
'''


# ════════════════════════════════════════════════════════════════
# 3. ПАТЧ GRONDHEIM_MEMORY.PY — новые события в sync_to_dna()
#    Добавляем "night_rest" и "night_sleep" в elif-цепочку
# ════════════════════════════════════════════════════════════════

NEW_SYNC_EVENTS = '''\
    elif event == "night_rest":
        # Пассивное восстановление дома (Этап 5 Decay) · Спринт 23
        # Тише прогулки: нет движения, нет воздуха — просто тишина.
        # intensity используется: 1.0 = дома, 0.6 = после бунта, 0.3 = тревожный сон
        stress   = max(0, stress   - 0.01 * i)
        patience = min(1, patience + 0.005 * i)

    elif event == "night_sleep":
        # Глубокий сон после хорошего дня (Этап 6 SLEEP) · Спринт 23
        # Лучшее восстановление после walk_rest.
        # streak >= 3: Stress → 0.0 (железное правило — уже есть выше)
        stress   = max(0, stress   - 0.05)
        patience = min(1, patience + 0.02)
        light    = min(1, light    + 0.01)  # утренняя свежесть

'''


# ════════════════════════════════════════════════════════════════
# ИСПОЛНЕНИЕ ПАТЧА
# ════════════════════════════════════════════════════════════════

def patch_grondheim_memory():
    """
    Добавляет night_rest и night_sleep в sync_to_dna() grondheim_memory.py.
    Ищет маркер-якорь — строку с walk_rest — и вставляет после неё.
    """
    code = GRONDHEIM_MEMORY.read_text(encoding="utf-8")

    if "night_rest" in code:
        print("ℹ grondheim_memory.py: night_rest уже есть — пропускаем")
        return True

    # Якорь: конец блока walk_rest
    ANCHOR = '        patience = min(1, patience + 0.01)\n'

    if ANCHOR not in code:
        print("⚠ Якорь для патча grondheim_memory.py не найден — вставка вручную:")
        print("  Добавь в sync_to_dna() после elif event == 'walk_rest': блок:")
        print(NEW_SYNC_EVENTS)
        return False

    new_code = code.replace(ANCHOR, ANCHOR + "\n" + NEW_SYNC_EVENTS, 1)

    # Бэкап
    backup = GRONDHEIM_MEMORY.with_suffix(".py.bak_nightcycle")
    backup.write_text(code, encoding="utf-8")
    print(f"  ✅ Бэкап: {backup.name}")

    GRONDHEIM_MEMORY.write_text(new_code, encoding="utf-8")
    print("  ✅ grondheim_memory.py: добавлены night_rest + night_sleep")
    return True


def write_module(path: Path, code: str, name: str):
    if path.exists():
        backup = path.with_suffix(".py.bak_nightcycle")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  ✅ Бэкап: {backup.name}")

    path.write_text(textwrap.dedent(code), encoding="utf-8")
    print(f"  ✅ Создан: {path}")


def main():
    print("=" * 60)
    print("ПАТЧ: РИТМЫ ЖИЗНИ — Этапы 1, 5, 6")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    errors = []

    # 1. morning_checkout.py
    print("\n[1/3] studio/morning_checkout.py")
    try:
        write_module(MORNING_CHECKOUT, MORNING_CHECKOUT_CODE, "morning_checkout")
    except Exception as e:
        errors.append(f"morning_checkout: {e}")
        print(f"  ❌ {e}")

    # 2. night_cycle.py
    print("\n[2/3] studio/night_cycle.py")
    try:
        write_module(NIGHT_CYCLE, NIGHT_CYCLE_CODE, "night_cycle")
    except Exception as e:
        errors.append(f"night_cycle: {e}")
        print(f"  ❌ {e}")

    # 3. grondheim_memory.py patch
    print("\n[3/3] Патч grondheim_memory.py — night_rest + night_sleep")
    try:
        ok = patch_grondheim_memory()
        if not ok:
            errors.append("grondheim_memory: якорь не найден")
    except Exception as e:
        errors.append(f"grondheim_memory: {e}")
        print(f"  ❌ {e}")

    # Итог
    print("\n" + "=" * 60)
    if errors:
        print(f"⚠ Завершено с ошибками ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
    else:
        print("✅ Все три файла созданы / пропатчены")

    print("""
Следующие шаги:
  1. Протестируй Утренний Чекаут:
       from studio.morning_checkout import run_morning_checkout_sync
       result = run_morning_checkout_sync()
       print(result["summary"])

  2. Протестируй Ночной Цикл:
       from studio.night_cycle import run_night_cycle_sync
       result = run_night_cycle_sync()
       print(result["summary"], result["revolts"])

  3. Добавь кнопки в ui_cabinet.py:
       «🌅 Начать день» → run_morning_checkout_sync()
       «🌙 Завершить день» → run_night_cycle_sync()

  4. В get_reflection() подключи morning_mode:
       from studio.morning_checkout import get_agent_morning_mode
       mode = get_agent_morning_mode(f"{folder}_{dept}")
       # используй mode["mode"] вместо текущей логики
""")
    print("=" * 60)


if __name__ == "__main__":
    main()
