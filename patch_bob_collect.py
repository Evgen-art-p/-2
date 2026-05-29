#!/usr/bin/env python3
"""
patch_bob_collect.py
====================
Точечный патч: _bob_collect_media в hooks.py
veo3_prompts → video_clips + video_path

Применять ПОСЛЕ patch_hooks_sam_bob.py (патчи 2 и 3 уже применены).
Запуск из корня репо: python patch_bob_collect.py
"""

from pathlib import Path

HOOKS_PATH = Path("studio/modules/video_long/hooks.py")

# Ищем по уникальному маркеру — строке с veo3_prompts
OLD = '            deliverables["veo3_prompts"] = [{'

NEW = '''            deliverables["video_clips"] = [{
                "frame_id":      f.get("frame_id", ""),
                "shot_id":       f.get("shot_id", ""),
                "scene_id":      f.get("scene_id", ""),
                "motion_prompt": f.get("motion_prompt", ""),
                "camera_move":   f.get("camera_move", ""),
                "duration_sec":  f.get("duration_sec", 0),
                "ref_ids":       f.get("ref_ids", []),
                "vfx_layer":     f.get("vfx_layer", "none"),
                "video_path":    f.get("video_path"),
                "clip_assessment": f.get("clip_assessment", {}),
            } for f in felix_clips]'''

# Старый хвост блока — убираем его тоже
OLD_TAIL = '''                "shot_id":  f.get("shot_id", ""),
                "camera":   f.get("camera_move", ""),
                "duration": f.get("duration_sec", 0),
                "prompt":   f.get("motion_prompt", ""),
                "ref_ids":  f.get("ref_ids", []),
                "vfx_layer": f.get("vfx_layer", ""),
            } for f in felix_clips]'''

# Старый print
OLD_PRINT = '            print(f"[EPISODE A12]   veo3_prompts: {len(deliverables[\'veo3_prompts\'])} клипов")'
NEW_PRINT = '''            ok = sum(1 for c in deliverables["video_clips"] if c.get("video_path"))
            total = len(deliverables["video_clips"])
            print(f"[EPISODE A12]   video_clips : {ok}/{total} клипов с video_path")'''

# Старый комментарий
OLD_COMMENT = '''    # ── A08 Феликс: veo3_prompts ────────────────────────────────────────
    # FIX v2.1: поле "video_clips" согласно CHAIN_CONTRACT (было key_frames/veo3_prompts)
    #           поле промпта "motion_prompt" (было veo_prompt_en / veo3_prompt)
    #           поле камеры  "camera_move"   (было camera_movement)'''

NEW_COMMENT = '''    # ── A08 Феликс: video_clips (реальные mp4) ──────────────────────────
    # LONG_RULES v4.3 правило 16: video_clips[*].video_path — реальные mp4, не промпты
    # patch_bob_collect: veo3_prompts → video_clips + video_path'''


def apply():
    if not HOOKS_PATH.exists():
        print(f"❌ Не найден: {HOOKS_PATH}")
        print("   Запускай из корня репо.")
        return False

    text = HOOKS_PATH.read_text(encoding="utf-8")

    if 'deliverables["video_clips"]' in text and 'deliverables["veo3_prompts"]' not in text:
        print("ℹ️  ПАТЧ 1 уже применён — veo3_prompts не найден, video_clips есть.")
        return True

    if 'deliverables["veo3_prompts"]' not in text:
        print("⚠️  Ни veo3_prompts ни video_clips не найдены — что-то не так с файлом.")
        print(f"   Проверь вручную: {HOOKS_PATH}")
        return False

    original = text

    # Шаг 1: комментарий
    if OLD_COMMENT in text:
        text = text.replace(OLD_COMMENT, NEW_COMMENT)
        print("✅ Шаг 1: комментарий обновлён")
    else:
        print("⚠️  Шаг 1: комментарий не найден точно — пропускаю")

    # Шаг 2: строка с veo3_prompts + хвост
    FULL_OLD_BLOCK = OLD + '\n' + OLD_TAIL
    FULL_NEW_BLOCK = NEW

    if FULL_OLD_BLOCK in text:
        text = text.replace(FULL_OLD_BLOCK, FULL_NEW_BLOCK)
        print("✅ Шаг 2: deliverables[veo3_prompts] → deliverables[video_clips] + video_path")
    elif OLD in text:
        # Fallback: заменяем только первую строку + убираем хвост по отдельности
        text = text.replace(OLD, '            deliverables["video_clips"] = [{')
        if OLD_TAIL in text:
            text = text.replace(OLD_TAIL, NEW.split('\n', 1)[1])  # без первой строки
        print("✅ Шаг 2 (fallback): video_clips + video_path")
    else:
        print("❌ Шаг 2: блок не найден — нужна ручная правка")

    # Шаг 3: print
    if OLD_PRINT in text:
        text = text.replace(OLD_PRINT, NEW_PRINT)
        print("✅ Шаг 3: print обновлён (ok/total клипов с video_path)")
    else:
        print("⚠️  Шаг 3: print не найден точно — пропускаю")

    if text == original:
        print("\n⚠️  Файл не изменился. Проверь вручную:")
        print(f"   grep -n 'veo3_prompts' {HOOKS_PATH}")
        return False

    backup = HOOKS_PATH.with_suffix(".py.bak_collect")
    backup.write_text(original, encoding="utf-8")
    print(f"\n💾 Бэкап: {backup}")
    HOOKS_PATH.write_text(text, encoding="utf-8")
    print(f"✅ Записано: {HOOKS_PATH}")

    # Финальная проверка
    result = HOOKS_PATH.read_text(encoding="utf-8")
    if 'deliverables["video_clips"]' in result and 'deliverables["veo3_prompts"]' not in result:
        print("\n🎉 ПАТЧ 1 применён успешно!")
        print("   deliverables теперь содержит video_clips с video_path")
        return True
    else:
        print("\n⚠️  Проверь файл вручную — что-то могло пойти не так")
        return False


if __name__ == "__main__":
    apply()
