#!/usr/bin/env python3
"""
patch_clipmakers_launch.py
Студия «Шесть пальцев» | Спринт 40

Закрывает баги из CLIPMAKERS_RULES.md + подключает Виктора:

  Баг 1: hooks.py — пустая болванка → живой файл
  Баг 2: manifest.json: run_type = "full" → "clipmakers"
  Баг 3: manifest.json: qa_agent = "A05" → "A12"
  Баг 5: interaction_log_clipmakers.jsonl — создать пустой

  +Виктор: manifest.hard_stop + маска clipmakers_hardstop.md
  +Документы: CHAIN_CONTRACT.md + CLIPMAKERS_RULES.md в папку цеха

Запуск:
  python patch_clipmakers_launch.py            # dry-run
  python patch_clipmakers_launch.py --apply    # применить
"""
import sys
import json
import shutil
from pathlib import Path

DRY_RUN = "--apply" not in sys.argv

STUDIO_ROOT   = Path(__file__).parent / "studio"
CLIPMAKERS    = STUDIO_ROOT / "modules" / "clipmakers"
ECONOMY_DATA  = STUDIO_ROOT / "economy" / "data"
VICTOR_MASKS  = STUDIO_ROOT / "modules" / "residents" / "005_VICTOR" / "forge" / "masks"

MANIFEST_PATH = CLIPMAKERS / "manifest.json"
HOOKS_PATH    = CLIPMAKERS / "hooks.py"
ILOG_PATH     = ECONOMY_DATA / "interaction_log_clipmakers.jsonl"
CONTRACT_DST  = CLIPMAKERS / "CHAIN_CONTRACT.md"
RULES_DST     = CLIPMAKERS / "CLIPMAKERS_RULES.md"
MASK_DST           = VICTOR_MASKS / "clipmakers_hardstop.md"
MONTEUR_MASKS      = STUDIO_ROOT / "modules" / "residents" / "006_MONTEUR" / "forge" / "masks"
MONTEUR_MASK_DST   = MONTEUR_MASKS / "clipmakers.md"
A06_PROMPT_DST     = CLIPMAKERS / "A06" / "forge" / "prompt.md"
A08_PROMPT_DST     = CLIPMAKERS / "A08" / "forge" / "prompt.md"

# Файлы рядом со скриптом
CONTRACT_SRC  = Path(__file__).parent / "CHAIN_CONTRACT.md"
RULES_SRC     = Path(__file__).parent / "CLIPMAKERS_RULES.md"
MASK_SRC           = Path(__file__).parent / "clipmakers_hardstop.md"
MONTEUR_MASK_SRC   = Path(__file__).parent / "monteur_clipmakers.md"
A06_PROMPT_SRC     = Path(__file__).parent / "prompt_A06_gimbal_gus.md"
A08_PROMPT_SRC     = Path(__file__).parent / "prompt_A08_drone_dan.md"

BACKUP_SUFFIX = ".bak_sprint40_launch"


def log(msg):
    print(f"  {msg}")

def log_action(label, detail=""):
    prefix = "○ DRY" if DRY_RUN else "▶ APP"
    print(f"[{prefix}] {label}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {line}")

def backup(path):
    dst = path.with_suffix(path.suffix + BACKUP_SUFFIX)
    if not DRY_RUN:
        shutil.copy2(path, dst)
    log(f"бэкап → {dst.name}")


# ─── manifest.json ────────────────────────────────────────

HARD_STOP = {
    "after_agent": "A03",
    "residents": ["victor"],
    "knowledge": ["29_Music_Video_Grammar.txt", "04_Audio_Aesthetics.txt"],
    "web_search": True
}

def fix_manifest():
    print("\n[1/6] manifest.json — run_type + qa_agent + hard_stop")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    changed = []

    if data.get("run_type") != "clipmakers":
        log_action(f'run_type: "{data.get("run_type")}" → "clipmakers"')
        changed.append("run_type")
        data["run_type"] = "clipmakers"

    if data.get("qa_agent") != "A12":
        log_action(f'qa_agent: "{data.get("qa_agent")}" → "A12"')
        changed.append("qa_agent")
        data["qa_agent"] = "A12"

    existing_hs = data.get("hard_stop", {})
    if existing_hs != HARD_STOP:
        log_action(
            'hard_stop: добавить Виктора после A03',
            'after_agent: "A03"\n'
            'residents: ["victor"]\n'
            'knowledge: ["29_Music_Video_Grammar.txt", "04_Audio_Aesthetics.txt"]\n'
            'web_search: true'
        )
        changed.append("hard_stop")
        data["hard_stop"] = HARD_STOP

    if not changed:
        log("✓ manifest.json уже корректен")
        return

    if not DRY_RUN:
        backup(MANIFEST_PATH)
        MANIFEST_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"✅ manifest.json обновлён ({', '.join(changed)})")
    else:
        log(f"○ dry-run: не записан ({', '.join(changed)})")


# ─── hooks.py ─────────────────────────────────────────────

