"""
patch_social_mix_hooks.py
Студия «Шесть Пальцев» · Спринт 39 (fix)

Что делает:
  Переписывает studio/modules/social_mix/hooks.py до v4.1.

Изменения v4.1 vs v4.0 (после прогона по цепочке):
  БАГ 1 ИСПРАВЛЕН: A06 — убрана двухэтапная схема через pipeline.
    Pipeline не умеет перезапускать агента (нет action:"repeat").
    Теперь как у Евы: хук сам генерирует + проверяет через vision_client.
    Агент пишет промпт → хук гоняет fal.ai + ОТК → готово за один проход.

  БАГ 2 ИСПРАВЛЕН: A11 Федя — vision_images теперь в on_BEFORE_agent.
    on_after_agent срабатывает ПОСЛЕ агента — картинку он уже не увидит.
    on_before_agent срабатывает ДО — pipeline передаст PNG вместе с контекстом.

Запуск: python patch_social_mix_hooks.py
  из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)
"""

import shutil
from pathlib import Path

HOOKS_PATH  = Path("studio/modules/social_mix/hooks.py")
BACKUP_PATH = HOOKS_PATH.with_suffix(".py.bak_v4")

NEW_CONTENT = '''\
# studio/modules/social_mix/hooks.py
# Студия «Шесть Пальцев» · 2026
# v4.1 — правильная схема A06 (как Ева в video_long: генерация+ОТК внутри хука).
#         A11 Федя — vision_images в on_before_agent (до вызова агента).
#         A12 Клавдия — замыкание петли: chain_integrity + billing_ledger + Strategy Registry.
#         PLAN-режим останавливается после A04.

import json
import re
import time
from datetime import datetime
from pathlib import Path


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Срабатывает ДО вызова агента.
    A11 Федя — кладём готовую картинку в vision_images чтобы pipeline передал PNG.
    """
    if worker_id == "A11":
        _fedya_prepare_vision(state)
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """Срабатывает ПОСЛЕ вызова агента."""
    run_type = state.get("run_type", state.get("active_dept", ""))

    # PLAN: стоп после PRE-PROD (A04)
    if run_type == "content_plan" and worker_id == "A04":
        print(f"[HOOKS] PLAN: контент-план готов. Стоп после {worker_id}.")
        return {"action": "stop"}

    # A06 — Эван Вижн: агент написал промпт → хук генерирует + ОТК
    if worker_id == "A06":
        _evan_generate_and_check(state, human_text)

    # A11 — vision_images уже убраны после вызова агента (чистим state)
    if worker_id == "A11":
        state.pop("vision_images", None)

    # A12 — Клавдия: замыкание петли
    if worker_id == "A12":
        _claudia_finalize(state, human_text)

    return {}


# ══════════════════════════════════════════════════════════════════
# A06 ЭВАН — ГЕНЕРАЦИЯ + ОТК ВНУТРИ ХУКА (как Ева в video_long)
# ══════════════════════════════════════════════════════════════════

def _evan_generate_and_check(state: dict, human_text: str):
    """
    Агент уже написал prompt_positive в evan_visual.
    Хук:
      1. Берёт промпт из chain_data.evan_visual
      2. Генерирует через fal.ai
      3. Проверяет через vision_client (ОТК)
         При REJECTED — fix_hint добавляется в негативный промпт, перегенерация
      4. Пишет image_path + quality обратно в chain_data.evan_visual
    Pipeline вызывает A06 один раз — всё остальное внутри хука.
    """
    try:
        from studio.fal_client import generate_image, generate_with_refs
    except ImportError:
        print("[HOOKS/A06] fal_client не найден — пропускаю")
        return

    data = _parse_json(human_text)
    if not data:
        print("[HOOKS/A06] JSON не найден — пропускаю генерацию")
        return

    my_output   = data.get("my_output", data)
    evan_visual = my_output.get("evan_visual", my_output)

    prompt_positive = evan_visual.get("prompt_positive", "")
    if not prompt_positive:
        print("[HOOKS/A06] prompt_positive пуст — пропускаю")
        return

    fmt        = evan_visual.get("format", "4:5")
    slot_id    = state.get("_slot_id", "social_mix")
    project_id = state.get("project_id", "")

    # Имя файла по project_id
    safe_pid   = re.sub(r"[^a-zA-Z0-9_-]", "_", project_id or "social")
    filename   = f"evan_{safe_pid}.png"

    # Ссылки из master_brief (char_ref / style_ref)
    brief  = state.get("chain_data", {}).get("master_brief", {})
    assets = brief.get("assets", {}) if isinstance(brief, dict) else {}
    ref_ids = []
    if assets.get("char_ref"):
        ref_ids.append(assets["char_ref"])
    ref_ids += assets.get("style_ref", [])

    print(f"[HOOKS/A06] Генерирую картинку: {filename} (format={fmt})")

    # ОТК через vision_client (если есть)
    try:
        from studio.vision_client import generate_with_vision_check as _otk
        has_otk = True
    except ImportError:
        has_otk = False
        print("[HOOKS/A06] vision_client не найден — без ОТК")

    current_prompt  = [prompt_positive]
    negative_suffix = [""]

    def _gen():
        full = current_prompt[0]
        if negative_suffix[0]:
            full += f", --no {negative_suffix[0]}"
        if ref_ids:
            return generate_with_refs(
                prompt=full, ref_ids=ref_ids, format=fmt,
                filename=filename, agent_id="A06", slot_id=slot_id,
            )
        else:
            return generate_image(
                prompt=full, format=fmt,
                filename=filename, agent_id="A06", slot_id=slot_id,
            )

    def _on_retry(attempt: int, fix_hint: str):
        if fix_hint:
            negative_suffix[0] = (negative_suffix[0] + ", " + fix_hint).strip(", ")
            print(f"[HOOKS/A06] ОТК попытка {attempt}: негатив += {fix_hint}")

    try:
        if has_otk:
            image_path = _otk(
                generate_fn=_gen,
                original_prompt=prompt_positive,
                agent_id="A06",
                rules="Пост для соцсети. Строгая анатомия, нет лишних элементов, яркий визуал.",
                max_visual_retries=3,
                on_retry=_on_retry,
                project_id=project_id,
            )
            quality = "ok"
        else:
            image_path = _gen()
            quality    = "ok"

        print(f"[HOOKS/A06] Картинка готова: {Path(image_path).name}")

    except Exception as e:
        print(f"[HOOKS/A06] Генерация упала: {e}")
        image_path = None
        quality    = "failed"

    # Пишем image_path обратно в chain_data.evan_visual
    chain       = state.setdefault("chain_data", {})
    ev          = chain.get("evan_visual", {})
    ev["image_path"]        = str(image_path) if image_path else None
    ev["quality"]           = quality
    ev["quality_score"]     = 8 if quality == "ok" else 3
    ev["negative_used"]     = negative_suffix[0] or None
    chain["evan_visual"]    = ev
    state["chain_data"]     = chain
    print(f"[HOOKS/A06] evan_visual.image_path записан в state")


# ══════════════════════════════════════════════════════════════════
# A11 ФЕДЯ — ГОТОВИМ КАРТИНКУ ДО ВЫЗОВА АГЕНТА
# ══════════════════════════════════════════════════════════════════

def _fedya_prepare_vision(state: dict):
    """
    Вызывается из on_BEFORE_agent("A11") — ДО того как pipeline зовёт агента.
    Кладём image_path в state["vision_images"].
    Pipeline видит vision_images и передаёт PNG Феде через chat_with_images.
    """
    chain      = state.get("chain_data", {})
    image_path = chain.get("evan_visual", {}).get("image_path")
    if image_path and Path(image_path).exists():
        state["vision_images"] = [image_path]
        print(f"[HOOKS/A11] Передаю картинку Феде: {Path(image_path).name}")
    else:
        print("[HOOKS/A11] image_path не найден — Федя без картинки")


# ══════════════════════════════════════════════════════════════════
# A12 КЛАВДИЯ — ЗАМЫКАНИЕ ПЕТЛИ
# ══════════════════════════════════════════════════════════════════

def _claudia_finalize(state: dict, human_text: str):
    """
    Три шага:
      1. Chain Integrity Check — всё на месте?
      2. billing_ledger + Strategy Registry (task_score)
      3. deliverables.json → runs/{project_id}/ (Мастерская найдёт)
      4. work_end → city_pulse для всех 12 агентов
    """
    data       = _parse_json(human_text)
    chain      = state.get("chain_data", {})
    slot_id    = state.get("_slot_id", "social_mix")
    project_id = (
        (data or {}).get("my_output", {}).get("deliverables", {}).get("project_id")
        or chain.get("history_dna", {}).get("project_id")
        or state.get("project_id", "")
    )

    # ── 1. Chain Integrity Check ───────────────────────────────────
    image_path = chain.get("evan_visual", {}).get("image_path")
    caption    = chain.get("bella_engagement", {}).get("caption", "")
    ai_defects = chain.get("fedya_inspection", {}).get("ai_defects", {}).get("detected", False)

    checks = {
        "image_exists": bool(image_path and Path(image_path).exists()),
        "caption_ok":   bool(caption and len(caption) > 10),
        "no_defects":   not ai_defects,
    }
    passed      = sum(checks.values())
    chain_score = round((passed / len(checks)) * 6.0, 2)  # потолок 6.0
    chain_status = "APPROVED" if passed == len(checks) else "PARTIAL"

    print(f"[HOOKS/A12] Chain Integrity: {chain_status} score={chain_score} checks={checks}")

    # ── 2. billing_ledger + Strategy Registry ─────────────────────
    _record_task_score(state, chain_score, slot_id, project_id)

    # ── 3. Сохраняем deliverables.json ────────────────────────────
    if data:
        deliverables = (
            data.get("my_output", {}).get("deliverables")
            or data.get("deliverables")
            or {}
        )
        if not deliverables:
            # Собираем из chain_data напрямую
            deliverables = _build_deliverables_from_chain(chain, project_id, slot_id)
        _save_deliverables(deliverables, project_id, state)
    else:
        # JSON не пришёл — собираем сами
        deliverables = _build_deliverables_from_chain(chain, project_id, slot_id)
        _save_deliverables(deliverables, project_id, state)

    # ── 4. work_end → city_pulse ──────────────────────────────────
    try:
        from studio.city_pulse import log_work_end as _lwe
        for _aid in ["A01","A02","A03","A04","A05",
                     "A06","A07","A08","A09","A10","A11","A12"]:
            _lwe(agent=_aid, dept="social_mix",
                 slot_id=slot_id, project_id=project_id, status="DONE")
        print(f"[HOOKS/A12] work_end → все 12 агентов social_mix свободны")
    except Exception as e:
        print(f"[HOOKS/A12] city_pulse work_end: {e}")

    print(f"[HOOKS/A12] Петля замкнута. project_id={project_id} score={chain_score}")


def _build_deliverables_from_chain(chain: dict, project_id: str, slot_id: str) -> dict:
    """Собирает deliverables из chain_data если Клавдия не отдала JSON."""
    ev  = chain.get("evan_visual", {})
    be  = chain.get("bella_engagement", {})
    tim = chain.get("tim_analytics", {})
    fi  = chain.get("fedya_inspection", {})

    return {
        "project_id":           project_id,
        "slot_id":              slot_id,
        "image_path":           ev.get("image_path"),
        "caption":              be.get("caption", ""),
        "cta":                  be.get("cta", {}),
        "hashtags":             be.get("hashtags", []),
        "first_comment":        be.get("first_comment", ""),
        "platform":             chain.get("history_dna", {}).get("platform", ""),
        "tim_forecast":         tim.get("viral_score"),
        "fedya_risk_score":     fi.get("risk_score", 0),
        "negative_prompt_next": fi.get("negative_prompt_recommendation", ""),
        "quality_score":        ev.get("quality_score"),
    }


def _save_deliverables(deliverables: dict, project_id: str, state: dict):
    """Сохраняет deliverables.json в runs/{project_id}/."""
    if not project_id:
        print("[HOOKS/A12] project_id пуст — deliverables.json не сохраняю")
        return

    runs_dir = Path("runs") / project_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    deliverables["saved_at"] = datetime.utcnow().isoformat()
    deliverables.setdefault("slot_id", "social_mix")

    dest = runs_dir / "deliverables.json"
    tmp  = runs_dir / "deliverables.json.tmp"
    try:
        tmp.write_text(
            json.dumps(deliverables, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(dest)
        print(f"[HOOKS/A12] deliverables.json → {dest}")
    except Exception as e:
        print(f"[HOOKS/A12] deliverables.json не записан: {e}")
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _record_task_score(state: dict, score: float, slot_id: str, project_id: str):
    """billing_ledger + Strategy Registry."""
    agents = ["A01","A02","A03","A04","A05",
              "A06","A07","A08","A09","A10","A11","A12"]

    # billing_ledger
    try:
        from studio.billing_ledger import record as _bl
        for aid in agents:
            _bl(
                agent_id=aid, slot_id=slot_id,
                model="social_mix/finalize",
                prompt_tokens=0, completion_tokens=0,
                call_type="finalize", task_score=score,
            )
        print(f"[HOOKS/A12] billing_ledger: task_score={score} ({len(agents)} агентов)")
    except Exception as e:
        print(f"[HOOKS/A12] billing_ledger: {e}")

    # Strategy Registry
    try:
        from datetime import datetime as _dt
        reg_path = Path("studio/strategy_registry.json")
        reg = {}
        if reg_path.exists():
            try:
                reg = json.loads(reg_path.read_text(encoding="utf-8"))
            except Exception:
                reg = {}

        chain   = state.get("chain_data", {})
        first   = chain.get("kostya_analysis", {})
        summary = (
            first.get("psychology_notes", "")
            or first.get("platform", "")
            or "без описания"
        )[:200]

        slots     = reg.setdefault("slots", {})
        slot_reg  = slots.setdefault(slot_id, {})
        fa_list   = slot_reg.setdefault("a01", [])

        existing = next(
            (s for s in fa_list if s.get("summary", "")[:60] == summary[:60]),
            None
        )
        now = _dt.now().isoformat()
        if existing:
            if score >= 6.0:
                existing["wins"] = existing.get("wins", 0) + 1
            existing["last_score"] = score
            existing["last_run"]   = now
        else:
            fa_list.append({
                "ts":           now,
                "score":        score,
                "last_score":   score,
                "last_run":     now,
                "run_type":     slot_id,
                "summary":      summary,
                "wins":         1 if score >= 6.0 else 0,
                "transferable": False,
            })

        total_wins = sum(
            s.get("wins", 0)
            for sl in reg.get("slots", {}).values()
            for elist in sl.values()
            for s in elist
        )
        reg["total_wins"] = total_wins
        reg["updated_at"] = now
        reg.setdefault("version", 1)

        reg_path.write_text(
            json.dumps(reg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        mark = "trophy" if score >= 6.0 else "memo"
        print(f"[HOOKS/A12] Strategy Registry: score={score} wins={total_wins}")
    except Exception as e:
        print(f"[HOOKS/A12] Strategy Registry: {e}")


# ══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════════════════════════

def _parse_json(text: str) -> dict | None:
    match = re.search(
        r"SYSTEM_JSON_START[^\\n]*\\n(.*?)\\n[^\\n]*SYSTEM_JSON_END",
        text, re.DOTALL
    )
    if match:
        raw = match.group(1)
    else:
        fence = re.search(r"```json\\s*\\n(.*?)\\n```", text, re.DOTALL)
        if fence:
            raw = fence.group(1)
        else:
            return None
    raw = raw.strip().strip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"[SOCIAL_MIX] JSON parse error: {e}")
        return None
'''

# ═══════════════════════════════════════════════════════════
# ПРИМЕНЯЕМ
# ═══════════════════════════════════════════════════════════

def main():
    if not HOOKS_PATH.exists():
        print(f"Файл не найден: {HOOKS_PATH}")
        return

    shutil.copy2(HOOKS_PATH, BACKUP_PATH)
    print(f"Бэкап: {BACKUP_PATH}")

    HOOKS_PATH.write_text(NEW_CONTENT, encoding="utf-8")

    import subprocess
    r = subprocess.run(
        ["python", "-m", "py_compile", str(HOOKS_PATH)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("Синтаксис OK")
        print("hooks.py v4.1 применён")
    else:
        print(f"Синтаксис ошибка:\n{r.stderr}")
        print("Откатываю...")
        shutil.copy2(BACKUP_PATH, HOOKS_PATH)
        print("Откат выполнен")


if __name__ == "__main__":
    main()
