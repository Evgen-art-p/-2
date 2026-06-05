"""
patch_assembly_video_shorts.py
Студия «Шесть Пальцев» · Спринт 40

ЧТО ДЕЛАЕТ:
  Добавляет video_shorts в сборочный цех (assembly/__init__.py):
  1. _find_projects() — распознаёт slot_id == "video_shorts"
     считает clips_count и frames_count из deliverables video_shorts
  2. _render_workbench() — добавляет ветку elif slot == "video_shorts"
     → вызывает _render_shorts_workbench()
  3. Добавляет функцию _render_shorts_workbench() — верстак для shorts:
     - финальный ролик (если собран)
     - кадры от Веры (9:16 превью)
     - обложки A/B от Тамб Тома
     - аудио статус (музыка / SFX / VO)
     - публикация (SEO, хештеги, время)

ЗАПУСК из корня проекта:
  python patch_assembly_video_shorts.py
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

ASSEMBLY_INIT = Path("studio/assembly/__init__.py")


def check():
    if not ASSEMBLY_INIT.exists():
        print(f"❌  Не найден: {ASSEMBLY_INIT}")
        sys.exit(1)
    print(f"✅  Найден: {ASSEMBLY_INIT}")


def backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = ASSEMBLY_INIT.with_suffix(f".py.bak_{stamp}")
    shutil.copy2(ASSEMBLY_INIT, dest)
    print(f"📦  Бэкап: {dest}")
    return dest


# ─── Изменение 1: _find_projects() ──────────────────────────────────────────
# Добавляем обработку video_shorts рядом с social_mix

OLD_FIND = """        # social_mix: считаем картинки вместо клипов
        if slot_id == "social_mix":
            images = deliverables.get("images", [])
            if not images and deliverables.get("image_path"):
                images = [{"path": deliverables["image_path"]}]
            clips_count  = 0
            frames_count = len(images)
            has_audio    = False
        else:
            clips_count  = len(deliverables.get("video_clips", []))
            frames_count = len(deliverables.get("key_frames", []))
            has_audio    = bool(deliverables.get("audio"))"""

NEW_FIND = """        # social_mix: считаем картинки вместо клипов
        if slot_id == "social_mix":
            images = deliverables.get("images", [])
            if not images and deliverables.get("image_path"):
                images = [{"path": deliverables["image_path"]}]
            clips_count  = 0
            frames_count = len(images)
            has_audio    = False
        elif slot_id == "video_shorts":
            # video_shorts: клипы от Стэна (stan_video) + кадры от Веры (vera_visual)
            clips_count  = len(deliverables.get("video_clips", []))
            frames_count = len(deliverables.get("key_frames", []))
            has_audio    = bool(
                deliverables.get("audio", {}).get("music", {}).get("audio_path")
                or deliverables.get("audio", {}).get("sfx_list")
                or deliverables.get("audio", {}).get("vo_lines")
            )
        else:
            clips_count  = len(deliverables.get("video_clips", []))
            frames_count = len(deliverables.get("key_frames", []))
            has_audio    = bool(deliverables.get("audio"))"""


# ─── Изменение 2: _render_workbench() ───────────────────────────────────────
# Добавляем ветку video_shorts перед стандартным рендером

OLD_RENDER = """        # ── SOCIAL MIX: превью поста ─────────────────────────────
        if slot == "social_mix":
            _render_social_workbench(el, d, pid)
            return"""

NEW_RENDER = """        # ── SOCIAL MIX: превью поста ─────────────────────────────
        if slot == "social_mix":
            _render_social_workbench(el, d, pid)
            return

        # ── VIDEO SHORTS: вертикальный ролик ─────────────────────
        elif slot == "video_shorts":
            _render_shorts_workbench(el, d, pid, assembly)
            return"""


# ─── Изменение 3: новая функция _render_shorts_workbench() ──────────────────
# Вставляем перед def page_assembly():

OLD_PAGE = """def page_assembly():"""

NEW_PAGE = '''def _render_shorts_workbench(el, d: dict, pid: str, assembly: dict):
    """
    Верстак для video_shorts.
    Показывает: финальный ролик (если собран) → кадры Веры 9:16 →
    обложки A/B Тамб Тома → аудио статус → SEO публикация.
    """
    with el:
        # ── Финальный ролик ──────────────────────────────────────
        final_path = assembly.get("final_path")
        if final_path and Path(final_path).exists():
            rel = "/" + str(Path(final_path)).replace("\\\\", "/")
            ui.html('<div class="mt-sec">🎬 ФИНАЛЬНЫЙ РОЛИК (9:16)</div>')
            ui.html(
                f\'<video controls style="width:100%;max-height:400px;\'
                f\'border-radius:10px;background:#000;margin-bottom:8px">\'
                f\'<source src="{rel}" type="video/mp4"></video>\'
            )
            dur = assembly.get("duration_sec", 0)
            cl  = assembly.get("clips_used", 0)
            ct  = assembly.get("clips_total", 0)
            ui.html(
                f\'<div class="mt-meta">\'
                f\'<span>⏱ {dur:.1f}с</span>\'
                f\'<span>🎞 {cl}/{ct} клипов</span>\'
                f\'<span>🔊{"✅" if assembly.get("has_audio") else "—"}</span>\'
                f\'<span>🎙{"✅" if assembly.get("has_vo") else "—"}</span>\'
                f\'</div>\'
            )
        else:
            # Ещё не собран — показываем готовые клипы
            clips = d.get("video_clips", [])
            ready = [c for c in clips if c.get("video_path") and
                     Path(c["video_path"]).exists()]
            ui.html(
                f\'<div class="mt-not-assembled">\'
                f\'Сборка ещё не запущена.<br>\'
                f\'Клипов готово: {len(ready)}/{len(clips)}\'
                f\'</div>\'
            )

        # ── Кадры Веры 9:16 ─────────────────────────────────────
        key_frames = d.get("key_frames", [])
        if isinstance(key_frames, list) and key_frames:
            ready_frames = [f for f in key_frames
                            if isinstance(f, dict) and f.get("path")
                            and Path(f["path"]).exists()]
            if ready_frames:
                ui.html(
                    f\'<div class="mt-sec" style="margin-top:12px">\'
                    f\'🖼 КАДРЫ ВЕРЫ ({len(ready_frames)}/{len(key_frames)})</div>\'
                )
                with ui.row().style("gap:8px;flex-wrap:wrap;"):
                    for frame in ready_frames[:6]:
                        p   = frame["path"]
                        rel = "/" + str(Path(p)).replace("\\\\", "/")
                        fid = frame.get("frame_id", "")
                        seg = frame.get("segment", "")
                        va  = frame.get("self_assessment", {})
                        verdict = va.get("verdict", "") if isinstance(va, dict) else ""
                        v_icon  = "✅" if verdict == "APPROVED" else (
                                  "❌" if verdict == "REJECTED" else "")
                        ui.html(
                            f\'<div style="width:90px;flex-shrink:0;">\'
                            f\'<img src="{rel}" style="width:90px;height:160px;\'
                            f\'object-fit:cover;border-radius:6px;display:block;">\'
                            f\'<div style="font-family:JetBrains Mono;font-size:0.5rem;\'
                            f\'color:rgba(180,190,220,0.6);margin-top:3px;\'
                            f\'text-align:center;">{v_icon} {fid}<br>{seg}</div>\'
                            f\'</div>\'
                        )

        # ── Обложки A/B ──────────────────────────────────────────
        thumb = d.get("thumbnail", {})
        va_t  = thumb.get("variant_a", {}) if isinstance(thumb, dict) else {}
        vb_t  = thumb.get("variant_b", {}) if isinstance(thumb, dict) else {}
        if va_t.get("path") or vb_t.get("path"):
            ui.html(
                \'<div class="mt-sec" style="margin-top:12px">\'
                \'🖼 ОБЛОЖКИ A/B</div>\'
            )
            with ui.row().style("gap:8px;"):
                for label_t, v_t in [("A", va_t), ("B", vb_t)]:
                    p_t = v_t.get("path", "")
                    if p_t and Path(p_t).exists():
                        rel = "/" + str(Path(p_t)).replace("\\\\", "/")
                        overlay = v_t.get("text_overlay", "")
                        emotion = v_t.get("emotion", "")
                        ui.html(
                            f\'<div style="flex:1;min-width:0;">\'
                            f\'<div style="font-family:JetBrains Mono;font-size:0.6rem;\'
                            f\'color:rgba(180,190,220,0.6);margin-bottom:4px;">\'
                            f\'Вариант {label_t}</div>\'
                            f\'<img src="{rel}" style="width:100%;border-radius:8px;\'
                            f\'display:block;">\'
                            f\'{"<div class=\'mt-overlay\'>" + overlay + "</div>" if overlay else ""}\'
                            f\'{"<div style=\'font-size:0.5rem;color:rgba(180,190,220,0.5);\'>" + emotion + "</div>" if emotion else ""}\'
                            f\'</div>\'
                        )

        # ── Аудио статус ─────────────────────────────────────────
        audio = d.get("audio", {})
        if isinstance(audio, dict):
            music     = audio.get("music", {})
            sfx_list  = audio.get("sfx_list", [])
            vo_lines  = audio.get("vo_lines", [])
            music_ok  = bool(isinstance(music, dict) and music.get("audio_path")
                             and Path(music.get("audio_path","")).exists())
            sfx_ok    = sum(1 for s in sfx_list
                            if isinstance(s, dict) and s.get("sfx_path")
                            and Path(s.get("sfx_path","")).exists())
            vo_ok     = sum(1 for v in vo_lines
                            if isinstance(v, dict) and v.get("vo_path")
                            and Path(v.get("vo_path","")).exists())

            if music_ok or sfx_ok or vo_ok:
                ui.html(
                    \'<div class="mt-sec" style="margin-top:12px">\'
                    \'🎧 АУДИО</div>\'
                )
                assessment = (music.get("audio_assessment", {})
                              if isinstance(music, dict) else {})
                verdict_a  = assessment.get("verdict", "") if isinstance(assessment, dict) else ""
                v_icon_a   = "✅" if verdict_a == "APPROVED" else (
                             "❌" if verdict_a == "REJECTED" else "")
                ui.html(
                    f\'<div class="mt-meta">\'
                    f\'<span>🎵 Музыка: {"✅" if music_ok else "—"} {v_icon_a}</span>\'
                    f\'<span>💥 SFX: {sfx_ok}/{len(sfx_list)}</span>\'
                    f\'<span>🎙 VO: {vo_ok}/{len(vo_lines)}</span>\'
                    f\'</div>\'
                )

        # ── SEO / Публикация ─────────────────────────────────────
        seo = d.get("seo", {})
        if isinstance(seo, dict):
            title   = seo.get("title", "")
            desc    = seo.get("description", "")
            tags    = seo.get("hashtags", [])
            post_t  = d.get("posting_time", "")
            if title or desc or tags:
                ui.html(
                    \'<div class="mt-sec" style="margin-top:12px">\'
                    \'📱 ПУБЛИКАЦИЯ</div>\'
                )
                if title:
                    ui.html(
                        f\'<div style="font-family:JetBrains Mono;font-size:0.7rem;\'
                        f\'color:rgba(220,225,240,0.9);margin-bottom:4px;">\'
                        f\'{title}</div>\'
                    )
                if desc:
                    ui.html(f\'<div class="mt-desc">{desc[:200]}</div>\')
                if tags:
                    ui.html(
                        f\'<div class="mt-tags">\'
                        f\'{" ".join(tags[:12])}</div>\'
                    )
                if post_t:
                    ui.html(
                        f\'<div class="mt-posting">⏰ {post_t}</div>\'
                    )


def page_assembly():'''


def apply():
    check()
    bak = backup()

    src = ASSEMBLY_INIT.read_text(encoding="utf-8")

    # Проверяем что патч ещё не применён
    if "video_shorts" in src and "_render_shorts_workbench" in src:
        print("ℹ️  Патч уже применён (video_shorts и _render_shorts_workbench найдены)")
        sys.exit(0)

    # Изменение 1 — _find_projects
    if OLD_FIND not in src:
        print("❌  Якорь 1 (_find_projects) не найден — возможно код изменился")
        sys.exit(1)
    src = src.replace(OLD_FIND, NEW_FIND, 1)
    print("✅  Изменение 1: _find_projects() — video_shorts добавлен")

    # Изменение 2 — _render_workbench
    if OLD_RENDER not in src:
        print("❌  Якорь 2 (_render_workbench) не найден")
        sys.exit(1)
    src = src.replace(OLD_RENDER, NEW_RENDER, 1)
    print("✅  Изменение 2: _render_workbench() — ветка video_shorts добавлена")

    # Изменение 3 — _render_shorts_workbench + page_assembly
    if OLD_PAGE not in src:
        print("❌  Якорь 3 (page_assembly) не найден")
        sys.exit(1)
    src = src.replace(OLD_PAGE, NEW_PAGE, 1)
    print("✅  Изменение 3: _render_shorts_workbench() добавлена")

    # Записываем
    ASSEMBLY_INIT.write_text(src, encoding="utf-8")
    print(f"✅  Файл записан ({len(src)} символов)")

    # Синтаксис
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(ASSEMBLY_INIT)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌  Синтаксическая ошибка:\n{result.stderr}")
        ASSEMBLY_INIT.write_text(
            Path(str(bak)).read_text(encoding="utf-8"),
            encoding="utf-8"
        )
        print(f"↩️  Откат из бэкапа: {bak}")
        sys.exit(1)
    else:
        print("✅  Синтаксис OK")


def report():
    print()
    print("=" * 60)
    print("ПАТЧ ПРИМЕНЁН — video_shorts в сборочном цеху")
    print("=" * 60)
    print()
    print("Что изменилось:")
    print()
    print("  _find_projects():")
    print("    slot_id == 'video_shorts' → считает clips из video_clips[]")
    print("    has_audio → проверяет music.audio_path / sfx_list / vo_lines")
    print()
    print("  _render_workbench():")
    print("    elif slot == 'video_shorts' → _render_shorts_workbench()")
    print()
    print("  _render_shorts_workbench() — новая функция:")
    print("    1. Финальный ролик (если собран) — видеоплеер 9:16")
    print("    2. Кадры Веры — превью 9:16, self_assessment иконка")
    print("    3. Обложки A/B — от Тамб Тома")
    print("    4. Аудио статус — музыка / SFX / VO с audio_assessment")
    print("    5. SEO / публикация — заголовок, описание, хештеги, время")
    print()
    print("Не тронуто:")
    print("  social_mix, video_long — работают как прежде")
    print("  monteur.py — без изменений (video_shorts использует")
    print("               стандартный assemble() — клипы + аудио)")


if __name__ == "__main__":
    apply()
    report()