HOOKS_NEW = r'''
# studio/modules/clipmakers/hooks.py — Хуки CLIPMAKERS v2.0
# Студия «Шесть пальцев» · 2026
#
# v2.0 — Спринт 40. Реальная генерация медиа.
# Паттерн: video_long/hooks.py v4.7
#
# on_before_agent:
#   A01: инъекция history_dna + work_start
#   A04–A12: хард-стоп если Виктор → NEEDS_REWORK
#   A12: напоминание о замыкании петли
#
# on_after_agent:
#   A06 Гимбал Гас: параллельная генерация PNG кадров через fal.ai
#   A08 Дрон Дэн:   параллельная генерация PNG дрон-шотов через fal.ai
#                   → оба передают кадры в Wan2.2 для получения mp4
#   A11 Бьюти Белла: генерация hero-кадров (обложки)
#   A12 Рендер Рекс: billing_ledger + strategy_registry + ministry
#                    + city_pulse work_end + вызов Монтажёра

import json
import re
import time
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

AGENTS_ALL         = [f"A{str(i).zfill(2)}" for i in range(1, 13)]
AGENTS_POST_VICTOR = [f"A{str(i).zfill(2)}" for i in range(4, 13)]

_LOG_PATH          = Path("studio/economy/data/interaction_log_clipmakers.jsonl")
OUTPUT_DIR         = Path("output/generated")
_FRAME_TIMEOUT     = 300
_RETRY_DELAYS      = [5, 10]
_MAX_WORKERS       = 4


# ═══════════════════════════════════════════════════════════════════
# ГЛАВНЫЕ ХУКИ
# ═══════════════════════════════════════════════════════════════════

def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    if worker_id == "A01":
        context = _inject_history_dna(state, context)
        _log_work_start(state)

    if worker_id in AGENTS_POST_VICTOR:
        verdict = _get_victor_verdict(state)
        if verdict == "NEEDS_REWORK":
            msg = (
                f"[clipmakers] ХАРД-СТОП: Виктор → NEEDS_REWORK. "
                f"Агент {worker_id} заблокирован. Вернитесь к A01 или A03."
            )
            print(msg)
            raise StopIteration(msg)

    if worker_id == "A12":
        context += (
            "\n\n=== ЗАКОН ЗАМЫКАНИЯ ПЕТЛИ (CLIPMAKERS_RULES §13) ===\n"
            "После финального вердикта ОБЯЗАТЕЛЬНО:\n"
            "1. chain_status = \"APPROVED\" или \"FAILED\"\n"
            "2. history_dna сформирован для следующего клипа\n"
            "3. deliverables заполнены — video_clips[] с video_path\n"
            "Без этого монтажёр не сможет собрать клип.\n"
            "=== КОНЕЦ ==="
        )

    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    score = float(meta.get("score", 0.0))

    _append_interaction({
        "ts":        datetime.datetime.utcnow().isoformat(),
        "workshop":  "clipmakers",
        "agent":     worker_id,
        "score":     score,
        "chars_out": len(human_text),
    })

    if worker_id == "A06":
        _gus_generate_frames(state, human_text)

    elif worker_id == "A08":
        _dan_generate_aerial(state, human_text)
        # ОТК всех клипов: A06 уже сделал кадры, A08 добавил дроны
        # Проверяем пригодность mp4 перед монтажом
        _otk_clips(state)

    elif worker_id == "A11":
        _bella_generate_covers(state, human_text)

    elif worker_id == "A12":
        _rex_close_loop(state, human_text, score)

    return {}


# ═══════════════════════════════════════════════════════════════════
# A06 ГИМБАЛ ГАС — параллельная генерация кадров (fal.ai + Wan2.2)
# ═══════════════════════════════════════════════════════════════════

def _gus_generate_frames(state: dict, human_text: str):
    """
    Читает generation_frames[] из ответа Гаса.
    Для каждого кадра:
      1. fal.ai → PNG (banana_prompt)
      2. SiliconFlow Wan2.2 → mp4 (motion из camera_move)
    Пишет video_path обратно в state.
    """
    data = _parse_json(human_text)
    if not data:
        print("[CLIPMAKERS A06] JSON не найден — пропускаю")
        return

    my_output = data.get("my_output", data)
    frames    = my_output.get("generation_frames", [])
    if not frames:
        print("[CLIPMAKERS A06] generation_frames пуст — пропускаю")
        return

    slot_id     = state.get("_slot_id", "clipmakers")
    project_id  = state.get("project_id", "clip_unknown")
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    total = len(frames)
    print(f"[CLIPMAKERS A06] Генерация {total} кадров (fal.ai + Wan2.2)...")

    def _gen_frame(args):
        idx, frame = args
        prompt   = frame.get("banana_prompt", "")
        shot_id  = frame.get("shot_id", f"shot_{idx+1:02d}")
        ref_ids  = frame.get("ref_ids", [])
        if isinstance(ref_ids, str):
            ref_ids = [ref_ids]

        if not prompt:
            frame["video_path"] = None
            return idx, frame

        png_name = f"{_slugify(shot_id)}.png"
        mp4_name = f"{_slugify(shot_id)}.mp4"
        png_path = project_dir / png_name
        mp4_path = project_dir / mp4_name

        print(f"[A06] → {shot_id} ({idx+1}/{total})")

        # Шаг 1: fal.ai → PNG
        try:
            from studio.fal_client import generate_with_refs, generate_image
            if ref_ids:
                raw_png = generate_with_refs(
                    prompt=prompt, ref_ids=ref_ids,
                    format="16:9", filename=png_name,
                    agent_id="A06", slot_id=slot_id,
                )
            else:
                raw_png = generate_image(
                    prompt=prompt, format="16:9",
                    filename=png_name,
                    agent_id="A06", slot_id=slot_id,
                )
            Path(raw_png).replace(png_path)
            print(f"[A06] ✅ PNG: {png_name}")
        except Exception as e:
            print(f"[A06] ❌ fal.ai {shot_id}: {e}")
            frame["video_path"] = None
            return idx, frame

        # Шаг 2: Wan2.2 → mp4
        camera_move = frame.get("camera_move", "static")
        motion_prompt = _camera_to_motion(camera_move, prompt)
        try:
            from studio.siliconflow_client import generate_video_with_retry
            raw_mp4 = generate_video_with_retry(
                image_path=str(png_path),
                motion_prompt=motion_prompt,
                filename=mp4_name,
                duration=int(frame.get("duration_sec", 4)),
                resolution="720p",
                agent_id="A06",
                slot_id=slot_id,
            )
            import shutil
            shutil.move(raw_mp4, mp4_path)
            frame["png_path"]   = str(png_path)
            frame["video_path"] = str(mp4_path)
            print(f"[A06] ✅ mp4: {mp4_name}")
        except Exception as e:
            print(f"[A06] ❌ Wan2.2 {shot_id}: {e}")
            frame["png_path"]   = str(png_path)
            frame["video_path"] = None

        return idx, frame

    results = list(frames)
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        future_map = {pool.submit(_gen_frame, (i, f)): i for i, f in enumerate(frames)}
        for future in as_completed(future_map, timeout=_FRAME_TIMEOUT * total):
            try:
                idx, frame = future.result()
                results[idx] = frame
            except Exception as e:
                idx = future_map[future]
                print(f"[A06] ❌ Поток {idx}: {e}")
                results[idx]["video_path"] = None

    ok = sum(1 for f in results if f.get("video_path"))
    print(f"[A06] Итог: {ok}/{total} кадров с video_path")

    my_output["generation_frames"] = results
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════════
# A08 ДРОН ДЭН — воздушные кадры (fal.ai + Wan2.2)
# ═══════════════════════════════════════════════════════════════════

def _dan_generate_aerial(state: dict, human_text: str):
    """Аналог _gus_generate_frames для дрон-шотов."""
    data = _parse_json(human_text)
    if not data:
        print("[CLIPMAKERS A08] JSON не найден — пропускаю")
        return

    my_output    = data.get("my_output", data)
    drone_frames = my_output.get("drone_frames", [])
    if not drone_frames:
        print("[CLIPMAKERS A08] drone_frames пуст — пропускаю")
        return

    slot_id     = state.get("_slot_id", "clipmakers")
    project_id  = state.get("project_id", "clip_unknown")
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    total = len(drone_frames)
    print(f"[CLIPMAKERS A08] Генерация {total} дрон-шотов...")

    def _gen_aerial(args):
        idx, frame = args
        prompt     = frame.get("banana_prompt", "")
        shot_id    = frame.get("shot_id", f"D{idx+1:02d}")
        flight     = frame.get("flight_type", "reveal")

        if not prompt:
            frame["video_path"] = None
            return idx, frame

        png_name = f"aerial_{_slugify(shot_id)}.png"
        mp4_name = f"aerial_{_slugify(shot_id)}.mp4"
        png_path = project_dir / png_name
        mp4_path = project_dir / mp4_name

        print(f"[A08] → {shot_id} ({idx+1}/{total})")

        try:
            from studio.fal_client import generate_image
            raw_png = generate_image(
                prompt=prompt, format="16:9",
                filename=png_name, agent_id="A08", slot_id=slot_id,
            )
            Path(raw_png).replace(png_path)
        except Exception as e:
            print(f"[A08] ❌ fal.ai {shot_id}: {e}")
            frame["video_path"] = None
            return idx, frame

        motion_prompt = _flight_to_motion(flight, prompt)
        try:
            from studio.siliconflow_client import generate_video_with_retry
            raw_mp4 = generate_video_with_retry(
                image_path=str(png_path),
                motion_prompt=motion_prompt,
                filename=mp4_name,
                duration=int(frame.get("duration_sec", 6)),
                resolution="720p",
                agent_id="A08",
                slot_id=slot_id,
            )
            import shutil
            shutil.move(raw_mp4, mp4_path)
            frame["png_path"]   = str(png_path)
            frame["video_path"] = str(mp4_path)
            print(f"[A08] ✅ {mp4_name}")
        except Exception as e:
            print(f"[A08] ❌ Wan2.2 {shot_id}: {e}")
            frame["png_path"]   = str(png_path)
            frame["video_path"] = None

        return idx, frame

    results = list(drone_frames)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_map = {pool.submit(_gen_aerial, (i, f)): i for i, f in enumerate(drone_frames)}
        for future in as_completed(future_map, timeout=_FRAME_TIMEOUT * total):
            try:
                idx, frame = future.result()
                results[idx] = frame
            except Exception as e:
                idx = future_map[future]
                results[idx]["video_path"] = None

    ok = sum(1 for f in results if f.get("video_path"))
    print(f"[A08] Итог дрон: {ok}/{total}")

    my_output["drone_frames"] = results
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════════
# A11 БЬЮТИ БЕЛЛА — hero-кадры (обложки) через fal.ai
# ═══════════════════════════════════════════════════════════════════

def _bella_generate_covers(state: dict, human_text: str):
    """Генерирует hero_frames (YouTube cover, poster, reels_preview) через fal.ai."""
    data = _parse_json(human_text)
    if not data:
        return

    my_output   = data.get("my_output", data)
    hero_frames = my_output.get("hero_frames", [])
    if not hero_frames:
        print("[CLIPMAKERS A11] hero_frames пуст — пропускаю")
        return

    slot_id     = state.get("_slot_id", "clipmakers")
    project_id  = state.get("project_id", "clip_unknown")
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Ищем ai_prompts для обложек
    ai_prompts = {
        p.get("scope", ""): p.get("prompt", "")
        for p in my_output.get("ai_prompts", [])
    }

    print(f"[CLIPMAKERS A11] Генерация {len(hero_frames)} hero-кадров...")

    for frame in hero_frames:
        purpose = frame.get("purpose", "cover")
        # Берём промпт из ai_prompts["hero"] или из самого frame
        prompt = ai_prompts.get("hero", "") or frame.get("banana_prompt", "")
        if not prompt:
            continue

        shot_id  = frame.get("shot_id", f"hero_{purpose}")
        filename = f"cover_{_slugify(purpose)}.png"
        dest     = project_dir / filename

        try:
            from studio.fal_client import generate_image
            raw = generate_image(
                prompt=prompt, format="16:9",
                filename=filename, agent_id="A11", slot_id=slot_id,
            )
            Path(raw).replace(dest)
            frame["path"] = str(dest)
            print(f"[A11] ✅ {purpose}: {filename}")
        except Exception as e:
            print(f"[A11] ❌ {purpose}: {e}")
            frame["path"] = None

    my_output["hero_frames"] = hero_frames
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════════
# A12 РЕНДЕР РЕКС — замыкание петли + вызов Монтажёра
# ═══════════════════════════════════════════════════════════════════

def _rex_close_loop(state: dict, human_text: str, score: float):
    slot_id   = state.get("_slot_id", "clipmakers")
    chain     = state.get("chain_data", {})
    vinnie    = chain.get("vinnie_concept", {})
    clip_type = "unknown"
    if isinstance(vinnie, dict):
        clip_type = vinnie.get("concept", {}).get("clip_type", "unknown")

    data    = _parse_json(human_text)
    verdict = "UNKNOWN"
    if data:
        rex_qa  = data.get("my_output", {}).get("rex_qa", {})
        if isinstance(rex_qa, dict):
            verdict = rex_qa.get("verdict", "UNKNOWN")

    # ── billing_ledger ────────────────────────────────────────────
    try:
        import sys as _sys
        _root = str(Path(__file__).parent.parent.parent)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from studio.billing_ledger import record as _bl
        for _aid in AGENTS_ALL:
            _bl(
                agent_id=_aid, slot_id=slot_id,
                model=f"{slot_id}/finalize",
                prompt_tokens=0, completion_tokens=0,
                call_type="finalize", task_score=score,
            )
        print(f"[CLIPMAKERS A12] 📊 billing_ledger: score={score} × 12")
    except Exception as e:
        print(f"[CLIPMAKERS A12] ⚠ billing_ledger: {e}")

    # ── strategy_registry ────────────────────────────────────────
    try:
        import json as _rj
        from datetime import datetime as _rdt
        _reg_path = Path("studio/strategy_registry.json")
        _reg = {}
        if _reg_path.exists():
            try:
                _reg = _rj.loads(_reg_path.read_text(encoding="utf-8"))
            except Exception:
                _reg = {}
        _slots    = _reg.setdefault("slots", {})
        _slot_reg = _slots.setdefault(slot_id, {})
        _a01_list = _slot_reg.setdefault("a01", [])
        _summary  = (
            vinnie.get("concept", {}).get("idea", "")
            or vinnie.get("concept", {}).get("visual_metaphor", "")
            or clip_type
        )[:200]
        _existing = next(
            (s for s in _a01_list if s.get("summary", "")[:60] == _summary[:60]),
            None
        )
        if _existing:
            if score >= 6.0:
                _existing["wins"] = _existing.get("wins", 0) + 1
            _existing["last_score"] = score
            _existing["last_run"]   = _rdt.now().isoformat()
        else:
            _a01_list.append({
                "ts": _rdt.now().isoformat(), "score": score,
                "last_score": score, "last_run": _rdt.now().isoformat(),
                "run_type": clip_type, "summary": _summary,
                "wins": 1 if score >= 6.0 else 0, "transferable": False,
            })
        _total_wins = sum(
            s.get("wins", 0) for _sl in _reg.get("slots", {}).values()
            for _elist in _sl.values() for s in _elist
        )
        _reg["total_wins"] = _total_wins
        _reg["updated_at"] = _rdt.now().isoformat()
        _reg.setdefault("version", 1)
        _reg_path.write_text(_rj.dumps(_reg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[CLIPMAKERS A12] {'🏆' if score >= 6.0 else '📝'} strategy_registry: {clip_type}")
    except Exception as e:
        print(f"[CLIPMAKERS A12] ⚠ strategy_registry: {e}")

    # ── ministry ─────────────────────────────────────────────────
    try:
        from studio.economy import ministry as _min
        for _aid in AGENTS_ALL:
            _min.record_outcome(agent_id=_aid, slot_id=slot_id, score=score, cost_usd=0.0)
        print(f"[CLIPMAKERS A12] 🏛 ministry: score={score}")
    except Exception as e:
        print(f"[CLIPMAKERS A12] ⚠ ministry: {e}")

    # ── city_pulse work_end ───────────────────────────────────────
    try:
        from studio.city_pulse import log_work_end as _lwe
        _pid = state.get("project_id", "")
        for _aid in AGENTS_ALL:
            _lwe(agent=_aid, dept="clipmakers", slot_id=slot_id, project_id=_pid, status="DONE")
        print("[CLIPMAKERS A12] 🏁 work_end → все 12 свободны")
    except Exception as e:
        print(f"[CLIPMAKERS A12] ⚠ city_pulse work_end: {e}")

    # ── interaction_log ──────────────────────────────────────────
    _append_interaction({
        "ts": datetime.datetime.utcnow().isoformat(),
        "workshop": "clipmakers", "agent": "A12_LOOP_CLOSED",
        "clip_type": clip_type, "verdict": verdict, "score": score,
    })

    # ── Монтажёр ─────────────────────────────────────────────────
    if verdict == "APPROVED":
        _call_monteur(state, data, clip_type, slot_id)
    else:
        print(f"[CLIPMAKERS A12] ⚠ Монтажёр не вызван: verdict={verdict}")

    print(f"[CLIPMAKERS A12] ✅ Петля замкнута: {clip_type} {verdict} score={score}")


def _call_monteur(state: dict, rex_data: dict | None, clip_type: str, slot_id: str):
    """Собирает deliverables и вызывает run_monteur_assembly()."""
    project_id = state.get("project_id", "clip_unknown")
    chain      = state.get("chain_data", {})

    # Собираем video_clips из A06 (gus_camera) и A08 (dan_aerial)
    video_clips = []
    gus = chain.get("gus_camera", {})
    if isinstance(gus, dict):
        for f in gus.get("generation_frames", []):
            if f.get("video_path"):
                video_clips.append({
                    "shot_id":     f.get("shot_id", ""),
                    "scene_id":    f.get("scene_id", ""),
                    "shot_type":   f.get("shot_type", "performance"),
                    "timecode":    f.get("timecode", "0:00"),
                    "sync_point":  f.get("sync_point", False),
                    "duration_sec": f.get("duration_sec", 4),
                    "video_path":  f["video_path"],
                })

    dan = chain.get("dan_aerial", {})
    if isinstance(dan, dict):
        for f in dan.get("drone_frames", []):
            if f.get("video_path"):
                video_clips.append({
                    "shot_id":     f.get("shot_id", ""),
                    "scene_id":    f.get("scene_id", ""),
                    "shot_type":   "aerial",
                    "timecode":    f.get("timecode", "0:00"),
                    "sync_point":  f.get("sync_point", False),
                    "duration_sec": f.get("duration_sec", 6),
                    "video_path":  f["video_path"],
                })

    # Сортируем по timecode — закон музыкального клипа
    def _tc_to_sec(tc: str) -> float:
        try:
            parts = tc.replace("—", "-").split(":")
            return float(parts[0]) * 60 + float(parts[1]) if len(parts) == 2 else float(parts[0])
        except Exception:
            return 0.0

    video_clips.sort(key=lambda c: _tc_to_sec(c.get("timecode", "0:00")))

    # Hero-кадры из A11
    bella = chain.get("bella_retouch", {})
    covers = []
    if isinstance(bella, dict):
        covers = [f for f in bella.get("hero_frames", []) if f.get("path")]

    # sync_data из A02 Ричи
    richi = chain.get("richi_sync", {})

    # Музыка — трек артиста из master_brief (не генерируем, это входящий файл)
    audio_layer = {}
    master_brief = chain.get("master_brief", {})
    if isinstance(master_brief, dict):
        audio_refs = master_brief.get("assets", {}).get("audio_ref", [])
        if audio_refs:
            audio_path = audio_refs[0] if isinstance(audio_refs[0], str) else ""
            if audio_path and Path(audio_path).exists():
                audio_layer = {"music": {"audio_path": audio_path, "ducking_db": -6}}
                print(f"[CLIPMAKERS A12] 🎵 Трек артиста: {Path(audio_path).name}")
            else:
                print(f"[CLIPMAKERS A12] ℹ️  audio_ref задан но файл не найден: {audio_refs[0]}")
        else:
            print("[CLIPMAKERS A12] ℹ️  audio_ref пуст — клип без музыки")

    # Фильтруем клипы отклонённые ОТК
    before = len(video_clips)
    video_clips = [c for c in video_clips if not c.get("broken")]
    if before != len(video_clips):
        print(f"[CLIPMAKERS A12] 🗑 ОТК отклонил {before - len(video_clips)} клипов")

    # Перенумеруем shot_id чтобы гарантировать порядок в monteur.py
    for idx, clip in enumerate(video_clips):
        clip["shot_id"] = f"S{idx+1:03d}"

    deliverables = {
        "project_id":  project_id,
        "clip_type":   clip_type,
        "video_clips": video_clips,
        "covers":      covers,
        "audio":       audio_layer,
        "sync_data":   richi,
    }

    print(f"[CLIPMAKERS A12] 🎬 Монтажёр: {len(video_clips)} клипов → сборка...")

    try:
        from studio.residents_manager import run_monteur_assembly
        result = run_monteur_assembly(
            deliverables=deliverables,
            project_id=project_id,
            slot_id=slot_id,
        )
        print(f"[CLIPMAKERS A12] 🎬 Монтажёр: {result.status} → {result.final_path}")
        state["_assembly_result"] = {
            "status":     result.status,
            "final_path": result.final_path,
            "duration":   getattr(result, "duration_sec", 0),
            "clips":      f"{result.clips_used}/{result.clips_total}",
        }
    except Exception as e:
        print(f"[CLIPMAKERS A12] ❌ Монтажёр упал: {e}")
        state["_assembly_result"] = {"status": "FAILED", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════

def _inject_history_dna(state: dict, context: str) -> str:
    history_dna = (
        state.get("history_dna")
        or state.get("chain_data", {}).get("history_dna", {})
    )
    if not history_dna:
        print("[CLIPMAKERS A01] history_dna нет — чистый старт")
        return context
    try:
        block = (
            "\n\n---\n[PROJECT MEMORY — history_dna]\n"
            "История прошлых клипов. Предложи контраст — не повторение.\n"
            + json.dumps(history_dna, ensure_ascii=False, indent=2)
            + "\n---\n"
        )
        print("[CLIPMAKERS A01] ✅ history_dna инъецирован")
        return context + block
    except Exception:
        return context


def _get_victor_verdict(state: dict) -> str | None:
    vc = state.get("victor_critique")
    if isinstance(vc, dict):
        return vc.get("verdict")
    chain = state.get("chain_data", {})
    vc2 = chain.get("victor_critique")
    if isinstance(vc2, dict):
        return vc2.get("verdict")
    return None


def _log_work_start(state: dict):
    try:
        from studio.city_pulse import log_work_start as _lws
        _slot = state.get("_slot_id", "clipmakers")
        _pid  = state.get("project_id", "")
        for _aid in AGENTS_ALL:
            _lws(agent=_aid, dept="clipmakers", slot_id=_slot, project_id=_pid)
        print("[CLIPMAKERS A01] 🏭 work_start → 12 агентов в цеху")
    except Exception as e:
        print(f"[CLIPMAKERS A01] ⚠ city_pulse: {e}")


def _append_interaction(event: dict):
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[CLIPMAKERS] ⚠ interaction_log: {e}")


def _update_state(state: dict, data: dict):
    state["_last_output"] = data
    chain = state.get("chain_data", {})
    if "my_output" in data:
        chain.update(data["my_output"])
    else:
        chain.update(data)
    state["chain_data"] = chain


def _camera_to_motion(camera_move: str, base_prompt: str) -> str:
    """Конвертирует camera_move в motion_prompt для Wan2.2."""
    moves = {
        "tilt_down":     "camera slowly tilts downward, smooth motion",
        "tilt_up":       "camera slowly tilts upward, smooth motion",
        "dolly_forward": "camera dolly push-in toward subject, steady movement",
        "dolly_back":    "camera pulls back from subject, steady movement",
        "tracking":      "camera tracks alongside moving subject",
        "orbit":         "camera orbits around subject in circular path",
        "static":        "camera perfectly static, no movement",
        "crash_zoom":    "sudden rapid zoom toward subject, dramatic",
        "handheld":      "slight handheld camera movement, natural",
    }
    motion = moves.get(camera_move, "smooth cinematic camera movement")
    return f"{motion}, {base_prompt[:100]}"


def _flight_to_motion(flight_type: str, base_prompt: str) -> str:
    """Конвертирует flight_type в motion_prompt для Wan2.2."""
    flights = {
        "reveal":     "aerial camera slowly descends revealing landscape below",
        "orbit":      "aerial camera orbits in wide circular path around subject",
        "tracking":   "aerial camera tracks subject from above, following movement",
        "pull_away":  "aerial camera pulls back and ascends, subject grows smaller",
        "dive":       "aerial camera dives downward toward subject rapidly",
        "top_down":   "aerial camera moves straight down maintaining top-down view",
        "fly_through": "aerial camera flies through space, dynamic sweeping motion",
    }
    motion = flights.get(flight_type, "smooth aerial drone movement")
    return f"{motion}, {base_prompt[:100]}"


def _parse_json(text: str) -> dict | None:
    match = re.search(
        r"SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END", text, re.DOTALL
    )
    if match:
        raw = match.group(1)
    else:
        fence = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        raw = fence.group(1) if fence else None
    if not raw:
        return None
    raw = raw.strip().strip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name).lower().strip())
    return re.sub(r"_+", "_", slug).strip("_") or "unknown"


# ═══════════════════════════════════════════════════════════════════
# ОТК КЛИПОВ — проверка mp4 от Wan2.2 перед монтажом
# Вызывается из on_after_agent после A08 (все клипы готовы)
# ═══════════════════════════════════════════════════════════════════

def _otk_clips(state: dict):
    """
    Проверяет все video_path в chain_data через 3 кадра + LLM.

    Критерии REJECT (только технический брак):
      - Артефакты генерации (дыры, размытые пятна, цветовые сбои)
      - Видео полностью чёрное или белое
      - Явное несоответствие: вместо человека — абстракция

    PARTIAL — использовать с пометкой.
    PASS — в сборку.

    Результат пишется в frame["otk"] = "PASS" | "PARTIAL" | "REJECT".
    broken клипы помечаются — _call_monteur() их пропустит.
    """
    slot_id    = state.get("_slot_id", "clipmakers")
    chain      = state.get("chain_data", {})
    all_frames = []

    # Собираем все клипы из A06 и A08
    gus = chain.get("gus_camera", {})
    if isinstance(gus, dict):
        all_frames += [(f, "A06") for f in gus.get("generation_frames", [])
                       if f.get("video_path") and Path(f["video_path"]).exists()]

    dan = chain.get("dan_aerial", {})
    if isinstance(dan, dict):
        all_frames += [(f, "A08") for f in dan.get("drone_frames", [])
                       if f.get("video_path") and Path(f["video_path"]).exists()]

    if not all_frames:
        print("[ОТК] Нет клипов для проверки")
        return

    print(f"[ОТК] Проверка {len(all_frames)} клипов...")

    try:
        from studio.llm import chat_with_images
    except ImportError:
        print("[ОТК] ⚠ chat_with_images недоступен — пропускаю проверку")
        return

    OTK_SYSTEM = (
        "Ты технический контролёр видеопроизводства. "
        "Смотришь на 3 кадра из mp4 клипа (начало, середина, конец).\n\n"
        "REJECT только при техническом браке:\n"
        "  · Артефакты генерации: дыры, распадающиеся лица, цветовые пятна\n"
        "  · Видео полностью чёрное или засвеченное\n"
        "  · Вместо заявленного содержимого — абстракция или мусор\n\n"
        "PARTIAL если:\n"
        "  · Небольшие артефакты по краям, основное содержимое читается\n"
        "  · Один кадр плохой, два нормальных\n\n"
        "PASS — всё остальное. Художественное качество не оцениваешь.\n\n"
        'JSON: {"verdict": "PASS" | "PARTIAL" | "REJECT", '
        '"reason": "одна фраза или null"}'
    )

    passed = rejected = partial = 0

    for frame, agent_id in all_frames:
        shot_id    = frame.get("shot_id", "?")
        video_path = frame["video_path"]
        frames_img = _extract_3_frames(video_path)

        if not frames_img:
            frame["otk"] = "PASS"  # нет кадров — не блокируем
            passed += 1
            continue

        try:
            import re as _re, json as _json
            raw = chat_with_images(
                system=OTK_SYSTEM,
                user_text=f"shot_id: {shot_id}. Оцени пригодность.",
                images=frames_img,
                temperature=0.1,
                agent_id="OTK_CLIPMAKERS",
                slot_id=slot_id,
            )
            m = _re.search(r'\{.*\}', raw, _re.DOTALL)
            check = _json.loads(m.group()) if m else {"verdict": "PASS"}
        except Exception as e:
            print(f"[ОТК] ⚠ {shot_id}: LLM ошибка — {e}, считаю PASS")
            check = {"verdict": "PASS"}

        verdict = check.get("verdict", "PASS")
        reason  = check.get("reason", "")
        frame["otk"] = verdict

        if verdict == "PASS":
            passed += 1
        elif verdict == "PARTIAL":
            partial += 1
            print(f"[ОТК] ⚡ {shot_id}: PARTIAL — {reason}")
        else:
            rejected += 1
            frame["broken"] = True
            print(f"[ОТК] ❌ {shot_id}: REJECT — {reason} → пропустим в монтаже")

    print(f"[ОТК] Итог: PASS={passed} PARTIAL={partial} REJECT={rejected}")


def _extract_3_frames(video_path: str) -> list:
    """Извлекает 3 кадра (5%, 50%, 92%) из mp4 для ОТК."""
    import subprocess, base64, json as _j, tempfile

    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(_j.loads(probe.stdout).get("format", {}).get("duration", 4))
    except Exception:
        duration = 4.0

    frames = []
    timestamps = [max(0.1, duration * 0.05), duration * 0.5, duration * 0.92]

    try:
        with tempfile.TemporaryDirectory() as tmp:
            for i, ts in enumerate(timestamps):
                fp = Path(tmp) / f"f{i}.jpg"
                subprocess.run(
                    ["ffmpeg", "-ss", str(ts), "-i", str(video_path),
                     "-vframes", "1", "-q:v", "5", str(fp), "-y"],
                    capture_output=True, timeout=15,
                )
                if fp.exists() and fp.stat().st_size > 0:
                    b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                    frames.append({
                        "base64": b64,
                        "mime_type": "image/jpeg",
                        "name": f"frame_{i}_{ts:.1f}s.jpg",
                    })
    except FileNotFoundError:
        pass  # ffmpeg не найден — не блокируем
    except Exception as e:
        print(f"[ОТК] ⚠ Кадры из {video_path}: {e}")

    return frames

'''

