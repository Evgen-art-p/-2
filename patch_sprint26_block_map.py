#!/usr/bin/env python3
"""
patch_sprint26_block_map.py
═══════════════════════════
Спринт 26 · Блок 1 — block_map в manifest.json

ПРОБЛЕМА:
  agent_feedback.py вызывает _build_block_map(agent_ids) — временный протез.
  Знание о структуре цеха должно жить в manifest.json, не в feedback-модуле.

РЕШЕНИЕ:
  1. Добавить "block_map" в manifest.json ВСЕХ 11 цехов
  2. CartridgeManifest.load() читает block_map из manifest
  3. CartridgeRunner передаёт через state["_block_map"]
  4. save_feedback() принимает block_map напрямую — протез → DEPRECATED-заглушка

ЗАПУСК:
  python patch_sprint26_block_map.py

ЦЕХИ (11 штук):
  video_shorts, video_long, turbo, social_mix,
  web_story, living_book, clipmakers, advertising,
  market_hit, logo_design, emo_card
"""

import json
from pathlib import Path

ROOT = Path(".")
MODULES_DIR = ROOT / "studio" / "modules"


# ══════════════════════════════════════════════════════════════
# ШАГ 1 — block_map для каждого цеха
#
# Логика именования блоков: QA-агент пишет my_output.blocks с этими ключами.
# Для цехов без живых промтов — используем стандартную разбивку PRE/PROD/POST.
# При написании промтов QA (A12/A05/A16) имена блоков должны совпадать.
#
# Структура: {"block_name": ["A01", "A02"]}
# ══════════════════════════════════════════════════════════════

