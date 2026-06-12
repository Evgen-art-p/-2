# patch_quarter_field.py
# ═══════════════════════════════════════════════════════════════
# КВАРТАЛ — два шага:
#
# ШАГ 1: Проставляет поле Quarter во все существующие объекты
#   каталога (catalog.json). 157 объектов без потери данных.
#
# ШАГ 2: Добавляет в ui_registry.py (Страница Жизни):
#   а) Для ЛОКАЦИИ — выбор квартала (select) в блоке «Место в Грондхейме»
#   б) Для АГЕНТА  — выбор квартала (select) в блоке «Цифровая ДНК»,
#      + автозаполнение по Workshop_ID при выборе цеха
#   в) generate_agent_files() пишет quarter в dna.json и info.json
#
# После патча новые агенты и локации сразу получают квартал.
# Карта Кабинета начнёт группировать по нему.
#
# Запуск: python patch_quarter_field.py
# ═══════════════════════════════════════════════════════════════

import json
import shutil
import py_compile
from datetime import datetime
from pathlib import Path

CATALOG_FILE   = Path("00_REGISTRY_NFT/catalog.json")
REGISTRY_FILE  = Path("studio/ui_registry.py")
BACKUP_DIR     = Path("_patch_backups")

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ── Карта локаций → квартал ──────────────────────────────────────
LOCATION_QUARTER = {
    "Грондхейм":                    "",                   # фон, не квартал
    'Студия "Шесть Пальцев"':       "Квартал Мастеров",
    "Площадь Резонанса":            "Квартал Мастеров",
    "Гавань Смыслов":               "Квартал Мастеров",
    "Квартал Мастеров":             "Квартал Мастеров",
    "Маяк Пробуждения":             "Квартал Мастеров",
    "Высотка":                      "Квартал Мастеров",
    "Храм Пробуждения - Гексагон":  "Квартал Мастеров",
    "Замок Сов":                    "Квартал Мастеров",
    "Павильон Жидкого Времени":     "Квартал Мастеров",
    "Artifacts & Bugs":             "Квартал Мастеров",
    "Библиотека Смыслов":           "Квартал Мастеров",
    "Таверна «Усталый Пиксель»":    "Квартал Мастеров",
    "Торговый Квартал":             "Торговый Квартал",
    "Биржа":                        "Торговый Квартал",
}

# ── Карта Workshop_ID → квартал агента ──────────────────────────
WORKSHOP_QUARTER = {
    "residents":    "Высотка",
    "turbo":        "Квартал Мастеров",
    "social_mix":   "Квартал Мастеров",
    "video_long":   "Квартал Мастеров",
    "video_shorts": "Квартал Мастеров",
    "web_story":    "Квартал Мастеров",
    "clipmakers":   "Квартал Мастеров",
    "advertising":  "Квартал Мастеров",
    "emo_card":     "Квартал Мастеров",
    "logo_design":  "Квартал Мастеров",
    "market_hit":   "Квартал Мастеров",
    "living_book":  "Квартал Мастеров",
    "trading":      "Торговый Квартал",
}

ALL_QUARTERS = sorted(set(WORKSHOP_QUARTER.values()) | {"Торговый Квартал"})


# ════════════════════════════════════════════════
# ШАГ 1: каталог
# ════════════════════════════════════════════════

def patch_catalog():
    if not CATALOG_FILE.exists():
        print(f"❌ {CATALOG_FILE} не найден")
        return False

    data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))

    # Бэкап
    BACKUP_DIR.mkdir(exist_ok=True)
    bak = BACKUP_DIR / f"catalog.json.bak_quarter_{STAMP}"
    shutil.copy2(CATALOG_FILE, bak)
    print(f"📦 Бэкап каталога: {bak}")

    patched = 0
    for obj in data:
        cls  = obj.get("Object_Type_Class", "")
        name = obj.get("Official_Name", "")

        if cls in ("location",) or obj.get("Object_Type") == "Location":
            q = LOCATION_QUARTER.get(name, "")
            obj["Quarter"] = q
            patched += 1
        elif cls == "agent":
            ws = obj.get("Workshop_ID", "")
            obj["Quarter"] = WORKSHOP_QUARTER.get(ws, "Квартал Мастеров")
            patched += 1

    CATALOG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✏️  Каталог: {patched} объектов получили поле Quarter")
    return True