def fix_hooks():
    print("\n[2/6] hooks.py — живой файл")
    log_action(
        "Перезаписать hooks.py",
        "on_before_agent: history_dna + work_start + хард-стоп Виктора\n"
        "on_after_agent: interaction_log каждый агент\n"
        "A12: billing_ledger + strategy_registry + ministry + city_pulse work_end"
    )
    if not DRY_RUN:
        backup(HOOKS_PATH)
        HOOKS_PATH.write_text(HOOKS_NEW, encoding="utf-8")
        log("✅ hooks.py записан")
    else:
        log("○ dry-run: hooks.py не записан")


# ─── interaction_log ──────────────────────────────────────

def fix_interaction_log():
    print("\n[3/6] interaction_log_clipmakers.jsonl")
    if ILOG_PATH.exists():
        log(f"✓ уже существует")
        return
    log_action(f"Создать пустой файл")
    if not DRY_RUN:
        ILOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ILOG_PATH.write_text("", encoding="utf-8")
        log("✅ создан")
    else:
        log("○ dry-run: не создан")


# ─── Маска Виктора ────────────────────────────────────────

def place_victor_mask():
    print("\n[4/6] Маска Виктора: clipmakers_hardstop.md")

    if not MASK_SRC.exists():
        log(f"⚠  clipmakers_hardstop.md не найден рядом со скриптом")
        log(f"   Положи сюда: {MASK_SRC}")
        return

    log_action(
        f"Создать {VICTOR_MASKS}/clipmakers_hardstop.md",
        "7 вопросов музыкального стори-эдитора\n"
        "sync_gap, return_to, web_search через Tavily"
    )

    if not DRY_RUN:
        VICTOR_MASKS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MASK_SRC, MASK_DST)
        log("✅ clipmakers_hardstop.md → Виктор")
    else:
        log("○ dry-run: не скопирована")

    # Маска Монтажёра
    if MONTEUR_MASK_SRC.exists():
        log_action("006_MONTEUR/forge/masks/clipmakers.md")
        if not DRY_RUN:
            MONTEUR_MASKS.mkdir(parents=True, exist_ok=True)
            shutil.copy2(MONTEUR_MASK_SRC, MONTEUR_MASK_DST)
            log("✅ clipmakers.md → Монтажёр")
    else:
        log(f"⚠  monteur_clipmakers.md не найден рядом со скриптом")

    # A06 промт
    if A06_PROMPT_SRC.exists():
        log_action("A06/forge/prompt.md — banana_prompt + Wan2.2")
        if not DRY_RUN:
            if A06_PROMPT_DST.exists():
                backup(A06_PROMPT_DST)
            shutil.copy2(A06_PROMPT_SRC, A06_PROMPT_DST)
            log("✅ A06 Гимбал Гас промт обновлён")
    else:
        log(f"⚠  prompt_A06_gimbal_gus.md не найден рядом со скриптом")

    # A08 промт
    if A08_PROMPT_SRC.exists():
        log_action("A08/forge/prompt.md — banana_prompt дрон + Wan2.2")
        if not DRY_RUN:
            if A08_PROMPT_DST.exists():
                backup(A08_PROMPT_DST)
            shutil.copy2(A08_PROMPT_SRC, A08_PROMPT_DST)
            log("✅ A08 Дрон Дэн промт обновлён")
    else:
        log(f"⚠  prompt_A08_drone_dan.md не найден рядом со скриптом")


