#!/usr/bin/env python3
"""
patch_clipmakers_agents.py
Студия «Шесть пальцев» | Спринт 40

Правит все файлы агентов clipmakers + manifest + hooks.

Что делает:
  manifest.json:
    - run_type: "full" → "clipmakers"
    - qa_agent: "A05" → "A12"
    - checkpoint_after: [] (убираем — хард-стоп Виктора его заменяет)
    - turbo_parallel: [] (убираем — A02 должен отработать до A03)
    - hard_stop: добавляем
    - version: "2.1"

  dna.json (все 12):
    - Resonance_Frequency A12: 0.1 → 0.65 (не может быть почти 0)
    - balance: дифференцируем по характеру агента
    - trigger_keywords: заполняем по роли
    - model: добавляем (claude-haiku-4-5-20251001 — рабочие лошадки)
      A01 Винни и A12 Рекс → claude-sonnet-4-6 (творческий + финальный QA)

  info.json (все 12):
    - model: добавляем если нет

Запуск:
  python patch_clipmakers_agents.py            # dry-run
  python patch_clipmakers_agents.py --apply
"""
import sys, json, shutil
from pathlib import Path

DRY_RUN       = "--apply" not in sys.argv
STUDIO_ROOT   = Path(__file__).parent / "studio"
CLIPMAKERS    = STUDIO_ROOT / "modules" / "clipmakers"
BACKUP_SUFFIX = ".bak_sprint40_agents"

def log(msg): print(f"  {msg}")
def log_action(label):
    print(f"  [{'DRY' if DRY_RUN else 'APP'}] {label}")
def backup(p):
    dst = p.with_suffix(p.suffix + BACKUP_SUFFIX)
    if not DRY_RUN: shutil.copy2(p, dst)

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p, data):
    if not DRY_RUN:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── ДАННЫЕ ПО АГЕНТАМ ───────────────────────────────────────────
# model: haiku = рабочая лошадка, sonnet = творческий/финальный
# balance: GND=деньги, Теплики=тепло/поддержка, Световики=вдохновение
# trigger_keywords: что цепляет агента в городе

AGENT_DATA = {
    "A01": {  # Вайб Винни — Creative Director
        "model": "claude-sonnet-4-6",
        "balance": {"GND": 60.0, "Теплики": 80.0, "Световики": 100.0},
        "trigger_keywords": ["трек", "клип", "концепт", "образ", "музыка", "видение"],
        "Resonance_Frequency": 0.98,
    },
    "A02": {  # Ричи Ритм — Sync Master
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 70.0, "Теплики": 60.0, "Световики": 80.0},
        "trigger_keywords": ["BPM", "ритм", "такт", "sync", "дроп", "склейка", "бит"],
        "Resonance_Frequency": 0.99,
    },
    "A03": {  # Стори Стив — Storyboard Artist
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 65.0, "Теплики": 70.0, "Световики": 90.0},
        "trigger_keywords": ["кадр", "сцена", "раскадровка", "герой", "крупный план"],
        "Resonance_Frequency": 0.72,
    },
    "A04": {  # Лока Лотти — Location Scout
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 80.0, "Теплики": 90.0, "Световики": 70.0},
        "trigger_keywords": ["локация", "место", "пространство", "атмосфера", "фактура"],
        "Resonance_Frequency": 0.85,
    },
    "A05": {  # Стелла Стайл — Art Director
        "model": "claude-sonnet-4-6",
        "balance": {"GND": 55.0, "Теплики": 75.0, "Световики": 95.0},
        "trigger_keywords": ["стиль", "образ", "костюм", "палитра", "мудборд", "визуал"],
        "Resonance_Frequency": 0.88,
    },
    "A06": {  # Гимбал Гас — Camera
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 75.0, "Теплики": 55.0, "Световики": 75.0},
        "trigger_keywords": ["камера", "ракурс", "движение", "план", "кадр", "гимбал"],
        "Resonance_Frequency": 0.70,
    },
    "A07": {  # Люмен Люк — Lighting
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 65.0, "Теплики": 70.0, "Световики": 100.0},
        "trigger_keywords": ["свет", "тень", "блик", "прожектор", "контраст", "температура"],
        "Resonance_Frequency": 0.78,
    },
    "A08": {  # Дрон Дэн — Aerial
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 80.0, "Теплики": 40.0, "Световики": 65.0},
        "trigger_keywords": ["дрон", "высота", "орбита", "полёт", "масштаб", "панорама"],
        "Resonance_Frequency": 0.78,
    },
    "A09": {  # Лютер Лут — Colorist
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 70.0, "Теплики": 65.0, "Световики": 85.0},
        "trigger_keywords": ["цвет", "грейд", "LUT", "палитра", "тон", "насыщенность"],
        "Resonance_Frequency": 0.92,
    },
    "A10": {  # Джиджи Глитч — VFX
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 70.0, "Теплики": 60.0, "Световики": 90.0},
        "trigger_keywords": ["VFX", "эффект", "глитч", "частицы", "переход", "маска"],
        "Resonance_Frequency": 0.88,
    },
    "A11": {  # Бьюти Белла — Retouch
        "model": "claude-haiku-4-5-20251001",
        "balance": {"GND": 60.0, "Теплики": 85.0, "Световики": 80.0},
        "trigger_keywords": ["ретушь", "кожа", "обложка", "финал", "hero", "детали"],
        "Resonance_Frequency": 0.75,
    },
    "A12": {  # Рендер Рекс — Technical Lead & Final QA
        "model": "claude-sonnet-4-6",
        "balance": {"GND": 90.0, "Теплики": 30.0, "Световики": 50.0},
        "trigger_keywords": ["рендер", "QA", "финал", "артефакт", "качество", "сборка"],
        "Resonance_Frequency": 0.65,  # был 0.1 — критично низко
    },
}


