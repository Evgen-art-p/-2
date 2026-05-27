#!/usr/bin/env python3
"""
patch_sprint23_block_a.py — Спринт 23, Блок А
Живой город: инерция привычки + погода как зеркало стресса

Что делает:
  1. ИНЕРЦИЯ ПРИВЫЧКИ
     - Добавляет habit_data в dna["dynamic"] всех агентов:
       {"favorite_location": "", "visit_streak": 0, "habit_strength": 0.0}
     - Патчит compute_location_weights() в city_walker.py:
       favorite_location получает +habit_strength к весу (max бонус 0.25)
     - Патчит walk_one_agent() в city_walker.py:
       после выбора локации обновляет habit_data агента

  2. ПОГОДА КАК ЗЕРКАЛО СТРЕССА
     - Патчит update_city_weather() в city_walker.py:
       читает средний Stress всех агентов → детерминированная погода

Запуск:
  python patch_sprint23_block_a.py

Требования:
  - Запускать из корня репо (рядом со studio/ и 00_REGISTRY_NFT/)
  - Python 3.10+
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════

MODULES_DIR = Path("studio/modules")
CITY_WALKER = Path("studio/city_walker.py")
BACKUP_DIR  = Path("_patch_backups/sprint23_block_a")

# Три диапазона стресса → погода
WEATHER_PRESETS = {
    "low":    ["рассвет · золотой свет", "ясно · ветер с океана", "тёплый дождь"],
    "medium": ["серое небо · тихо", "туман над гаванью", "переменная облачность"],
    "high":   ["гроза вдали", "туман над гаванью", "тяжёлые тучи · тихо перед бурей"],
}

# ═══════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════

def backup(path: Path):
    """Создаёт резервную копию файла перед патчем."""
    if not path.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    dest = BACKUP_DIR / f"{path.name}.{ts}.bak"
    shutil.copy2(path, dest)
    print(f"  📦 Бэкап: {dest}")


def load_dna(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_dna(path: Path, dna: dict):
    path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════
# ШАГИ ПАТЧА
# ═══════════════════════════════════════════════════════

def step1_add_habit_to_agents():
    """
    Шаг 1: Добавляет habit_data в dna["dynamic"] всех агентов у которых его нет.
    Не трогает агентов у которых поля уже есть.
    """
    print("\n─── Шаг 1: Добавляем habit_data в dna.json агентов ───")

    if not MODULES_DIR.exists():
        print("  ⚠️  studio/modules/ не найден — пропускаем")
        return 0

    updated = 0
    skipped = 0
    errors  = 0

    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        for agent_dir in sorted(dept_dir.iterdir()):
            dna_path = agent_dir / "dna.json"
            if not dna_path.exists():
                continue

            dna = load_dna(dna_path)
            if not dna:
                errors += 1
                continue

            dynamic = dna.get("dynamic", {})

            # Проверяем — уже есть?
            if "favorite_location" in dynamic:
                skipped += 1
                continue

            # Добавляем habit_data
            dynamic["favorite_location"] = ""
            dynamic["visit_streak"]      = 0
            dynamic["habit_strength"]    = 0.0

            dna["dynamic"] = dynamic

            try:
                save_dna(dna_path, dna)
                updated += 1
            except Exception as e:
                print(f"  ❌ {agent_dir.name}: {e}")
                errors += 1

    print(f"  ✅ Обновлено: {updated} | Уже есть: {skipped} | Ошибок: {errors}")
    return updated


def step2_patch_city_walker():
    """
    Шаг 2: Патчит city_walker.py — два блока:
      A) compute_location_weights() — добавляет habit_bonus в конец функции
      B) update_city_weather() — заменяет random.choice на stress-детерминированный расчёт
      C) walk_one_agent() — обновляет habit_data после выбора локации
    """
    print("\n─── Шаг 2: Патчим city_walker.py ───")

    if not CITY_WALKER.exists():
        print("  ❌ studio/city_walker.py не найден")
        return False

    backup(CITY_WALKER)
    src = CITY_WALKER.read_text(encoding="utf-8")

    # ── 2A: habit_bonus в compute_location_weights() ──
    # Ищем строку "# pull_vector бонус УБРАН" (финальная часть функции)
    # и добавляем перед ней habit_bonus

    HABIT_BONUS_MARKER = "        # pull_vector бонус УБРАН — выбор по текущему состоянию агента"
    HABIT_BONUS_CODE = """\
        # ══ ИНЕРЦИЯ ПРИВЫЧКИ · Спринт 23 ══
        # Если агент уже бывал здесь — его тянет сильнее.
        # habit_strength растёт с каждым визитом (max 0.25 бонус).
        # Это не хардкод — это накопленная история агента.
        fav_loc  = dna.get("dynamic", {}).get("favorite_location", "")
        hab_str  = float(dna.get("dynamic", {}).get("habit_strength", 0.0))
        if fav_loc and name == fav_loc:
            habit_bonus = min(0.25, hab_str)
            w = min(0.95, w + habit_bonus)
        # ══ END ИНЕРЦИЯ ПРИВЫЧКИ ══

        # pull_vector бонус УБРАН — выбор по текущему состоянию агента"""

    if HABIT_BONUS_MARKER in src:
        src = src.replace(HABIT_BONUS_MARKER, HABIT_BONUS_CODE)
        print("  ✅ 2A: habit_bonus добавлен в compute_location_weights()")
    else:
        print("  ⚠️  2A: маркер не найден в compute_location_weights() — проверь вручную")

    # ── 2B: stress-детерминированная погода ──
    # Заменяем тело update_city_weather()

    OLD_WEATHER_FUNC = '''\
def update_city_weather():
    """Обновляет погоду города (раз в день)."""
    import random
    state = load_city_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["weather"] = random.choice(WEATHER_OPTIONS)
        state["walk_count"] = 0
    save_city_state(state)
    return state'''

    NEW_WEATHER_FUNC = '''\
def _compute_avg_stress() -> float:
    """
    Читает средний Stress по всем агентам с dna.json.
    Кеширование: пересчёт не чаще раза в 30 минут.
    · Спринт 23: погода как зеркало стресса
    """
    import time
    cache_path = Path("studio/_stress_cache.json")

    # Проверяем кеш (30 минут)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            age = time.time() - cached.get("ts", 0)
            if age < 1800:  # 30 минут
                return cached["avg_stress"]
        except Exception:
            pass

    # Читаем стресс всех агентов
    stresses = []
    if MODULES_DIR.exists():
        for dept_dir in MODULES_DIR.iterdir():
            if not dept_dir.is_dir():
                continue
            for agent_dir in dept_dir.iterdir():
                dna_path = agent_dir / "dna.json"
                if not dna_path.exists():
                    continue
                try:
                    dna = json.loads(dna_path.read_text(encoding="utf-8"))
                    s = float(dna.get("dynamic", {}).get("Stress", 0.0))
                    stresses.append(s)
                except Exception:
                    continue

    avg = round(sum(stresses) / len(stresses), 3) if stresses else 0.3

    # Сохраняем кеш
    try:
        cache_path.write_text(
            json.dumps({"avg_stress": avg, "ts": time.time(), "count": len(stresses)},
                       ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass

    return avg


def update_city_weather():
    """
    Обновляет погоду города.
    · Спринт 23: погода = зеркало среднего стресса агентов (детерминировано).
    · Обновляется раз в день (дата меняется) или при явном сбросе.
    """
    import random
    state = load_city_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["walk_count"] = 0

        # Детерминированная погода из стресса города
        avg_stress = _compute_avg_stress()

        # Три диапазона → три атмосферы
        if avg_stress < 0.35:
            # Город в балансе — ясно и тепло
            options = ["рассвет · золотой свет", "ясно · ветер с океана", "тёплый дождь"]
        elif avg_stress < 0.65:
            # Средний стресс — переменная облачность
            options = ["серое небо · тихо", "туман над гаванью", "переменная облачность"]
        else:
            # Высокий стресс — гнетущая атмосфера
            options = ["гроза вдали", "туман над гаванью", "тяжёлые тучи · тихо перед бурей"]

        # Внутри диапазона — небольшая вариация через хеш даты (reproducible)
        import hashlib
        day_hash = int(hashlib.md5(today.encode()).hexdigest(), 16)
        state["weather"] = options[day_hash % len(options)]
        state["avg_stress"] = avg_stress  # сохраняем для UI

        print(f"[CITY] 🌤 Погода: avg_stress={avg_stress:.2f} → {state['weather']}")

    save_city_state(state)
    return state'''

    if OLD_WEATHER_FUNC in src:
        src = src.replace(OLD_WEATHER_FUNC, NEW_WEATHER_FUNC)
        print("  ✅ 2B: update_city_weather() заменена на stress-детерминированную")
    else:
        print("  ⚠️  2B: старая update_city_weather() не найдена точно — попробуем мягкий поиск")
        # Мягкий поиск
        if "random.choice(WEATHER_OPTIONS)" in src:
            print("       random.choice(WEATHER_OPTIONS) найден — нужна ручная замена")
        else:
            print("       Функция уже могла быть изменена ранее")

    # ── 2C: обновление habit_data после walk ──
    # Вставляем после блока "# ── ДНК: прогулка через единый канал · Спринт 21 ──"
    # перед строкой "    result = {"

    HABIT_UPDATE_MARKER = "    result = {\n        \"agent\":    name,"

    HABIT_UPDATE_CODE = """\
    # ══ ИНЕРЦИЯ ПРИВЫЧКИ: обновляем habit_data · Спринт 23 ══
    # После каждой прогулки запоминаем куда пришёл агент.
    # Если та же локация что и прошлый раз → visit_streak растёт → habit_strength усиливается.
    # Физика: 10 визитов подряд → habit_strength = 0.25 (максимальный бонус к весу).
    # Уход в другую локацию → visit_streak сбрасывается, habit_strength плавно затухает.
    try:
        _dna_h = load_dna(workshop, folder)
        _dyn_h = _dna_h.get("dynamic", {})
        _prev_fav = _dyn_h.get("favorite_location", "")
        _streak_h = int(_dyn_h.get("visit_streak", 0))
        _hab_str  = float(_dyn_h.get("habit_strength", 0.0))

        if chosen_location and chosen_location != "неизвестно":
            if chosen_location == _prev_fav:
                # Та же локация — усиливаем привычку
                _streak_h = min(_streak_h + 1, 20)
                _hab_str  = min(0.25, _streak_h * 0.025)  # +0.025 за визит, cap 0.25
            else:
                # Другая локация — обновляем фаворит, сбрасываем стрик
                # Но habit_strength затухает медленно (×0.7), не рвётся резко
                _prev_fav = chosen_location
                _streak_h = 1
                _hab_str  = round(_hab_str * 0.7, 3)

            _dyn_h["favorite_location"] = _prev_fav
            _dyn_h["visit_streak"]      = _streak_h
            _dyn_h["habit_strength"]    = round(_hab_str, 3)
            _dna_h["dynamic"] = _dyn_h
            save_dna(workshop, folder, _dna_h)
            print(f"[CITY] 🏠 {name} привычка: {_prev_fav} (streak={_streak_h}, strength={_hab_str:.3f})")
    except Exception as _hab_err:
        print(f"[CITY] ⚠ habit_data не обновлён: {_hab_err}")
    # ══ END ИНЕРЦИЯ ПРИВЫЧКИ ══

    result = {
        "agent":    name,"""

    if HABIT_UPDATE_MARKER in src:
        src = src.replace(HABIT_UPDATE_MARKER, HABIT_UPDATE_CODE)
        print("  ✅ 2C: habit_data обновление добавлено в walk_one_agent()")
    else:
        print("  ⚠️  2C: маркер для habit_data не найден — проверь вручную")

    # Записываем
    CITY_WALKER.write_text(src, encoding="utf-8")
    print(f"  💾 city_walker.py сохранён")
    return True


