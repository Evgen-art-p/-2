"""
patch_assembly_social.py
Студия «Шесть Пальцев» · Спринт 39

Что делает:
  Патчит studio/assembly/__init__.py — добавляет поддержку social_mix в Мастерской.

Изменения:
  1. _find_projects() — берёт social_mix проекты (deliverables.slot_id == "social_mix")
     вместе с видео-проектами. Показывает в очереди слева.
  2. _render_workbench() — если slot_id == "social_mix":
       показывает превью поста (картинка + caption + хэштеги + кнопка 📤)
       вместо видеоплеера.
  3. Заглушка «Нет проектов» — убирает упоминание Боба, говорит нейтрально.

Запуск: python patch_assembly_social.py
  из корня проекта (C:\\Users\\Евгений\\Desktop\\студия 2)
"""

import shutil
from pathlib import Path

TARGET = Path("studio/assembly/__init__.py")
BACKUP = TARGET.with_suffix(".py.bak_pre_social")


# ═══════════════════════════════════════════════════════════
# ПАТЧ 1 — заглушка «нет проектов»
# ═══════════════════════════════════════════════════════════

OLD_EMPTY = "ui.html('<div class=\"mt-empty\">Нет проектов<br>с APPROVED от Боба</div>')"
NEW_EMPTY = "ui.html('<div class=\"mt-empty\">Нет проектов<br>Запусти пайплайн — появятся здесь</div>')"


# ═══════════════════════════════════════════════════════════
# ПАТЧ 2 — _find_projects: добавляем social_mix
# ═══════════════════════════════════════════════════════════

OLD_FIND = '''        projects.append({
            "project_id":      project_id,
            "platform":        deliverables.get("platform", "—"),
            "slot":            deliverables.get("slot_id", "—"),
            "clips_count":     len(deliverables.get("video_clips", [])),
            "frames_count":    len(deliverables.get("key_frames", [])),
            "has_audio":       bool(deliverables.get("audio")),
            "assembly_status": assembly.get("status", "NOT_ASSEMBLED"),
            "deliverables":    deliverables,
            # final_dna оставляем пустым — он не нужен UI Мастерской
            "final_dna":       {},
        })'''

NEW_FIND = '''        slot_id = deliverables.get("slot_id", "")

        # social_mix: считаем картинки вместо клипов
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
            has_audio    = bool(deliverables.get("audio"))

        projects.append({
            "project_id":      project_id,
            "platform":        deliverables.get("platform", "—"),
            "slot":            slot_id or "—",
            "clips_count":     clips_count,
            "frames_count":    frames_count,
            "has_audio":       has_audio,
            "assembly_status": assembly.get("status", "NOT_ASSEMBLED"),
            "deliverables":    deliverables,
            "final_dna":       {},
        })'''


# ═══════════════════════════════════════════════════════════
# ПАТЧ 3 — _render_workbench: ветка для social_mix
# ═══════════════════════════════════════════════════════════

OLD_WORKBENCH = '''    def _render_workbench(proj: dict):
        """Рендерит продукт на верстаке — зависит от платформы и цеха."""
        el = refs["workbench"]
        if not el:
            return
        el.clear()
        d  = proj["deliverables"]
        fd = proj["final_dna"]
        pid = proj["project_id"]
        assembly = get_assembly_status(pid)

        with el:
            # ── Финальный ролик ──────────────────────────────────'''

NEW_WORKBENCH = '''    def _render_workbench(proj: dict):
        """Рендерит продукт на верстаке — зависит от платформы и цеха."""
        el = refs["workbench"]
        if not el:
            return
        el.clear()
        d    = proj["deliverables"]
        fd   = proj["final_dna"]
        pid  = proj["project_id"]
        slot = proj.get("slot", "")
        assembly = get_assembly_status(pid)

        # ── SOCIAL MIX: превью поста ─────────────────────────────
        if slot == "social_mix":
            _render_social_workbench(el, d, pid)
            return

        with el:
            # ── Финальный ролик ──────────────────────────────────'''


# ═══════════════════════════════════════════════════════════
# ПАТЧ 4 — добавить функцию _render_social_workbench
#           вставляем ПЕРЕД def _toggle_chat():
# ═══════════════════════════════════════════════════════════