# ─── MANIFEST ────────────────────────────────────────────────────

HARD_STOP = {
    "after_agent": "A03",
    "residents": ["victor"],
    "knowledge": ["29_Music_Video_Grammar.txt", "04_Audio_Aesthetics.txt"],
    "web_search": True
}

def patch_manifest():
    print("\n[1] manifest.json")
    p = CLIPMAKERS / "manifest.json"
    if not p.exists():
        log("❌ не найден"); return

    data = read_json(p)
    changed = []

    checks = [
        ("run_type",       data.get("run_type"),      "clipmakers"),
        ("qa_agent",       data.get("qa_agent"),       "A12"),
        ("version",        data.get("version"),        "2.1"),
        ("checkpoint_after", data.get("checkpoint_after"), []),
        ("turbo_parallel", data.get("turbo_parallel"), []),
        ("hard_stop",      data.get("hard_stop", {}),  HARD_STOP),
    ]

    for key, current, target in checks:
        if current != target:
            log_action(f'{key}: {json.dumps(current)} → {json.dumps(target)}')
            data[key] = target
            changed.append(key)

    if not changed:
        log("✓ manifest.json уже корректен")
        return

    if not DRY_RUN:
        backup(p)
        write_json(p, data)
        log(f"✅ manifest.json ({', '.join(changed)})")


# ─── DNA.JSON ────────────────────────────────────────────────────

def patch_dna():
    print("\n[2] dna.json — все 12 агентов")

    for agent_id, cfg in AGENT_DATA.items():
        p = CLIPMAKERS / agent_id / "dna.json"
        if not p.exists():
            log(f"❌ {agent_id}/dna.json не найден"); continue

        data   = read_json(p)
        changed = []

        # model
        if data.get("model") != cfg["model"]:
            log_action(f"{agent_id} model: → {cfg['model']}")
            data["model"] = cfg["model"]
            changed.append("model")

        # Resonance_Frequency в static
        static = data.setdefault("static", {})
        if static.get("Resonance_Frequency") != cfg["Resonance_Frequency"]:
            if static.get("Resonance_Frequency") != cfg["Resonance_Frequency"]:
                log_action(f"{agent_id} Resonance_Frequency: "
                           f"{static.get('Resonance_Frequency')} → {cfg['Resonance_Frequency']}")
                static["Resonance_Frequency"] = cfg["Resonance_Frequency"]
                changed.append("Resonance_Frequency")

        # balance
        if data.get("balance") != cfg["balance"]:
            log_action(f"{agent_id} balance: → {cfg['balance']}")
            data["balance"] = cfg["balance"]
            changed.append("balance")

        # trigger_keywords
        res = data.setdefault("resonance", {})
        if res.get("trigger_keywords") != cfg["trigger_keywords"]:
            log_action(f"{agent_id} trigger_keywords: → {cfg['trigger_keywords']}")
            res["trigger_keywords"] = cfg["trigger_keywords"]
            changed.append("trigger_keywords")

        if not changed:
            log(f"✓ {agent_id}/dna.json уже корректен")
            continue

        if not DRY_RUN:
            backup(p)
            write_json(p, data)
            log(f"✅ {agent_id}/dna.json ({', '.join(changed)})")


