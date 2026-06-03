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
    # 🌱 Финч обходит сад каждое утро
    try:
        from studio.garden_tools import finch_morning
        finch_morning(on_progress=on_progress)
    except Exception as e:
        print(f"[CHECKOUT] ⚠ Финч не смог обойти сад: {e}")


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
            # ── ПУЛЬС: wake ──────────────────────────────────────
            try:
                from studio.city_pulse import log_pulse as _lp
                _dyn = dna.get("dynamic", {})
                _lp("wake",
                    agent=agent_name, dept=dept,
                    stress=round(float(_dyn.get("Stress", 0.0)), 3),
                    light=round(float(_dyn.get("Internal_Light", 0.8)), 3),
                    patience=round(float(_dyn.get("Patience", 1.0)), 3),
                    mode=mode, streak=int(_dyn.get("streak", 0)),
                    night_revolt=result.get("night_revolt", False),
                )
            except Exception:
                pass
            # ── END ПУЛЬС ──

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
    return "\n".join(lines)


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