SOCIAL_WORKBENCH_FN = '''
    def _render_social_workbench(container, d: dict, pid: str):
        """Превью поста для social_mix в центре Мастерской."""
        from pathlib import Path as _P
        import time as _time

        container.clear()
        with container:
            with ui.element("div").style(
                "display:grid;grid-template-columns:1fr 1fr;gap:20px;"
                "padding:16px;height:100%;box-sizing:border-box;overflow-y:auto;"
            ):
                # ── ЛЕВАЯ: картинка ──────────────────────────────
                with ui.element("div").style(
                    "display:flex;flex-direction:column;gap:10px;"
                ):
                    image_path = d.get("image_path", "")

                    # Превью картинки
                    with ui.element("div").style(
                        "background:rgba(255,255,255,0.03);"
                        "border:1px solid rgba(255,255,255,0.08);"
                        "border-radius:16px;overflow:hidden;"
                        "aspect-ratio:4/5;display:flex;"
                        "align-items:center;justify-content:center;"
                        "min-height:280px;"
                    ):
                        if image_path and _P(image_path).exists():
                            try:
                                from studio.assembly.constants import OUTPUT_DIR
                                rel = _P(image_path).relative_to(OUTPUT_DIR)
                                url = f"/output/{rel.as_posix()}?t={int(_time.time()*1000)}"
                            except Exception:
                                url = "/" + str(_P(image_path)).replace("\\\\", "/")
                            ui.image(url).style(
                                "width:100%;height:100%;object-fit:cover;"
                            )
                        else:
                            ui.html(
                                "<div style='text-align:center;'>"
                                "<div style='font-size:40px;'>🖼️</div>"
                                "<div style='color:rgba(255,255,255,0.25);"
                                "font-size:11px;margin-top:8px;'>"
                                "Картинка не найдена</div></div>"
                            )

                    # Качество
                    q_score = d.get("quality_score") or d.get("evan_quality_score")
                    if q_score:
                        q_color = "#00ff88" if float(q_score) >= 7 else "rgba(255,204,0,0.85)"
                        ui.html(
                            f'<div style="font-size:10px;color:{q_color};">'
                            f'⭐ {q_score}/10</div>'
                        )

                    # Кнопка 📤 ОПУБЛИКОВАТЬ
                    client_id = d.get("client_id", "")
                    if client_id:
                        def _publish(e, cid=client_id, p=pid):
                            try:
                                from studio.assembly.broadcaster import publish
                                result = publish(cid, p)
                                ui.notify(
                                    f"✅ Опубликовано · post_id {result['post_id']}",
                                    type="positive"
                                )
                            except Exception as ex:
                                ui.notify(str(ex), type="negative", timeout=8000)

                        ui.button("📤 ОПУБЛИКОВАТЬ", on_click=_publish).props(
                            "flat dense"
                        ).style(
                            "width:100%;height:36px;border-radius:10px;"
                            "border:1px solid rgba(0,255,136,0.4);"
                            "background:rgba(0,255,136,0.08);"
                            "color:rgba(0,255,136,0.95);"
                            "font-size:11px;font-weight:700;"
                        )
                    else:
                        ui.html(
                            '<div style="font-size:10px;color:rgba(255,255,255,0.25);">'
                            'client_id не задан — публикация через Broadcaster недоступна'
                            '</div>'
                        )

                # ── ПРАВАЯ: текст поста ──────────────────────────
                with ui.element("div").style(
                    "display:flex;flex-direction:column;gap:10px;overflow-y:auto;"
                ):
                    platform = (d.get("platform") or "instagram").upper()
                    tim_forecast = d.get("tim_forecast")

                    # Бейджи
                    badges = (
                        f'<span style="padding:3px 10px;border-radius:8px;'
                        f'font-size:10px;font-weight:700;'
                        f'background:rgba(0,204,255,0.12);'
                        f'color:rgba(0,204,255,0.85);">📱 {platform}</span>'
                    )
                    if tim_forecast is not None:
                        badges += (
                            f'<span style="padding:3px 10px;border-radius:8px;'
                            f'font-size:10px;font-weight:700;'
                            f'background:rgba(0,255,136,0.08);'
                            f'color:rgba(0,255,136,0.7);">'
                            f'🔥 viral {tim_forecast}/10</span>'
                        )
                    ui.html(
                        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
                        f'{badges}</div>'
                    )

                    def _sec(label, content, color="rgba(255,255,255,0.82)"):
                        if not content:
                            return
                        ui.html(
                            f'<div style="color:rgba(255,255,255,0.35);'
                            f'font-size:9px;font-weight:700;'
                            f'text-transform:uppercase;letter-spacing:0.1em;'
                            f'margin-top:6px;">{label}</div>'
                            f'<div style="color:{color};font-size:13px;'
                            f'line-height:1.55;">{content}</div>'
                        )

                    # Caption
                    caption = d.get("caption", "")
                    if caption:
                        _sec("CAPTION", caption.replace("\\n", "<br>"))

                    # CTA
                    cta = d.get("cta", {})
                    if isinstance(cta, dict):
                        cta_text = cta.get("text", "")
                    else:
                        cta_text = str(cta)
                    _sec("CTA", cta_text, "#00ff88")

                    # Хэштеги
                    hashtags = d.get("hashtags", [])
                    if hashtags:
                        tags_html = " ".join(
                            f'<span style="display:inline-block;padding:2px 7px;'
                            f'margin:2px;border-radius:7px;font-size:11px;'
                            f'background:rgba(0,255,136,0.07);'
                            f'color:rgba(0,255,136,0.65);">{t}</span>'
                            for t in hashtags
                        )
                        ui.html(
                            '<div style="color:rgba(255,255,255,0.35);'
                            'font-size:9px;font-weight:700;'
                            'text-transform:uppercase;letter-spacing:0.1em;'
                            'margin-top:6px;">#️⃣ ХЭШТЕГИ</div>'
                            f'<div style="line-height:2;">{tags_html}</div>'
                        )

                    # Первый комментарий
                    first_comment = d.get("first_comment", "")
                    _sec(
                        "💬 ПЕРВЫЙ КОММЕНТАРИЙ",
                        f'<i style="color:rgba(255,255,255,0.55);">'
                        f'{first_comment}</i>' if first_comment else ""
                    )

                    # Предупреждение о дефектах
                    fedya_risk = d.get("fedya_risk_score", 0) or 0
                    if float(fedya_risk) > 0.3:
                        neg = d.get("negative_prompt_next", "")
                        ui.html(
                            f'<div style="margin-top:8px;padding:8px 12px;'
                            f'border-radius:8px;background:rgba(255,149,0,0.06);'
                            f'border:1px solid rgba(255,149,0,0.2);">'
                            f'<span style="color:rgba(255,149,0,0.9);'
                            f'font-size:11px;font-weight:700;">'
                            f'⚠️ Риск: {fedya_risk}/1.0</span>'
                            + (f'<div style="color:rgba(255,255,255,0.4);'
                               f'font-size:10px;margin-top:4px;">'
                               f'Для след. рана: {neg}</div>' if neg else '')
                            + '</div>'
                        )

                    # Статус
                    has_img = bool(image_path and _P(image_path).exists())
                    s_color = "#00ff88" if has_img else "rgba(255,204,0,0.85)"
                    s_text = "✅ Готово к публикации" if has_img else "⏳ Картинка не найдена"
                    ui.html(
                        f'<div style="margin-top:8px;padding:6px 12px;'
                        f'border-radius:8px;background:rgba(255,255,255,0.03);'
                        f'border:1px solid rgba(255,255,255,0.06);">'
                        f'<span style="color:{s_color};font-size:11px;'
                        f'font-weight:700;">{s_text}</span></div>'
                    )

'''