# ─── Документы цеха ───────────────────────────────────────

def place_docs():
    print("\n[5/6] Документы цеха (CHAIN_CONTRACT.md, CLIPMAKERS_RULES.md)")
    for src, dst in [(CONTRACT_SRC, CONTRACT_DST), (RULES_SRC, RULES_DST)]:
        if not src.exists():
            log(f"⚠  {src.name} не найден — пропуск")
            continue
        log_action(f"Скопировать {src.name} → modules/clipmakers/")
        if not DRY_RUN:
            shutil.copy2(src, dst)
            log(f"✅ {dst.name}")
        else:
            log(f"○ dry-run: не скопирован")


# ─── Финальная проверка ───────────────────────────────────

def final_check():
    print("\n[6/6] Финальная проверка")

    checks = {
        "manifest.json":                MANIFEST_PATH,
        "hooks.py":                     HOOKS_PATH,
        "info.json":                    CLIPMAKERS / "info.json",
        "interaction_log":              ILOG_PATH,
        "A01/dna.json":                 CLIPMAKERS / "A01" / "dna.json",
        "A12/forge/prompt.md":          CLIPMAKERS / "A12" / "forge" / "prompt.md",
        "005_VICTOR/forge/masks/ (dir)": VICTOR_MASKS,
        "clipmakers_hardstop.md":       MASK_DST,
        "monteur/masks/clipmakers.md":  MONTEUR_MASK_DST,
        "A06/forge/prompt.md":          A06_PROMPT_DST,
        "A08/forge/prompt.md":          A08_PROMPT_DST,
    }
    for label, path in checks.items():
        status = "✅" if path.exists() else "❌"
        print(f"  {status} {label}")

    if MANIFEST_PATH.exists():
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        rt = data.get("run_type", "?")
        qa = data.get("qa_agent", "?")
        hs = data.get("hard_stop", {})
        print(f"  {'✅' if rt == 'clipmakers' else '❌'} manifest.run_type = \"{rt}\"")
        print(f"  {'✅' if qa == 'A12' else '❌'} manifest.qa_agent = \"{qa}\"")
        print(f"  {'✅' if hs.get('after_agent') == 'A03' else '❌'} "
              f"manifest.hard_stop.after_agent = \"{hs.get('after_agent', '?')}\"")
        print(f"  {'✅' if 'victor' in hs.get('residents', []) else '❌'} "
              f"manifest.hard_stop.residents = {hs.get('residents', [])}")
        print(f"  {'✅' if hs.get('web_search') else '❌'} "
              f"manifest.hard_stop.web_search = {hs.get('web_search', False)}")


# ─── main ─────────────────────────────────────────────────

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n{'='*60}")
    print(f"  patch_clipmakers_launch.py  [{mode}]")
    print(f"  Цех: {CLIPMAKERS}")
    print(f"{'='*60}")

    fix_manifest()
    fix_hooks()
    fix_interaction_log()
    place_victor_mask()
    place_docs()
    final_check()

    print(f"\n{'='*60}")
    if DRY_RUN:
        print("  Dry-run. Применить: python patch_clipmakers_launch.py --apply")
    else:
        print("  ✅ Патч применён:")
        print("     • manifest: run_type + qa_agent + hard_stop (Виктор после A03)")
        print("     • hooks.py v2.0: fal.ai + Wan2.2 + Монтажёр")
        print("     • interaction_log создан")
        print("     • clipmakers_hardstop.md → 005_VICTOR/forge/masks/")
        print("     • бэкапы: .bak_sprint40_launch")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
