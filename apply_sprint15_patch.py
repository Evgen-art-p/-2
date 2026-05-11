#!/usr/bin/env python3
"""
apply_sprint15_patch.py
=======================
Спринт 15 — 5 фиксов одним скриптом.

Запускать из корня проекта:
    python apply_sprint15_patch.py

Что делает:
  1. cartridge.py  — conflict_mode добавлен в датакласс и load()
  2. cartridge.py  — _qa_agent = последний агент цеха (не хардкод "A12")
  3. cartridge.py  — Этап 8: field_tracker подключён после summarize_session
  4. pipeline.py   — убран ранний record_strategy с захардкоженным score=7.0
  5. agent_feedback.py — универсальный парсер score (blocks / otk_checklist / status)
                         + параметр agent_ids для не-A12 QA агентов
  6. pipeline.py   — передаём agent_ids в save_feedback()
"""

from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(".")
STUDIO = ROOT / "studio"

CARTRIDGE   = STUDIO / "cartridge.py"
PIPELINE    = STUDIO / "workshop" / "pipeline.py"
FEEDBACK    = STUDIO / "agent_feedback.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

errors = []
applied = []


def backup(path: Path):
    bak = path.with_suffix(path.suffix + f".bak_sprint15_{STAMP}")
    shutil.copy2(path, bak)
    print(f"  💾 Бэкап → {bak.name}")