# ════════════════════════════════════════════════
# ШАГ 2: ui_registry.py
# ════════════════════════════════════════════════

def patch_registry():
    if not REGISTRY_FILE.exists():
        print(f"❌ {REGISTRY_FILE} не найден")
        return False

    text = REGISTRY_FILE.read_text(encoding="utf-8")

    # ── Идемпотентность ──
    if "Quarter_widget" in text:
        print("✅ ui_registry.py уже содержит Quarter — пропускаем")
        return True

    BACKUP_DIR.mkdir(exist_ok=True)
    bak = BACKUP_DIR / f"ui_registry.py.bak_quarter_{STAMP}"
    shutil.copy2(REGISTRY_FILE, bak)
    print(f"📦 Бэкап реестра: {bak}")

    changed = 0

    # ── 2a: объявление переменной виджета после loc_neighbors_widget ──
    OLD_A = "                  loc_neighbors_widget = {\"w\": None}"
    NEW_A = (
        "                  loc_neighbors_widget = {\"w\": None}\n"
        "                  loc_quarter_widget = {\"w\": None}   # Quarter локации\n"
        "                  agent_quarter_widget = {\"w\": None} # Quarter агента"
    )
    if OLD_A in text:
        text = text.replace(OLD_A, NEW_A, 1)
        changed += 1
        print("  ✏️  [2a] объявлены loc_quarter_widget / agent_quarter_widget")

    # ── 2b: select квартала в блоке ЛОКАЦИИ — после поля loc_neighbors ──
    OLD_B = (
        "                        # Координаты на карте\n"
        "                        ui.html('''"
    )
    NEW_B = (
        "                        # Квартал локации\n"
        "                        quarter_opts_loc = {\"\": \"— выбрать квартал —\"}\n"
        "                        quarter_opts_loc.update({\n"
        + "".join(f'                            "{q}": "{q}",\n' for q in ALL_QUARTERS)
        + "                        })\n"
        "                        loc_quarter_widget[\"w\"] = ui.select(\n"
        "                            label=\"Квартал города\",\n"
        "                            options=quarter_opts_loc,\n"
        "                        ).classes(\"w-full mb-3\")\n\n"
        "                        # Координаты на карте\n"
        "                        ui.html('''"
    )
    if OLD_B in text:
        text = text.replace(OLD_B, NEW_B, 1)
        changed += 1
        print("  ✏️  [2b] select квартала добавлен в блок ЛОКАЦИИ")

    # ── 2c: select квартала в блоке АГЕНТА — после trigger_keywords ──
    # Вставляем после блока триггеров, перед «Статические веса»
    OLD_C = (
        "                        # Статические веса\n"
        "                        ui.html('<div style=\"font-size:0.72rem"
    )
    NEW_C = (
        "                        # Квартал агента (автозаполняется по цеху)\n"
        "                        quarter_opts_agent = {\"\": \"— выбрать квартал —\"}\n"
        "                        quarter_opts_agent.update({\n"
        + "".join(f'                            "{q}": "{q}",\n' for q in ALL_QUARTERS)
        + "                        })\n"
        "                        agent_quarter_widget[\"w\"] = ui.select(\n"
        "                            label=\"Квартал города\",\n"
        "                            options=quarter_opts_agent,\n"
        "                        ).classes(\"w-full mb-3\")\n\n"
        "                        # Статические веса\n"
        "                        ui.html('<div style=\"font-size:0.72rem"
    )
    if OLD_C in text:
        text = text.replace(OLD_C, NEW_C, 1)
        changed += 1
        print("  ✏️  [2c] select квартала добавлен в блок АГЕНТА (ДНК)")

    # ── 2d: автозаполнение квартала при выборе цеха ──
    WORKSHOP_QUARTER_STR = json.dumps(WORKSHOP_QUARTER, ensure_ascii=False)
    OLD_D = "                                def on_workshop_change(e):\n                                    ws = e.value or \"\""
    NEW_D = (
        "                                _WORKSHOP_QUARTER = "
        + WORKSHOP_QUARTER_STR + "\n"
        "                                def on_workshop_change(e):\n"
        "                                    ws = e.value or \"\""
    )
    if OLD_D in text:
        text = text.replace(OLD_D, NEW_D, 1)
        # Вставляем автозаполнение в тело on_workshop_change
        OLD_D2 = (
            "                                    opts = ROLE_OPTIONS_MAP.get(ws, [\"\"])\n"
            "                                    new_options = {v: v if v else \"— не задана —\" for v in opts}\n"
            "                                    if role_widget[\"w\"]:"
        )
        NEW_D2 = (
            "                                    opts = ROLE_OPTIONS_MAP.get(ws, [\"\"])\n"
            "                                    new_options = {v: v if v else \"— не задана —\" for v in opts}\n"
            "                                    # Автозаполнение квартала по цеху\n"
            "                                    if agent_quarter_widget[\"w\"] and ws:\n"
            "                                        auto_q = _WORKSHOP_QUARTER.get(ws, \"Квартал Мастеров\")\n"
            "                                        agent_quarter_widget[\"w\"].value = auto_q\n"
            "                                        agent_quarter_widget[\"w\"].update()\n"
            "                                    if role_widget[\"w\"]:"
        )
        if OLD_D2 in text:
            text = text.replace(OLD_D2, NEW_D2, 1)
            changed += 1
            print("  ✏️  [2d] автозаполнение квартала при выборе цеха")

    # ── 2e: collect_form() — читаем Quarter ──
    OLD_E = "                    if t == \"agent\":\n                        if workshop_widget[\"w\"]: obj[\"Workshop_ID\"] = workshop_widget[\"w\"].value or \"\""
    NEW_E = (
        "                    if t == \"agent\":\n"
        "                        if agent_quarter_widget[\"w\"]: obj[\"Quarter\"] = agent_quarter_widget[\"w\"].value or \"\"\n"
        "                        if workshop_widget[\"w\"]: obj[\"Workshop_ID\"] = workshop_widget[\"w\"].value or \"\""
    )
    if OLD_E in text:
        text = text.replace(OLD_E, NEW_E, 1)
        changed += 1
        print("  ✏️  [2e] collect_form: читаем Quarter агента")

    OLD_E2 = "                    elif t == \"location\":\n                        if loc_capacity_widget[\"w\"]:"
    NEW_E2 = (
        "                    elif t == \"location\":\n"
        "                        if loc_quarter_widget[\"w\"]: obj[\"Quarter\"] = loc_quarter_widget[\"w\"].value or \"\"\n"
        "                        if loc_capacity_widget[\"w\"]:"
    )
    if OLD_E2 in text:
        text = text.replace(OLD_E2, NEW_E2, 1)
        changed += 1
        print("  ✏️  [2e2] collect_form: читаем Quarter локации")

    # ── 2f: populate_form() — восстанавливаем Quarter при редактировании ──
    OLD_F = "                    if t == \"agent\":\n                        if workshop_widget[\"w\"]: workshop_widget[\"w\"].value = obj.get(\"Workshop_ID\", \"\")"
    NEW_F = (
        "                    if t == \"agent\":\n"
        "                        if agent_quarter_widget[\"w\"]: agent_quarter_widget[\"w\"].value = obj.get(\"Quarter\", \"\")\n"
        "                        if workshop_widget[\"w\"]: workshop_widget[\"w\"].value = obj.get(\"Workshop_ID\", \"\")"
    )
    if OLD_F in text:
        text = text.replace(OLD_F, NEW_F, 1)
        changed += 1
        print("  ✏️  [2f] populate_form: восстанавливаем Quarter агента")

    OLD_F2 = "                    elif t == \"location\":\n                        if loc_capacity_widget[\"w\"]: loc_capacity_widget[\"w\"].value = obj.get(\"Capacity\", 10)"
    NEW_F2 = (
        "                    elif t == \"location\":\n"
        "                        if loc_quarter_widget[\"w\"]: loc_quarter_widget[\"w\"].value = obj.get(\"Quarter\", \"\")\n"
        "                        if loc_capacity_widget[\"w\"]: loc_capacity_widget[\"w\"].value = obj.get(\"Capacity\", 10)"
    )
    if OLD_F2 in text:
        text = text.replace(OLD_F2, NEW_F2, 1)
        changed += 1
        print("  ✏️  [2f2] populate_form: восстанавливаем Quarter локации")

    # ── 2g: clear_form() — сбрасываем Quarter ──
    OLD_G = "                    for w in [loc_scale_widget, loc_lighting_widget,\n                              loc_atmosphere_widget, loc_neighbors_widget]:"
    NEW_G = (
        "                    if loc_quarter_widget[\"w\"]: loc_quarter_widget[\"w\"].value = \"\"\n"
        "                    if agent_quarter_widget[\"w\"]: agent_quarter_widget[\"w\"].value = \"\"\n"
        "                    for w in [loc_scale_widget, loc_lighting_widget,\n"
        "                              loc_atmosphere_widget, loc_neighbors_widget]:"
    )
    if OLD_G in text:
        text = text.replace(OLD_G, NEW_G, 1)
        changed += 1
        print("  ✏️  [2g] clear_form: сбрасываем Quarter")

    # ── 2h: generate_agent_files() — пишем quarter в dna.json и info.json ──
    OLD_H = '        "workshop": workshop,\n        "role": agent_role,'
    NEW_H = (
        '        "workshop": workshop,\n'
        '        "quarter": obj.get("Quarter", ""),\n'
        '        "role": agent_role,'
    )
    if OLD_H in text:
        text = text.replace(OLD_H, NEW_H, 1)
        changed += 1
        print("  ✏️  [2h] dna.json: quarter записывается при рождении")

    OLD_H2 = '            "workshop": workshop,\n        }'
    NEW_H2 = (
        '            "workshop": workshop,\n'
        '            "quarter": obj.get("Quarter", ""),\n'
        '        }'
    )
    if OLD_H2 in text:
        text = text.replace(OLD_H2, NEW_H2, 1)
        changed += 1
        print("  ✏️  [2h2] info.json: quarter записывается при рождении")

    if changed == 0:
        print("⚠️  Ни одна якорная строка не найдена — файл изменился.")
        print("   Добавь Quarter вручную в блоки ЛОКАЦИИ и АГЕНТА в ui_registry.py")
        return False

    # Записываем
    REGISTRY_FILE.write_text(text, encoding="utf-8")
    print(f"✏️  ui_registry.py: {changed} правок применено")

    # Компиляция
    try:
        py_compile.compile(str(REGISTRY_FILE), doraise=True)
        print("✅ Компиляция ui_registry.py OK")
    except py_compile.PyCompileError as e:
        print(f"❌ Ошибка компиляции, откатываю: {e}")
        shutil.copy2(bak, REGISTRY_FILE)
        return False

    return True


# ════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════

def main():
    print("═" * 60)
    print("ПАТЧ — ПОЛЕ QUARTER (КВАРТАЛ ГОРОДА)")
    print("═" * 60)

    ok1 = patch_catalog()
    print()
    ok2 = patch_registry()

    print()
    print("═" * 60)
    if ok1 and ok2:
        print("ГОТОВО.")
        print("• catalog.json — все объекты получили Quarter")
        print("• ui_registry.py — форма Страницы Жизни обновлена:")
        print("  - при выборе типа АГЕНТ появляется 'Квартал города'")
        print("    (автозаполняется по Workshop_ID)")
        print("  - при выборе типа ЛОКАЦИЯ появляется 'Квартал города'")
        print("  - при рождении квартал пишется в dna.json и info.json")
        print()
        print("Перезапусти студию.")
        print("Карта Кабинета теперь может группировать по кварталам.")
        print("Искра появится в Торговом Квартале, а не среди воркеров Студии.")
    else:
        print("ПАТЧ ПРИМЕНЁН ЧАСТИЧНО — проверь предупреждения выше.")
    print("═" * 60)


if __name__ == "__main__":
    main()