def step3_patch_city_summary():
    """
    Шаг 3: Добавляет avg_stress и weather_tier в get_city_summary()
    чтобы Кабинет мог показывать уровень напряжения города.
    """
    print("\n─── Шаг 3: Добавляем stress-tier в get_city_summary() ───")

    if not CITY_WALKER.exists():
        print("  ❌ city_walker.py не найден")
        return False

    src = CITY_WALKER.read_text(encoding="utf-8")

    OLD_SUMMARY = '''\
    lines = [
        f"🌆 Грондхейм · {state.get('date', '?')}",
        f"☁️ Погода: {state.get('weather', '?')}",
        f"⚡ Тонус: {state.get('energy', 0.7):.1f}",
        f"👥 Граждан: {len(agents)}",
        f"🏛️ Локаций: {len(locations)}",
        f"🚶 Прогулок сегодня: {state.get('walk_count', 0)}",
    ]'''

    NEW_SUMMARY = '''\
    # Погодный тир из avg_stress
    avg_stress = state.get("avg_stress", 0.3)
    if avg_stress < 0.35:
        stress_tier = "🌤 Баланс"
    elif avg_stress < 0.65:
        stress_tier = "⛅ Напряжение"
    else:
        stress_tier = "⛈ Кризис"

    lines = [
        f"🌆 Грондхейм · {state.get('date', '?')}",
        f"☁️ Погода: {state.get('weather', '?')}",
        f"🌡 Тонус города: {stress_tier} (стресс {avg_stress:.2f})",
        f"👥 Граждан: {len(agents)}",
        f"🏛️ Локаций: {len(locations)}",
        f"🚶 Прогулок сегодня: {state.get('walk_count', 0)}",
    ]'''

    if OLD_SUMMARY in src:
        src = src.replace(OLD_SUMMARY, NEW_SUMMARY)
        CITY_WALKER.write_text(src, encoding="utf-8")
        print("  ✅ stress-tier добавлен в get_city_summary()")
    else:
        print("  ⚠️  маркер get_city_summary() не найден — пропускаем")

    return True


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  patch_sprint23_block_a.py")
    print("  Живой город: инерция привычки + погода из стресса")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Проверка — запущен из корня репо?
    if not Path("studio").exists() or not Path("00_REGISTRY_NFT").exists():
        print("\n❌ Запускай из корня репо (где лежат studio/ и 00_REGISTRY_NFT/)")
        return

    results = {}

    n = step1_add_habit_to_agents()
    results["habit_fields_added"] = n

    ok2 = step2_patch_city_walker()
    results["city_walker_patched"] = ok2

    ok3 = step3_patch_city_summary()
    results["summary_patched"] = ok3

    print("\n" + "=" * 60)
    print("  ИТОГ")
    print("=" * 60)
    print(f"  Агентов с новым habit_data: {results['habit_fields_added']}")
    print(f"  city_walker.py пропатчен:   {'✅' if results['city_walker_patched'] else '❌'}")
    print(f"  get_city_summary обновлён:  {'✅' if results['summary_patched'] else '❌'}")
    print()
    print("  Что теперь работает:")
    print("  · Агенты накапливают привычку к любимой локации")
    print("  · Через 10 визитов подряд habit_strength = 0.25 (max бонус к весу)")
    print("  · Погода определяется средним Stress города, не рандомом")
    print("  · avg_stress < 0.35 → золотой свет | 0.35–0.65 → туман | > 0.65 → гроза")
    print("  · Кеш стресса пересчитывается раз в 30 минут (не грузит 134 файла каждый раз)")
    print()
    print("  Бэкапы: _patch_backups/sprint23_block_a/")
    print()
    print("  Следующий шаг — Блок Б: Flash-диалоги встреч с фильтром 'интересности'")
    print("=" * 60)


if __name__ == "__main__":
    main()