BLOCK_MAPS = {
    # ── 12-агентные стандартные (PRE/PROD/POST) ──────────────

    "video_shorts": {
        "pre_production":  ["A01", "A02"],
        "script":          ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "video_long": {
        "pre_production":  ["A01", "A02"],
        "bible":           ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "social_mix": {
        "strategy":        ["A01", "A02"],
        "content":         ["A03", "A04", "A05", "A06"],
        "production":      ["A07", "A08", "A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "clipmakers": {
        "pre_production":  ["A01", "A02"],
        "concept":         ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "advertising": {
        "pre_production":  ["A01", "A02"],
        "creative":        ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "market_hit": {
        "research":        ["A01", "A02"],
        "content":         ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "logo_design": {
        # stop_after=4, qa_agent=A12 — но реально останавливается после A04
        "brief":           ["A01", "A02"],
        "concept":         ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "emo_card": {
        # stop_after=4, qa_agent=A12 — аналогично logo_design
        "brief":           ["A01", "A02"],
        "design":          ["A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11"],
        "qa":              ["A12"],
    },
    "web_story": {
        # qa_agent=A05 (turbo-режим останавливается после A05)
        "brief":           ["A01", "A02"],
        "script":          ["A03", "A04"],
        "qa":              ["A05"],
        "production":      ["A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11", "A12"],
    },

    # ── Нестандартные ────────────────────────────────────────

    "turbo": {
        # 5 агентов: A01→(A02∥A03)→A04→A05(QA)
        "brief":    ["A01"],
        "content":  ["A02", "A03"],
        "assembly": ["A04"],
        "qa":       ["A05"],
    },
    "living_book": {
        # 18 агентов: GENESIS + PRE + PROD + POST + DELIVERY, QA=A16
        "genesis":         ["A00", "A00a"],
        "pre_production":  ["A01", "A02", "A03", "A04"],
        "production":      ["A05", "A06", "A07", "A08"],
        "post_production": ["A09", "A10", "A11", "A12"],
        "delivery":        ["A13", "A14", "A15"],
        "qa":              ["A16"],
    },
}


def patch_manifests():
    """Добавляет block_map в manifest.json каждого цеха."""
    ok = skipped = 0
    for module_id, block_map in BLOCK_MAPS.items():
        manifest_path = MODULES_DIR / module_id / "manifest.json"
        if not manifest_path.exists():
            print(f"  ⚠  {module_id}/manifest.json не найден — пропускаем")
            continue

        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        if "block_map" in data:
            print(f"  ✓  {module_id}: block_map уже есть")
            skipped += 1
            continue

        data["block_map"] = block_map
        manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        agents_count = sum(len(v) for v in block_map.values())
        print(f"  ✅ {module_id}: block_map добавлен ({len(block_map)} блоков, {agents_count} агентов)")
        ok += 1

    return ok, skipped


# ══════════════════════════════════════════════════════════════
# ШАГ 2 — CartridgeManifest: добавить поле block_map
# ══════════════════════════════════════════════════════════════

CARTRIDGE_PATH = ROOT / "studio" / "cartridge.py"

CARTRIDGE_OLD_FIELD = "    hard_stop: dict = field(default_factory=dict)"
CARTRIDGE_NEW_FIELD = """\
    hard_stop: dict = field(default_factory=dict)

    # Маппинг блоков QA → агенты: {"pre_production": ["A01","A02"], ...}
    # Заменяет _build_block_map() в agent_feedback.py (Спринт 26)
    block_map: dict = field(default_factory=dict)"""

CARTRIDGE_OLD_LOAD = '            hard_stop=data.get("hard_stop", {}),'
CARTRIDGE_NEW_LOAD = '''\
            hard_stop=data.get("hard_stop", {}),
            block_map=data.get("block_map", {}),'''


def patch_cartridge_dataclass():
    text = CARTRIDGE_PATH.read_text(encoding="utf-8")
    changed = False

    if "block_map: dict" not in text:
        if CARTRIDGE_OLD_FIELD in text:
            text = text.replace(CARTRIDGE_OLD_FIELD, CARTRIDGE_NEW_FIELD)
            print("  ✅ cartridge.py: поле block_map добавлено в @dataclass")
            changed = True
        else:
            print("  ⚠  cartridge.py: не найдено место для поля block_map")
    else:
        print("  ✓  cartridge.py: поле block_map уже есть")

    if 'block_map=data.get("block_map"' not in text:
        if CARTRIDGE_OLD_LOAD in text:
            text = text.replace(CARTRIDGE_OLD_LOAD, CARTRIDGE_NEW_LOAD)
            print("  ✅ cartridge.py: block_map добавлен в CartridgeManifest.load()")
            changed = True
        else:
            print("  ⚠  cartridge.py: не найдено место для block_map в load()")
    else:
        print("  ✓  cartridge.py: load() уже читает block_map")

    if changed:
        CARTRIDGE_PATH.write_text(text, encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# ШАГ 3 — CartridgeRunner: передаём block_map через state
# ══════════════════════════════════════════════════════════════

CARTRIDGE_OLD_STATE = (
    '        self.state["_slot_id"] = self.slot_id\n'
    '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч'
)
CARTRIDGE_NEW_STATE = (
    '        self.state["_slot_id"] = self.slot_id\n'
    '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч\n'
    '        # Спринт 26: передаём block_map манифеста в pipeline\n'
    '        self.state["_block_map"] = getattr(self.manifest, "block_map", {})'
)


def patch_cartridge_runner():
    text = CARTRIDGE_PATH.read_text(encoding="utf-8")

    if '"_block_map"' in text:
        print("  ✓  cartridge.py: _block_map уже передаётся в state")
        return

    if CARTRIDGE_OLD_STATE in text:
        text = text.replace(CARTRIDGE_OLD_STATE, CARTRIDGE_NEW_STATE)
        CARTRIDGE_PATH.write_text(text, encoding="utf-8")
        print("  ✅ cartridge.py: CartridgeRunner.run() передаёт _block_map в state")
    else:
        print("  ⚠  cartridge.py: не найден блок инициализации state в run()")


# ══════════════════════════════════════════════════════════════
# ШАГ 4 — pipeline.py: читаем _block_map из state
# ══════════════════════════════════════════════════════════════

PIPELINE_PATH = ROOT / "studio" / "workshop" / "pipeline.py"

PIPELINE_OLD_SAVE = (
    "            save_feedback(client_slug, raw_result, "
    "slot_id=_slot_id_for_fb, agent_ids=_all_run_agents)"
)
PIPELINE_NEW_SAVE = (
    "            _block_map_for_fb = state.get(\"_block_map\", {})\n"
    "            save_feedback(\n"
    "                client_slug, raw_result,\n"
    "                slot_id=_slot_id_for_fb,\n"
    "                agent_ids=_all_run_agents,\n"
    "                block_map=_block_map_for_fb,\n"
    "            )"
)


def patch_pipeline():
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    if "block_map=_block_map_for_fb" in text:
        print("  ✓  pipeline.py: block_map уже передаётся")
        return

    if PIPELINE_OLD_SAVE in text:
        text = text.replace(PIPELINE_OLD_SAVE, PIPELINE_NEW_SAVE)
        PIPELINE_PATH.write_text(text, encoding="utf-8")
        print("  ✅ pipeline.py: save_feedback() получает block_map из state")
    else:
        print("  ⚠  pipeline.py: не найден вызов save_feedback — проверь вручную")


# ══════════════════════════════════════════════════════════════
# ШАГ 5 — agent_feedback.py: принимаем block_map, убираем протез
# ══════════════════════════════════════════════════════════════

FEEDBACK_PATH = ROOT / "studio" / "agent_feedback.py"

FEEDBACK_OLD_SIG = (
    "def save_feedback(client_slug: str, arthur_result: str | dict, "
    "slot_id: str = \"\", agent_ids: list = None):"
)
FEEDBACK_NEW_SIG = (
    "def save_feedback(client_slug: str, arthur_result: str | dict, "
    "slot_id: str = \"\", agent_ids: list = None, block_map: dict = None):"
)

FEEDBACK_OLD_BUILD = (
    "    # Динамический маппинг блоков → агенты\n"
    "    # Строится из agent_ids если передан, иначе fallback на legacy-хардкод\n"
    "    BLOCK_TO_AGENTS = _build_block_map(agent_ids or [])"
)
FEEDBACK_NEW_BUILD = (
    "    # Спринт 26: block_map приходит из manifest.json картриджа.\n"
    "    # Если не передан — пустой dict (universal fallback выше поймает).\n"
    "    BLOCK_TO_AGENTS = block_map or {}"
)

DEPRECATED_STUB = '''

def _build_block_map(agent_ids: list) -> dict:
    """
    DEPRECATED · Спринт 26.
    Протез удалён: block_map теперь живёт в manifest.json каждого цеха.
    Функция оставлена как заглушка для безопасности старых импортов.
    Вырезать окончательно в Спринт 27 после первого реального рана.
    """
    print("[FEEDBACK] ⚠ _build_block_map() вызван — это DEPRECATED протез.")
    print("[FEEDBACK]   Убедись что block_map передаётся в save_feedback().")
    return {}
'''


def patch_feedback():
    text = FEEDBACK_PATH.read_text(encoding="utf-8")
    changed = False

    if "block_map: dict = None" not in text:
        if FEEDBACK_OLD_SIG in text:
            text = text.replace(FEEDBACK_OLD_SIG, FEEDBACK_NEW_SIG)
            print("  ✅ agent_feedback.py: save_feedback() принимает block_map")
            changed = True
        else:
            print("  ⚠  agent_feedback.py: не найдена сигнатура save_feedback")
    else:
        print("  ✓  agent_feedback.py: сигнатура уже обновлена")

    if "BLOCK_TO_AGENTS = block_map or {}" not in text:
        if FEEDBACK_OLD_BUILD in text:
            text = text.replace(FEEDBACK_OLD_BUILD, FEEDBACK_NEW_BUILD)
            print("  ✅ agent_feedback.py: _build_block_map() заменён на block_map or {}")
            changed = True
        else:
            print("  ⚠  agent_feedback.py: не найден BLOCK_TO_AGENTS = _build_block_map")
    else:
        print("  ✓  agent_feedback.py: BLOCK_TO_AGENTS уже обновлён")

    if "DEPRECATED · Спринт 26" not in text:
        text += DEPRECATED_STUB
        print("  ✅ agent_feedback.py: добавлена DEPRECATED-заглушка _build_block_map()")
        changed = True
    else:
        print("  ✓  agent_feedback.py: заглушка уже есть")

    if changed:
        FEEDBACK_PATH.write_text(text, encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("СПРИНТ 26 · БЛОК 1 — block_map из manifest (все 11 цехов)")
    print("=" * 60)

    print("\n[1/5] Патчим manifest.json всех 11 цехов...")
    added, skipped = patch_manifests()
    print(f"       Добавлено: {added}, уже было: {skipped}")

    print("\n[2/5] Добавляем поле block_map в CartridgeManifest @dataclass...")
    patch_cartridge_dataclass()

    print("\n[3/5] CartridgeRunner.run() → state['_block_map']...")
    patch_cartridge_runner()

    print("\n[4/5] pipeline.py → save_feedback(block_map=...)...")
    patch_pipeline()

    print("\n[5/5] agent_feedback.py → принимаем block_map, протез → DEPRECATED...")
    patch_feedback()

    print("\n" + "=" * 60)
    print("✅ ГОТОВО.")
    print()
    print("ИТОГ:")
    print("  • block_map живёт в manifest.json каждого из 11 цехов")
    print("  • CartridgeManifest.load() читает его автоматически")
    print("  • CartridgeRunner кладёт в state['_block_map'] перед раном")
    print("  • save_feedback() принимает block_map напрямую")
    print("  • _build_block_map() → DEPRECATED-заглушка (безопасно)")
    print()
    print("СЛЕДУЮЩИЙ ШАГ: python patch_sprint26_sparks.py (искрение)")
    print("=" * 60)