OLD_TOGGLE = "    def _toggle_chat():"
NEW_TOGGLE = SOCIAL_WORKBENCH_FN + "    def _toggle_chat():"


# ═══════════════════════════════════════════════════════════
# ПРИМЕНЯЕМ
# ═══════════════════════════════════════════════════════════

def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    shutil.copy2(TARGET, BACKUP)
    print(f"✅ Бэкап: {BACKUP}")

    text = TARGET.read_text(encoding="utf-8")

    # Патч 1
    if OLD_EMPTY in text:
        text = text.replace(OLD_EMPTY, NEW_EMPTY)
        print("✅ Патч 1: заглушка обновлена")
    else:
        print("⚠️  Патч 1: заглушка не найдена — пропускаю")

    # Патч 2
    if OLD_FIND in text:
        text = text.replace(OLD_FIND, NEW_FIND)
        print("✅ Патч 2: _find_projects обновлён")
    else:
        print("⚠️  Патч 2: _find_projects — строка не найдена — пропускаю")

    # Патч 3
    if OLD_WORKBENCH in text:
        text = text.replace(OLD_WORKBENCH, NEW_WORKBENCH)
        print("✅ Патч 3: _render_workbench обновлён")
    else:
        print("⚠️  Патч 3: _render_workbench — строка не найдена — пропускаю")

    # Патч 4
    if OLD_TOGGLE in text and "_render_social_workbench" not in text:
        text = text.replace(OLD_TOGGLE, NEW_TOGGLE)
        print("✅ Патч 4: _render_social_workbench добавлена")
    elif "_render_social_workbench" in text:
        print("ℹ️  Патч 4: _render_social_workbench уже есть — пропускаю")
    else:
        print("⚠️  Патч 4: _toggle_chat не найден — пропускаю")

    TARGET.write_text(text, encoding="utf-8")

    # Синтаксис-чек
    import subprocess
    r = subprocess.run(
        ["python", "-m", "py_compile", str(TARGET)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("✅ Синтаксис OK")
    else:
        print(f"❌ Синтаксис ошибка:\n{r.stderr}")
        print("⏪ Откатываю...")
        shutil.copy2(BACKUP, TARGET)
        print("✅ Откат выполнен")


if __name__ == "__main__":
    main()
