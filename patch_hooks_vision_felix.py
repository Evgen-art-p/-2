"""
patch_hooks_vision_felix.py
============================
Патч hooks.py video_long:
  1. Ева A06 — vision-check с архивом брака в output/rejected/{project_id}/
  2. Феликс A08 — генерация клипов через SiliconFlow Wan2.2 + vision-check

Запуск:
  python patch_hooks_vision_felix.py          # dry-run
  python patch_hooks_vision_felix.py --apply  # применить
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

BASE       = Path(__file__).parent
HOOKS_PATH = BASE / "studio/modules/video_long/hooks.py"
BACKUP_DIR = BASE / "_patch_backups" / f"hooks_vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ── 1. Замена вызовов генерации в Еве ────────────────────────────────────────

OLD_BIBLE_GEN = '        raw = _generate_with_retry(prompt, [], filename, "A06", slot_id)'
NEW_BIBLE_GEN = '''\
        raw = _generate_with_vision_check(
            prompt=prompt, ref_ids=[], filename=filename,
            agent_id="A06", slot_id=slot_id,
            project_id=state.get("project_id", ""),
            vision_rules="BIBLE режим: эталонный персонаж/локация. Строгая анатомия, профессиональное качество."
        )'''

OLD_EP_GEN = '            raw = _generate_with_retry(prompt, ref_ids, filename, "A06", slot_id)'
NEW_EP_GEN = '''\
            raw = _generate_with_vision_check(
                prompt=prompt, ref_ids=ref_ids, filename=filename,
                agent_id="A06", slot_id=slot_id,
                project_id=state.get("project_id", ""),
                vision_rules="EPISODE кадр: соответствие раскадровке Лукаса. Строгая анатомия, 16:9 формат."
            )'''

# ── 2. Диспетчер — добавить вызов _felix_generate_clips ──────────────────────

OLD_FELIX_DISPATCH = '''\
    elif worker_id == "A08":
        _felix_log_interaction(state, human_text)'''
NEW_FELIX_DISPATCH = '''\
    elif worker_id == "A08":
        _felix_log_interaction(state, human_text)
        if mode == "episode":
            _felix_generate_clips(state, human_text)'''

# ── 3. Новые функции — вставляем перед _build_storyboard_map ─────────────────

OLD_UTILS_MARKER = '''\
# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════

def _build_storyboard_map'''

NEW_UTILS_MARKER = '''\
# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════


def _generate_with_vision_check(prompt: str, ref_ids: list, filename: str,
                                 agent_id: str, slot_id: str,
                                 project_id: str = "",
                                 vision_rules: str = "") -> str:
    """
    Генерирует картинку через fal.ai + проверяет ОТК через vision_client.
    При REJECTED — брак архивируется в output/rejected/{project_id}/,
    промпт корректируется через fix_hint, максимум 3 попытки.
    Если vision_client недоступен — работает как _generate_with_retry.
    """
    try:
        from studio.vision_client import generate_with_vision_check as _otk
    except ImportError:
        print(f"[{agent_id}] ⚠️  vision_client не найден — работаю без ОТК")
        return _generate_with_retry(prompt, ref_ids, filename, agent_id, slot_id)

    current_prompt  = [prompt]
    negative_suffix = [""]

    def _gen():
        full = current_prompt[0]
        if negative_suffix[0]:
            full += f", --no {negative_suffix[0]}"
        return _generate_with_retry(full, ref_ids, filename, agent_id, slot_id)

    def _on_retry(attempt: int, fix_hint: str):
        if fix_hint:
            negative_suffix[0] = (negative_suffix[0] + ", " + fix_hint).strip(", ")
            print(f"[{agent_id} ОТК] Добавляю в негатив: {fix_hint}")

    return _otk(
        generate_fn=_gen,
        original_prompt=prompt,
        agent_id=agent_id,
        rules=vision_rules,
        max_visual_retries=3,
        on_retry=_on_retry,
        project_id=project_id,
    )


def _felix_generate_clips(state: dict, human_text: str):
    """
    A08 ФЕЛИКС — генерация видео-клипов через SiliconFlow Wan2.2 I2V.
    Читает felix_vfx.video_clips[], берёт картинки из eva_visuals.frames[].path,
    для каждого клипа:
      1. Генерирует mp4 через Wan2.2
      2. Проверяет через ОТК (первый + последний кадр)
      3. При REJECTED — брак в output/rejected/{project_id}/, перегенерирует
      4. Пишет video_path обратно в state
    """
    try:
        from studio.siliconflow_client import generate_video_with_retry
    except ImportError:
        print("[A08 Феликс] ❌ siliconflow_client не найден — пропускаю")
        return

    try:
        from studio.vision_client import generate_with_vision_check as _otk
        has_otk = True
    except ImportError:
        print("[A08 Феликс] ⚠️  vision_client не найден — ОТК для клипов отключён")
        has_otk = False

    data = _parse_json(human_text)
    if not data:
        print("[A08 Феликс] JSON не найден — пропускаю")
        return

    my_output   = data.get("my_output", data)
    video_clips = my_output.get("video_clips", [])
    if not video_clips:
        print("[A08 Феликс] video_clips пуст — пропускаю")
        return

    # Карта frame_id/shot_id → path из eva_visuals.frames[]
    chain      = state.get("chain_data", {})
    eva_frames = (chain.get("eva_visuals", {}).get("frames", [])
                  if isinstance(chain.get("eva_visuals"), dict) else [])
    frame_map  = {f.get("frame_id", ""): f.get("path") for f in eva_frames}
    shot_map   = {f.get("shot_id",  ""): f.get("path") for f in eva_frames}

    project_id  = state.get("project_id", "")
    project_dir = OUTPUT_DIR / (project_id or "vl_episode_unknown")
    project_dir.mkdir(parents=True, exist_ok=True)
    slot_id = state.get("_slot_id", "video_long")
    total   = len(video_clips)

    print(f"[A08 Феликс] 🎬 Генерация {total} клипов через Wan2.2 I2V...")

    results = []
    for idx, clip in enumerate(video_clips):
        frame_id = clip.get("frame_id", "")
        shot_id  = clip.get("shot_id",  "")
        scene_id = clip.get("scene_id", "")
        motion   = clip.get("motion_prompt", "")
        duration = clip.get("duration_sec", 5)
        camera   = clip.get("camera_move", "static")

        img_path = frame_map.get(frame_id) or shot_map.get(shot_id)
        if not img_path or not Path(img_path).exists():
            print(f"[A08 Феликс] ❌ {frame_id or shot_id}: картинка не найдена")
            clip["video_path"] = None
            results.append(clip)
            continue

        if not motion:
            print(f"[A08 Феликс] ❌ {frame_id}: motion_prompt пуст")
            clip["video_path"] = None
            results.append(clip)
            continue

        filename       = (f"{_slugify(str(scene_id))[:20]}_"
                          f"{_slugify(str(shot_id or frame_id))[:15]}.mp4")
        dest           = project_dir / filename
        current_motion = [motion]

        def _gen_clip():
            path = generate_video_with_retry(
                image_path=img_path,
                motion_prompt=current_motion[0],
                filename=filename,
                duration=duration,
                resolution="720p",
                agent_id="A08",
                slot_id=slot_id,
            )
            import shutil as _sh
            _sh.move(path, dest)
            return str(dest)

        print(f"[A08 Феликс] → клип {idx+1}/{total}: {filename}")
        try:
            if has_otk:
                def _on_retry(attempt, fix_hint):
                    if fix_hint:
                        current_motion[0] = motion + f", avoid: {fix_hint}"
                        print(f"[A08 ОТК] motion_prompt скорректирован")

                from studio.vision_client import generate_with_vision_check as _otk_fn
                video_path = _otk_fn(
                    generate_fn=_gen_clip,
                    original_prompt=motion,
                    agent_id="A08",
                    rules=(f"Видео-клип. Камера: {camera}. "
                           "Плавность движения, анатомия в первом и последнем кадре."),
                    max_visual_retries=3,
                    on_retry=_on_retry,
                    project_id=project_id,
                )
            else:
                video_path = _gen_clip()

            clip["video_path"] = video_path
            print(f"[A08 Феликс] ✅ {filename}")

        except Exception as e:
            print(f"[A08 Феликс] ❌ {frame_id}: {e}")
            clip["video_path"] = None
            clip["error"]      = str(e)

        results.append(clip)

    ok = sum(1 for c in results if c.get("video_path"))
    print(f"[A08 Феликс] 🎬 Итог: {ok}/{total} клипов готово")

    my_output["video_clips"] = results
    if "my_output" in data:
        data["my_output"] = my_output
    _update_state(state, data)


def _build_storyboard_map'''

# ─── Main ─────────────────────────────────────────────────────────────────────

PATCHES = [
    ("bible_gen → vision_check",   OLD_BIBLE_GEN,       NEW_BIBLE_GEN),
    ("episode_gen → vision_check", OLD_EP_GEN,          NEW_EP_GEN),
    ("felix_dispatch + clips",     OLD_FELIX_DISPATCH,  NEW_FELIX_DISPATCH),
    ("new functions block",        OLD_UTILS_MARKER,    NEW_UTILS_MARKER),
]


def main():
    apply = "--apply" in sys.argv
    print(f"\n🔧 patch_hooks_vision_felix.py")
    print(f"   Режим: {'APPLY' if apply else 'DRY-RUN'}")

    if not HOOKS_PATH.exists():
        print(f"❌ hooks.py не найден: {HOOKS_PATH}")
        print("   Убедись что скрипт в корне репо")
        sys.exit(1)

    original = HOOKS_PATH.read_text(encoding="utf-8")
    patched  = original

    for label, old, new in PATCHES:
        if old in patched:
            patched = patched.replace(old, new)
            print(f"  ✅ {label}")
        else:
            print(f"  ⚠️  Не найден: {label}")

    if patched == original:
        print("\n✅ hooks.py уже актуален")
        return

    # Показываем diff
    old_lines = original.splitlines()
    new_lines = patched.splitlines()
    diffs = []
    for i in range(max(len(old_lines), len(new_lines))):
        a = old_lines[i] if i < len(old_lines) else None
        b = new_lines[i] if i < len(new_lines) else None
        if a != b:
            if a is not None: diffs.append(f"  - {a.rstrip()}")
            if b is not None: diffs.append(f"  + {b.rstrip()}")
    print(f"\n{'─'*55}\n  hooks.py ({len(diffs)//2} строк)\n{'─'*55}")
    for d in diffs[:80]:
        print(d)
    if len(diffs) > 80:
        print(f"  ... ещё {len(diffs)-80} строк")

    if apply:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HOOKS_PATH, BACKUP_DIR / "hooks.py.bak")
        HOOKS_PATH.write_text(patched, encoding="utf-8")
        print(f"\n✅ hooks.py обновлён. Бэкап: {BACKUP_DIR}")
        print("   Stage All → Commit → Push 🚀")
    else:
        print(f"\n   Запусти с --apply")


if __name__ == "__main__":
    main()
