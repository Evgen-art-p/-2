"""
patch_trading_workshop.py
=========================
Студия «Шесть Пальцев» · 2026-06-09

ШАГ 1 — регистрация Торгового Цеха в городе.

Что делает:
  1. Добавляет "trading" в WORKSHOP_OPTIONS в ui_registry.py
     → Страница Жизни видит цех в дропдауне и может рожать агентов штатно
  2. Создаёт каркас папок studio/modules/trading/
  3. Кладёт manifest.json и CHAIN_CONTRACT.md
  4. Создаёт пустые forge/ папки для 9 агентов (A01–A09)
  5. Создаёт economy/data/ если не существует
     (для interaction_log_trading.jsonl и atlas_trading.jsonl)

После запуска:
  → Открыть Страницу Жизни (/registry)
  → В дропдауне "Цех" появится "trading"
  → Рожать агентов A01–A09 штатно через форму

Запуск из корня проекта:
  python patch_trading_workshop.py

Безопасность:
  - ui_registry.py: только одна строка меняется (WORKSHOP_OPTIONS)
  - Существующие файлы НЕ перезаписываются
  - Бэкап ui_registry.py создаётся автоматически
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════

REGISTRY_FILE   = Path("ui_registry.py")
MODULES_DIR     = Path("studio/modules")
TRADING_DIR     = MODULES_DIR / "trading"
ECONOMY_DIR     = Path("economy/data")
BACKUP_DIR      = Path("_patch_backups")

AGENTS = [
    ("A01", "Искра"),
    ("A02", "Морж"),
    ("A03", "Паникёр"),
    ("A04", "Ганс"),
    ("A05", "Архивариус"),
    ("A06", "Брут"),
    ("A07", "Авантюрист"),
    ("A08", "Консерватор"),
    ("A09", "Исполнитель"),
]

MANIFEST = {
    "id":          "trading",
    "label":       "⚔️ Торговый Цех",
    "icon":        "⚔️",
    "version":     "1.0",
    "description": "Военный Совет: 4 сенсора → память → 3 трейдера параллельно → исполнение. Вердикт: входить или нет.",
    "run_type":    "trading",
    "phases": {
        "SENSORS":   ["A01", "A02", "A03", "A04"],
        "MEMORY":    ["A05"],
        "TRIBUNAL":  ["A06", "A07", "A08"],
        "EXECUTION": ["A09"]
    },
    "turbo_parallel": [["A06", "A07", "A08"]],
    "qa_agent":         "A09",
    "checkpoint_after": [],
    "stop_after":       None,
    "conflict_mode":    "none",
    "hard_stop":        {},
    "interaction_log":  "economy/data/interaction_log_trading.jsonl",
    "memory_layers":    ["personal", "project", "runtime", "interaction"],
    "notes": [
        "A04 Ганс: запускается только если t1_status=CONFIRMED и wave_1_validated=true (gate в hooks.py)",
        "A06/A07/A08: параллельно через turbo_parallel, каждый своё решение и magic number",
        "Хард-стоп: если все трое REJECTED → hooks.py возвращает action:stop из on_after_agent A09",
        "Если хотя бы один APPROVED → его ордер идёт. Исполнитель читает state[results][A06/A07/A08]",
        "Paper trading обязателен до первого реального ордера"
    ]
}

CHAIN_CONTRACT = '''# КОНТРАКТ КЛЮЧЕЙ — ТОРГОВЫЙ ЦЕХ v1.0
## studio/modules/trading/CHAIN_CONTRACT.md
## Студия «Шесть Пальцев» · 2026-06-09

> Это единственный источник правды для contract_validator.
> Каждый агент пишет строго то что указано в "Пишет".
> Каждый агент читает строго то что указано в "Читает".
> Ключи в backtick-ах — парсер читает только их.

---

## СВОДНАЯ ТАБЛИЦА

| Агент | Пишет | Читает |
|-------|-------|--------|
| A01 Морж | `morj_status`, `alligator_state`, `wave_1_validated`, `history_dna` | `market_data`, `history_dna` |
| A02 Искра | `t1_status`, `divergence`, `zero_cross_up`, `zero_point_price`, `exit_bell` | `market_data`, `morj_status`, `history_dna` |
| A03 Паникёр | `panic_phase`, `crowd_sentiment`, `action_for_traders` | `market_data`, `t1_status`, `morj_status` |
| A04 Ганс | `fractal_detected`, `fractal_outside_jaw`, `absorption_ratio`, `entry_trigger` | `market_data`, `t1_status`, `wave_1_validated`, `morj_status` |
| A05 Архивариус | `sample_size`, `success_rate`, `top_failure_reason`, `arkhiv_confidence` | `t1_status`, `morj_status`, `panic_phase`, `fractal_detected`, `entry_trigger` |
| A06 Брут | `brut_verdict`, `brut_reason`, `brut_entry`, `brut_stop`, `brut_tp`, `brut_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate`, `arkhiv_confidence` |
| A07 Авантюрист | `avan_verdict`, `avan_reason`, `avan_entry`, `avan_stop`, `avan_tp`, `avan_lot` | `t1_status`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate` |
| A08 Консерватор | `cons_verdict`, `cons_reason`, `cons_entry`, `cons_stop`, `cons_tp`, `cons_lot` | `t1_status`, `wave_1_validated`, `morj_status`, `panic_phase`, `entry_trigger`, `sample_size`, `success_rate`, `arkhiv_confidence` |
| A09 Исполнитель | `execution_log`, `final_dna`, `history_dna`, `deliverables` | `brut_verdict`, `avan_verdict`, `cons_verdict`, `brut_entry`, `brut_stop`, `brut_lot`, `avan_entry`, `avan_stop`, `avan_lot`, `cons_entry`, `cons_stop`, `cons_lot` |

---

## GATE-ПРАВИЛА (реализуются в hooks.py)

```
GATE 1 — Ганс:
  if t1_status != "CONFIRMED" or wave_1_validated != true:
      A04 пропускается, entry_trigger = false (дефолт)

GATE 2 — Хард-стоп:
  if brut_verdict == "REJECTED"
  and avan_verdict == "REJECTED"
  and cons_verdict == "REJECTED":
      on_after_agent A09 → {"action": "stop"}
      запись в Атлас Ошибок (economy/data/atlas_trading.jsonl)

GATE 3 — Авантюрист:
  Единственный кто может дать APPROVED при t1_status = "DETECTED"
  (до пересечения нуля). Это его архитектурное право.
```

---

## СТРУКТУРЫ КЛЮЧЕЙ (краткие)

### market_data (вход, пишет hooks.py)
```json
{
  "symbol": "XAUUSD", "timeframe": "H4", "bar_time": "...",
  "alligator": {"jaw": 0.0, "teeth": 0.0, "lips": 0.0, "sleeping": false},
  "ao": {"value": 0.0, "prev_value": 0.0, "crossed_zero": false},
  "ac": {"value": 0.0, "direction": "UP"},
  "mfi": {"type": "SQUAT", "volume": 0, "spread": 0.0},
  "price": {"high": 0.0, "low": 0.0, "close": 0.0},
  "divergence_ao": false
}
```

### t1_status (A02 Искра)
`NOT_FOUND` | `DETECTED` | `CONFIRMED`
CONFIRMED возможен только после DETECTED.

### morj_status (A01 Морж)
`SLEEPING` | `WAKING` | `AWAKE` | `MATURE`
Консерватор требует `MATURE` (Аллигатор открыт ≥ 8 баров).

### panic_phase (A03 Паникёр)
`DISBELIEF` | `FOMO` | `LIQUIDATION` | `NEUTRAL`

### entry_trigger (A04 Ганс)
true только если fractal_detected=true И fractal_outside_jaw=true

### brut_verdict / avan_verdict / cons_verdict
`APPROVED` | `REJECTED`

### execution_log (A09 Исполнитель)
```json
[{
  "trader": "BRUT", "magic": 100001,
  "verdict": "APPROVED", "entry": 0.0, "stop": 0.0, "tp": 0.0, "lot": 0.33,
  "status": "PAPER", "pnl": null
}]
```
status: `PAPER` | `LIVE` | `SKIPPED`

---

## АТЛАС ОШИБОК
Файл: `economy/data/atlas_trading.jsonl` (append-only)
Читает: A05 Архивариус.
Пишет: A09 Исполнитель (при каждом REJECTED или закрытой сделке).

---

*CHAIN_CONTRACT v1.0 · Торговый Цех · 2026-06-09*
*Заморозить после первого полного прогона на истории*
'''

# ═══════════════════════════════════════════════════
# ШАГИ
# ═══════════════════════════════════════════════════

def step1_patch_registry():
    """Добавляет 'trading' в WORKSHOP_OPTIONS в ui_registry.py."""
    print("\n[ШАГ 1] Патчим ui_registry.py...")

    if not REGISTRY_FILE.exists():
        print(f"  ❌ Файл не найден: {REGISTRY_FILE}")
        return False

    content = REGISTRY_FILE.read_text(encoding="utf-8")

    # Проверяем — уже добавлен?
    if '"trading"' in content:
        print("  ℹ️  'trading' уже есть в WORKSHOP_OPTIONS — пропускаем")
        return True

    # Бэкап
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"ui_registry_{ts}.py"
    shutil.copy2(REGISTRY_FILE, backup)
    print(f"  💾 Бэкап: {backup}")

    # Патч — добавляем "trading" после "clipmakers"
    OLD = '    "clipmakers", "advertising",'
    NEW = '    "clipmakers", "trading", "advertising",'

    if OLD not in content:
        # fallback — добавляем перед последней кавычкой в списке
        OLD = '    "living_book",\n]'
        NEW = '    "living_book",\n    "trading",\n]'

    if OLD not in content:
        print("  ❌ Не могу найти место для вставки в WORKSHOP_OPTIONS")
        print("     Добавь 'trading' вручную в список WORKSHOP_OPTIONS")
        return False

    new_content = content.replace(OLD, NEW, 1)
    REGISTRY_FILE.write_text(new_content, encoding="utf-8")
    print("  ✅ 'trading' добавлен в WORKSHOP_OPTIONS")
    return True


def step2_create_structure():
    """Создаёт каркас папок studio/modules/trading/."""
    print("\n[ШАГ 2] Создаём каркас цеха...")

    TRADING_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  📁 {TRADING_DIR}")

    # manifest.json
    manifest_path = TRADING_DIR / "manifest.json"
    if manifest_path.exists():
        print(f"  ℹ️  manifest.json уже существует — не перезаписываем")
    else:
        manifest_path.write_text(
            json.dumps(MANIFEST, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  ✅ manifest.json")

    # CHAIN_CONTRACT.md
    contract_path = TRADING_DIR / "CHAIN_CONTRACT.md"
    if contract_path.exists():
        print(f"  ℹ️  CHAIN_CONTRACT.md уже существует — не перезаписываем")
    else:
        contract_path.write_text(CHAIN_CONTRACT, encoding="utf-8")
        print(f"  ✅ CHAIN_CONTRACT.md")

    # forge/ папки для 9 агентов
    print("\n[ШАГ 3] Создаём папки агентов...")
    for agent_id, agent_name in AGENTS:
        agent_dir = TRADING_DIR / agent_id
        forge_dir = agent_dir / "forge"
        forge_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = forge_dir / "prompt.md"
        if not prompt_path.exists():
            prompt_path.write_text(
                f"# {agent_id} {agent_name} — промпт не написан\n"
                f"# Родить агента через Страницу Жизни (/registry)\n"
                f"# Затем написать forge/prompt.md (ШАГ 3 дорожной карты)\n",
                encoding="utf-8"
            )

        print(f"  📁 {agent_dir} ({agent_name}) → forge/prompt.md")

    return True


def step3_economy_dirs():
    """Создаёт economy/data/ если не существует."""
    print("\n[ШАГ 4] Проверяем economy/data/...")

    ECONOMY_DIR.mkdir(parents=True, exist_ok=True)

    # Пустой atlas_trading.jsonl
    atlas = ECONOMY_DIR / "atlas_trading.jsonl"
    if not atlas.exists():
        atlas.write_text("", encoding="utf-8")
        print(f"  ✅ {atlas} (пустой)")
    else:
        print(f"  ℹ️  {atlas} уже существует")

    # Пустой interaction_log_trading.jsonl
    log = ECONOMY_DIR / "interaction_log_trading.jsonl"
    if not log.exists():
        log.write_text("", encoding="utf-8")
        print(f"  ✅ {log} (пустой)")
    else:
        print(f"  ℹ️  {log} уже существует")

    return True


def verify():
    """Проверяем что всё на месте."""
    print("\n[ПРОВЕРКА]")
    ok = True

    checks = [
        TRADING_DIR / "manifest.json",
        TRADING_DIR / "CHAIN_CONTRACT.md",
        ECONOMY_DIR / "atlas_trading.jsonl",
        ECONOMY_DIR / "interaction_log_trading.jsonl",
    ] + [TRADING_DIR / agent_id / "forge" / "prompt.md" for agent_id, _ in AGENTS]

    for path in checks:
        exists = path.exists()
        mark = "✅" if exists else "❌"
        print(f"  {mark} {path}")
        if not exists:
            ok = False

    # Проверяем патч в ui_registry.py
    if REGISTRY_FILE.exists():
        content = REGISTRY_FILE.read_text(encoding="utf-8")
        if '"trading"' in content:
            print(f"  ✅ ui_registry.py: 'trading' в WORKSHOP_OPTIONS")
        else:
            print(f"  ❌ ui_registry.py: 'trading' НЕ найден в WORKSHOP_OPTIONS")
            ok = False

    return ok


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("  PATCH: Торговый Цех — ШАГ 1")
    print("  Студия «Шесть Пальцев» · 2026-06-09")
    print("=" * 55)

    ok1 = step1_patch_registry()
    ok2 = step2_create_structure()
    ok3 = step3_economy_dirs()
    all_ok = verify()

    print("\n" + "=" * 55)
    if all_ok:
        print("  ✅ ГОТОВО. Торговый Цех зарегистрирован.")
        print()
        print("  Следующие шаги:")
        print("  1. Перезапустить студию (main.py)")
        print("  2. Открыть /registry → Страница Жизни")
        print("  3. В дропдауне 'Цех' выбрать 'trading'")
        print("  4. Родить 9 агентов через Страницу Жизни:")
        print("     A01 Искра, A02 Морж, A03 Паникёр, A04 Ганс,")
        print("     A05 Архивариус, A06 Брут, A07 Авантюрист,")
        print("     A08 Консерватор, A09 Исполнитель")
        print("  5. После рождения — писать forge/prompt.md")
        print("     (ШАГ 3 дорожной карты)")
    else:
        print("  ⚠️  Есть проблемы — проверь вывод выше")
    print("=" * 55)