def patch(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  ⚠️  [{label}] Якорь не найден — пропускаю (уже применён?)")
        return False
    patched = text.replace(old, new, 1)
    path.write_text(patched, encoding="utf-8")
    print(f"  ✅  [{label}] Применён")
    applied.append(label)
    return True


# ════════════════════════════════════════════════════════
# CARTRIDGE.PY
# ════════════════════════════════════════════════════════

print(f"\n📄 Патчим {CARTRIDGE}")
backup(CARTRIDGE)

# --- 1. conflict_mode в датакласс ---
patch(
    CARTRIDGE,
    old='    qa_agent: str = "A12"  # QA-агент цеха, чьи оценки идут в feedback\n\n    # Run type',
    new='    qa_agent: str = "A12"  # QA-агент цеха, чьи оценки идут в feedback\n    conflict_mode: str = "none"  # Режим конфликта из manifest.json\n\n    # Run type',
    label="cartridge/conflict_mode_dataclass",
)

# --- 2. conflict_mode в load() ---
patch(
    CARTRIDGE,
    old='            qa_agent=data.get("qa_agent", "A12"),\n            run_type=data.get("run_type", module_id),\n        )',
    new='            qa_agent=data.get("qa_agent", "A12"),\n            run_type=data.get("run_type", module_id),\n            conflict_mode=data.get("conflict_mode", "none"),\n        )',
    label="cartridge/conflict_mode_load",
)

# --- 3. _qa_agent = динамически последний агент цеха ---
patch(
    CARTRIDGE,
    old='        self.state["_qa_agent"] = getattr(self.manifest, "qa_agent", "A12")',
    new=(
        '        # Динамический QA: если qa_agent не в пайплайне — берём последнего агента\n'
        '        _all_agents = self.manifest.get_all_agents()\n'
        '        _manifest_qa = getattr(self.manifest, "qa_agent", "A12")\n'
        '        self.state["_qa_agent"] = (\n'
        '            _manifest_qa if _manifest_qa in _all_agents\n'
        '            else (_all_agents[-1] if _all_agents else _manifest_qa)\n'
        '        )'
    ),
    label="cartridge/dynamic_qa_agent",
)

# --- 4. Этап 8: field_tracker после summarize_session ---
patch(
    CARTRIDGE,
    old=(
        '        try:\n'
        '            await summarize_session(self.state, client_slug, run_date, run_type)\n'
        '        except Exception as e:\n'
        '            print(f"[CARTRIDGE] Ошибка суммаризации: {e}")\n'
        '\n'
        '    async def run_turbo(self):'
    ),
    new=(
        '        try:\n'
        '            await summarize_session(self.state, client_slug, run_date, run_type)\n'
        '        except Exception as e:\n'
        '            print(f"[CARTRIDGE] Ошибка суммаризации: {e}")\n'
        '\n'
        '        # ══ Этап 8: Culture Formation ══\n'
        '        try:\n'
        '            from studio.culture.field_tracker import CulturalFieldTracker\n'
        '            CulturalFieldTracker().update_slot_field(self.slot_id)\n'
        '            print(f"[CULTURE] ✅ field_tracker обновлён для {self.slot_id}")\n'
        '        except Exception as e:\n'
        '            print(f"[CULTURE] Ошибка field_tracker: {e}")\n'
        '\n'
        '    async def run_turbo(self):'
    ),
    label="cartridge/field_tracker_stage8",
)


# ════════════════════════════════════════════════════════
# PIPELINE.PY
# ════════════════════════════════════════════════════════

print(f"\n📄 Патчим {PIPELINE}")
backup(PIPELINE)

# --- 5. Убрать ранний record_strategy с score=7.0 ---
patch(
    PIPELINE,
    old=(
        '        # ═══ STRATEGY: запись стратегии агента ═══\n'
        '    if _STRATEGY_ENABLED:\n'
        '        _slot_id = state.get("_slot_id") or state.get("active_dept") or ""\n'
        '        print(f"[STRATEGY] Вызываю record_strategy: {worker_id} slot={_slot_id}")\n'
        '        record_strategy(\n'
        '            agent_id=worker_id,\n'
        '            slot_id=_slot_id,\n'
        '            score=7.0,\n'
        '            result_summary=human_text[:300],\n'
        '            run_type=run_type,\n'
        '            client_slug=client_slug,\n'
        '        )\n'
    ),
    new=(
        '        # ═══ STRATEGY: стратегии пишутся только через QA (реальный score) ═══\n'
        '        # record_strategy вызывается в _record_winning_strategies() после QA\n'
    ),
    label="pipeline/remove_early_record_strategy",
)

# --- 6. Передаём agent_ids в save_feedback() ---
patch(
    PIPELINE,
    old=(
        '            _slot_id_for_fb = state.get("_slot_id", "")\n'
        '            save_feedback(client_slug, raw_result, slot_id=_slot_id_for_fb)'
    ),
    new=(
        '            _slot_id_for_fb = state.get("_slot_id", "")\n'
        '            _all_run_agents = list(state.get("results", {}).keys())\n'
        '            save_feedback(client_slug, raw_result, slot_id=_slot_id_for_fb, agent_ids=_all_run_agents)'
    ),
    label="pipeline/save_feedback_agent_ids",
)


# ════════════════════════════════════════════════════════
# AGENT_FEEDBACK.PY
# ════════════════════════════════════════════════════════

print(f"\n📄 Патчим {FEEDBACK}")
backup(FEEDBACK)

# --- 7. Универсальный _extract_score + agent_ids в save_feedback ---

# Добавляем функцию _extract_score перед save_feedback
patch(
    FEEDBACK,
    old='def save_feedback(client_slug: str, arthur_result: str | dict, slot_id: str = ""):',
    new=(
        'def _extract_score(my_output: dict) -> float:\n'
        '    """\n'
        '    Универсальный парсер score из my_output любого QA-агента.\n'
        '    Поддерживает: blocks (A12), otk_checklist (A16), status, прямой score.\n'
        '    """\n'
        '    # Прямой score\n'
        '    if "score" in my_output:\n'
        '        try:\n'
        '            return float(my_output["score"])\n'
        '        except (ValueError, TypeError):\n'
        '            pass\n'
        '\n'
        '    # OTK чеклист: "12/12" → 10.0, "10/12" → 8.3\n'
        '    checklist = my_output.get("otk_checklist", "")\n'
        '    if checklist and "/" in str(checklist):\n'
        '        try:\n'
        '            parts = str(checklist).split("/")\n'
        '            return round(10.0 * int(parts[0]) / int(parts[1]), 1)\n'
        '        except (ValueError, ZeroDivisionError):\n'
        '            pass\n'
        '\n'
        '    # Статус\n'
        '    status = my_output.get("status", "").upper()\n'
        '    status_map = {"READY": 9.0, "OK": 8.0, "INCOMPLETE": 5.0,\n'
        '                  "PARTIAL": 5.0, "FAIL": 2.0, "ERROR": 2.0}\n'
        '    if status in status_map:\n'
        '        return status_map[status]\n'
        '\n'
        '    # Blocks (формат A12) — считаем средний по всем блокам\n'
        '    blocks = my_output.get("blocks", {})\n'
        '    if blocks:\n'
        '        scores = []\n'
        '        for bd in blocks.values():\n'
        '            if isinstance(bd, dict):\n'
        '                checks = bd.get("checks", 0)\n'
        '                passed = bd.get("pass", 0)\n'
        '                if checks > 0:\n'
        '                    scores.append(10 * passed / checks)\n'
        '        if scores:\n'
        '            return round(sum(scores) / len(scores), 1)\n'
        '\n'
        '    return 5.0  # нейтральный дефолт\n'
        '\n'
        '\n'
        'def save_feedback(client_slug: str, arthur_result: str | dict, slot_id: str = "", agent_ids: list = None):'
    ),
    label="feedback/add_extract_score_fn",
)

# Меняем сигнатуру внутри docstring (уже изменена выше) и добавляем fallback
# когда blocks пусты — используем agent_ids + _extract_score
patch(
    FEEDBACK,
    old=(
        '    my_output = data.get("my_output", {})\n'
        '    blocks = my_output.get("blocks", {})\n'
        '    overall = my_output.get("overall_status", "UNKNOWN")\n'
        '    warnings = my_output.get("warnings", [])\n'
        '    critical = my_output.get("critical_issues", [])'
    ),
    new=(
        '    my_output = data.get("my_output", {})\n'
        '    blocks = my_output.get("blocks", {})\n'
        '    overall = my_output.get("overall_status", "UNKNOWN")\n'
        '    warnings = my_output.get("warnings", [])\n'
        '    critical = my_output.get("critical_issues", [])\n'
        '\n'
        '    # ══ Универсальный fallback: если нет blocks — распределяем общий score ══\n'
        '    if not blocks and agent_ids:\n'
        '        universal_score = _extract_score(my_output)\n'
        '        feedback = {\n'
        '            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),\n'
        '            "overall_status": overall or ("READY" if universal_score >= 8 else "OK"),\n'
        '            "agents": {\n'
        '                aid: {"score": universal_score, "problems": [], "blocks_checked": ["universal"]}\n'
        '                for aid in agent_ids\n'
        '            },\n'
        '        }\n'
        '        fp = _feedback_path(client_slug)\n'
        '        fp.parent.mkdir(parents=True, exist_ok=True)\n'
        '        fp.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")\n'
        '        _update_global(feedback, slot_id=slot_id)\n'
        '        print(f"[FEEDBACK] Universal score={universal_score} → {len(agent_ids)} агентов")\n'
        '        return'
    ),
    label="feedback/universal_score_fallback",
)


# ════════════════════════════════════════════════════════
# ИТОГ
# ════════════════════════════════════════════════════════

print(f"\n{'='*55}")
print(f"✅ Применено патчей: {len(applied)}")
for a in applied:
    print(f"   • {a}")
if errors:
    print(f"\n⚠️  Ошибок: {len(errors)}")
    for e in errors:
        print(f"   • {e}")
print(f"\nБэкапы сохранены с суффиксом .bak_sprint15_{STAMP}")
print("Перезапусти студию для применения изменений.")