# ─── INFO.JSON ───────────────────────────────────────────────────

def patch_info():
    print("\n[3] info.json — model поле")

    for agent_id, cfg in AGENT_DATA.items():
        p = CLIPMAKERS / agent_id / "info.json"
        if not p.exists():
            log(f"❌ {agent_id}/info.json не найден"); continue

        data = read_json(p)
        if data.get("model") == cfg["model"]:
            continue

        log_action(f"{agent_id} model: → {cfg['model']}")
        data["model"] = cfg["model"]

        if not DRY_RUN:
            backup(p)
            write_json(p, data)
            log(f"✅ {agent_id}/info.json")


# ─── HOOKS.PY ПРОВЕРКА ───────────────────────────────────────────

def check_hooks():
    print("\n[4] hooks.py — проверка")
    p = CLIPMAKERS / "hooks.py"
    if not p.exists():
        log("❌ hooks.py не найден — примени patch_clipmakers_launch.py --apply")
        return

    content = p.read_text(encoding="utf-8")
    checks = {
        "on_before_agent":         "on_before_agent",
        "on_after_agent":          "on_after_agent",
        "A06 fal.ai генерация":    "_gus_generate_frames",
        "A08 дрон генерация":      "_dan_generate_aerial",
        "A11 hero-кадры":          "_bella_generate_covers",
        "A12 петля":               "_rex_close_loop",
        "Монтажёр":                "run_monteur_assembly",
        "ОТК клипов":              "_otk_clips",
        "billing_ledger":          "billing_ledger",
        "strategy_registry":       "strategy_registry",
        "ministry":                "ministry",
        "city_pulse work_end":     "log_work_end",
        "timecode sort":           "_tc_to_sec",
        "хард-стоп Виктора":       "NEEDS_REWORK",
        "history_dna инъекция":    "_inject_history_dna",
    }
    all_ok = True
    for label, needle in checks.items():
        found = needle in content
        print(f"  {'✅' if found else '❌'} {label}")
        if not found: all_ok = False

    if all_ok:
        log("✅ hooks.py — все ключевые функции на месте")
    else:
        log("⚠ hooks.py неполный — примени patch_clipmakers_launch.py --apply")


# ─── ФИНАЛЬНАЯ ПРОВЕРКА ──────────────────────────────────────────

def final_check():
    print("\n[Итоговая проверка]")

    # manifest
    mp = CLIPMAKERS / "manifest.json"
    if mp.exists():
        data = read_json(mp)
        checks = [
            ("run_type == clipmakers",  data.get("run_type") == "clipmakers"),
            ("qa_agent == A12",         data.get("qa_agent") == "A12"),
            ("checkpoint_after пуст",   data.get("checkpoint_after") == []),
            ("turbo_parallel пуст",     data.get("turbo_parallel") == []),
            ("hard_stop есть",          bool(data.get("hard_stop"))),
            ("version == 2.1",          data.get("version") == "2.1"),
        ]
        for label, ok in checks:
            print(f"  {'✅' if ok else '❌'} manifest: {label}")

    # dna — проверяем A12 Resonance_Frequency
    rp = CLIPMAKERS / "A12" / "dna.json"
    if rp.exists():
        data = read_json(rp)
        rf = data.get("static", {}).get("Resonance_Frequency", 0)
        print(f"  {'✅' if rf >= 0.5 else '❌'} A12 Resonance_Frequency = {rf}")
        model = data.get("model", "")
        print(f"  {'✅' if model else '❌'} A12 model = {model or 'НЕТ'}")

    # model у всех агентов
    missing_model = []
    for agent_id in AGENT_DATA:
        dp = CLIPMAKERS / agent_id / "dna.json"
        if dp.exists():
            data = read_json(dp)
            if not data.get("model"):
                missing_model.append(agent_id)
    if missing_model:
        print(f"  ❌ model отсутствует: {missing_model}")
    else:
        print(f"  ✅ model задан у всех 12 агентов")


# ─── main ────────────────────────────────────────────────────────

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*60}")
    print(f"  patch_clipmakers_agents.py  [{mode}]")
    print(f"{'='*60}")

    patch_manifest()
    patch_dna()
    patch_info()
    check_hooks()
    final_check()

    print(f"\n{'='*60}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_clipmakers_agents.py --apply")
    else:
        print("  ✅ Все агенты обновлены.")
        print("  manifest v2.1: run_type + qa_agent + hard_stop + checkpoint убран")
        print("  dna.json: model + balance + trigger_keywords + Resonance_Frequency")
        print("  info.json: model поле")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
