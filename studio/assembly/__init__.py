"""
Assembly — Мастерская Монтажёра
Левая:  Заказы на верстак (проекты от Боба)
Центр:  Верстак (продукт) + чат (скрыт, по кнопке)
Правая: Мастер (аватар + опыт)
"""
import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from nicegui import ui

from studio.assembly.css import ASSEMBLY_CSS, MONTEUR_CSS
from studio.assembly.monteur import get_assembly_status
from studio.cabinet.agents import get_avatar_url, BAR_COLORS, BAR_LABELS

RUNS_DIR   = Path("runs")
RENDER_DIR = Path("output/render")
MONTEUR_ID = "006_MONTEUR"
MONTEUR_DEPT = "residents"


# ═══════════════════════════════════════════════════════════════════
# ДАННЫЕ
# ═══════════════════════════════════════════════════════════════════

def _load_monteur() -> tuple[dict, dict]:
    """info.json + dna.json Монтажёра."""
    base = Path("studio/modules/residents") / MONTEUR_ID
    info, dna = {}, {}
    try:
        p = base / "info.json"
        if p.exists():
            info = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    try:
        p = base / "dna.json"
        if p.exists():
            dna = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return info, dna


def _parse_bob_file(path: Path) -> dict | None:
    """Читает файл Боба, возвращает данные если chain_status APPROVED."""
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(
            r"SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END",
            text, re.DOTALL
        )
        if not m:
            m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if not m:
            return None
        data = json.loads(m.group(1))
        status = (data.get("my_output", {})
                      .get("bob_marketing", {})
                      .get("chain_status", ""))
        if status != "APPROVED":
            return None
        return data
    except Exception:
        return None


def _find_projects() -> list[dict]:
    """Все проекты из runs/ с APPROVED от Боба."""
    projects = []
    if not RUNS_DIR.exists():
        return projects

    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        bob_files = (
            list(run_dir.glob("*A12*.md")) +
            list(run_dir.glob("*[Bb]ob*.md"))
        )
        for bob_file in bob_files:
            data = _parse_bob_file(bob_file)
            if not data:
                continue
            deliverables = data.get("deliverables", {})
            if not deliverables:
                continue
            final_dna  = data.get("my_output", {}).get("final_dna", {})
            project_id = deliverables.get("project_id", run_dir.name)
            assembly   = get_assembly_status(project_id)
            projects.append({
                "project_id":      project_id,
                "platform":        deliverables.get("platform", "—"),
                "slot":            final_dna.get("mode", "—").lower(),
                "clips_count":     len(deliverables.get("video_clips", [])),
                "frames_count":    len(deliverables.get("key_frames", [])),
                "has_audio":       bool(deliverables.get("audio")),
                "assembly_status": assembly.get("status", "NOT_ASSEMBLED"),
                "deliverables":    deliverables,
                "final_dna":       final_dna,
            })
            break  # один проект из папки

    return projects


def _load_history() -> list[dict]:
    """История сборок из assembly_manifest.json."""
    history = []
    if not RENDER_DIR.exists():
        return history
    for d in sorted(RENDER_DIR.iterdir(), reverse=True):
        m = d / "assembly_manifest.json"
        if not m.exists():
            continue
        try:
            history.append(json.loads(m.read_text(encoding="utf-8")))
        except Exception:
            pass
    return history[:15]


# ═══════════════════════════════════════════════════════════════════
# ГЛАВНАЯ СТРАНИЦА
# ═══════════════════════════════════════════════════════════════════

def page_assembly():

    state = {
        "projects":       [],
        "active":         None,   # выбранный проект
        "chat_open":      False,
        "chat_history":   [],
        "waiting":        False,
    }

    refs = {
        "queue":       None,
        "workbench":   None,   # центр — продукт
        "chat_wrap":   None,   # центр — чат (скрыт)
        "chat":        None,
        "chat_input":  None,
        "right_body":  None,   # правая — опыт мастера
    }

    ui.add_head_html(f"<style>{ASSEMBLY_CSS}{MONTEUR_CSS}</style>")
    ui.html('<div id="bg-asm"></div>')

    # ── HELPERS ──────────────────────────────────────────────────

    def _refresh_queue():
        state["projects"] = _find_projects()
        el = refs["queue"]
        if not el:
            return
        el.clear()
        with el:
            if not state["projects"]:
                ui.html('<div class="mt-empty">Нет проектов<br>с APPROVED от Боба</div>')
                return
            for proj in state["projects"]:
                pid = proj["project_id"]
                is_act = (state["active"] and
                          state["active"]["project_id"] == pid)
                s = proj["assembly_status"]
                icon = {"DONE":"✅","PARTIAL":"⚠️","FAILED":"❌"}.get(s,"⏳")
                cls = "mt-proj-card" + (" active" if is_act else "")
                if s == "DONE":
                    cls += " done"
                card = ui.element("div").classes(cls)
                card.on("click", lambda e, _p=proj: _select(_p))
                with card:
                    ui.html(
                        f'<div class="mt-proj-id">{icon} {pid[:24]}</div>'
                        f'<div class="mt-proj-meta">'
                        f'{proj["slot"]} · {proj["platform"]}</div>'
                        f'<div class="mt-proj-stats">'
                        f'🎬{proj["clips_count"]} '
                        f'🖼{proj["frames_count"]} '
                        f'{"🔊" if proj["has_audio"] else ""}</div>'
                    )

    def _select(proj: dict):
        state["active"] = proj
        _refresh_queue()
        _render_workbench(proj)

    def _render_workbench(proj: dict):
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
            # ── Финальный ролик ──────────────────────────────────
            final_path = assembly.get("final_path")
            if final_path and Path(final_path).exists():
                rel = "/" + str(Path(final_path)).replace("\\", "/")
                ui.html('<div class="mt-sec">🎬 ФИНАЛЬНЫЙ РОЛИК</div>')
                ui.html(
                    f'<video controls style="width:100%;max-height:320px;'
                    f'border-radius:10px;background:#000;margin-bottom:8px">'
                    f'<source src="{rel}" type="video/mp4"></video>'
                )
                dur = assembly.get("duration_sec", 0)
                cl  = assembly.get("clips_used", 0)
                ct  = assembly.get("clips_total", 0)
                ui.html(
                    f'<div class="mt-meta">'
                    f'<span>⏱ {dur:.1f}с</span>'
                    f'<span>🎞 {cl}/{ct} клипов</span>'
                    f'<span>🔊{"✅" if assembly.get("has_audio") else "—"}</span>'
                    f'<span>🎙{"✅" if assembly.get("has_vo") else "—"}</span>'
                    f'</div>'
                )
            else:
                # Ещё не собран — показываем что есть
                clips = d.get("video_clips", [])
                ready = [c for c in clips if c.get("video_path") and
                         Path(c["video_path"]).exists()]
                ui.html(
                    f'<div class="mt-not-assembled">'
                    f'Сборка ещё не запущена.<br>'
                    f'Клипов готово: {len(ready)}/{len(clips)}'
                    f'</div>'
                )

            # ── Обложки ─────────────────────────────────────────
            thumb = d.get("thumbnail", {})
            va = thumb.get("variant_a", {})
            vb = thumb.get("variant_b", {})
            if va.get("path") or vb.get("path"):
                ui.html('<div class="mt-sec" style="margin-top:12px">🖼 ОБЛОЖКИ</div>')
                with ui.row().style("gap:8px;"):
                    for v in (va, vb):
                        p = v.get("path", "")
                        if p and Path(p).exists():
                            rel = "/" + str(Path(p)).replace("\\", "/")
                            overlay = v.get("text_overlay", "")
                            ui.html(
                                f'<div style="flex:1;min-width:0;">'
                                f'<img src="{rel}" style="width:100%;'
                                f'border-radius:8px;display:block;">'
                                f'{"<div class=\'mt-overlay\'>" + overlay + "</div>" if overlay else ""}'
                                f'</div>'
                            )

            # ── Публикация ───────────────────────────────────────
            desc = d.get("description", "")
            tags = d.get("hashtags", [])
            post = d.get("posting_time", "")
            if desc or tags:
                ui.html('<div class="mt-sec" style="margin-top:12px">📱 ПУБЛИКАЦИЯ</div>')
                if desc:
                    ui.html(f'<div class="mt-desc">{desc}</div>')
                if tags:
                    ui.html(
                        f'<div class="mt-tags">'
                        f'{" ".join(tags[:10])}</div>'
                    )
                if post:
                    ui.html(f'<div class="mt-posting">⏰ {post}</div>')

    def _toggle_chat():
        state["chat_open"] = not state["chat_open"]
        cw = refs["chat_wrap"]
        if cw:
            cw.style(
                "display:flex;" if state["chat_open"] else "display:none;"
            )
        # Если первый раз открываем — приветствие
        if state["chat_open"] and not state["chat_history"]:
            proj = state["active"]
            if proj:
                _add_msg(
                    "assistant",
                    f"Смотрю пакет. "
                    f"Проект: {proj['project_id']} · "
                    f"Платформа: {proj['platform']} · "
                    f"Клипов: {proj['clips_count']}."
                )
            else:
                _add_msg("assistant", "Выбери проект слева — скажу что там.")

    def _add_msg(role: str, text: str):
        state["chat_history"].append({
            "role": role, "content": text,
            "time": datetime.now().strftime("%H:%M"),
        })
        _update_chat()

    def _update_chat():
        el = refs["chat"]
        if not el:
            return
        el.clear()
        with el:
            for msg in state["chat_history"]:
                role = msg["role"]
                cls  = "mt-msg-user" if role == "user" else "mt-msg-ai"
                lbl  = "ты" if role == "user" else "Монтажёр"
                ui.html(
                    f'<div class="mt-msg {cls}">'
                    f'<div class="mt-msg-role">{lbl}</div>'
                    f'<div class="mt-msg-text">'
                    f'{msg["content"].replace(chr(10),"<br>")}'
                    f'</div></div>'
                )
        ui.run_javascript(
            'const c=document.querySelector(".mt-chat-body");'
            'if(c) c.scrollTop=c.scrollHeight;'
        )

    async def _send():
        inp = refs["chat_input"]
        if not inp:
            return
        text = (inp.value or "").strip()
        if not text or state["waiting"]:
            return
        inp.set_value("")
        _add_msg("user", text)
        state["waiting"] = True
        try:
            from studio.cabinet.api import call_openrouter, DEFAULT_MODEL
            proj = state["active"]
            proj_ctx = ""
            if proj:
                proj_ctx = (
                    f" Текущий проект: {proj['project_id']}, "
                    f"платформа {proj['platform']}, "
                    f"клипов {proj['clips_count']}, "
                    f"аудио {'есть' if proj['has_audio'] else 'нет'}."
                )
            soul_ctx = ""
            try:
                from studio.grondheim_memory import on_agent_wake
                soul_ctx = on_agent_wake(MONTEUR_ID, MONTEUR_DEPT) or ""
            except Exception:
                pass

            system = (
                "Ты — Монтажёр, резидент студии «Шесть пальцев». "
                "Собираешь финальные ролики из материалов команды. "
                "Точный, немногословный. Говоришь по делу."
                + proj_ctx
                + ("\n\n" + soul_ctx if soul_ctx else "")
            )
            messages = [{"role": "system", "content": system}]
            for m in state["chat_history"][-10:]:
                messages.append({"role": m["role"], "content": m["content"]})

            reply = await call_openrouter(messages, DEFAULT_MODEL)
            _add_msg("assistant", reply)

            try:
                from studio.grondheim_memory import record_sensory_event, sync_to_dna
                record_sensory_event(
                    agent_id=MONTEUR_ID,
                    content=f"Шеф: {text[:100]} / Монтажёр: {reply[:100]}",
                    event_type="social", source="assembly",
                    emotional_weight=0.5, dept=MONTEUR_DEPT,
                )
                sync_to_dna(MONTEUR_ID, "cabinet_chat",
                            intensity=1.0, dept=MONTEUR_DEPT)
            except Exception:
                pass
        except Exception as e:
            _add_msg("assistant", f"⚠ {e}")
        finally:
            state["waiting"] = False

    def _refresh_right():
        """Правая панель — опыт мастера."""
        el = refs["right_body"]
        if not el:
            return
        el.clear()
        history = _load_history()
        with el:
            if not history:
                ui.html('<div class="mt-empty">Ничего не собрано</div>')
                return

            last = history[0]

            # Последняя работа
            ui.html('<div class="mt-right-sec">Последняя работа</div>')
            pid    = last.get("project_id", "—")
            status = last.get("status", "—")
            dur    = last.get("duration_sec", 0)
            cl     = last.get("clips_used", 0)
            ct     = last.get("clips_total", 0)
            ts     = last.get("assembled_at", "")[:16].replace("T", " ")
            icon   = {"DONE":"✅","PARTIAL":"⚠️","FAILED":"❌"}.get(status,"—")
            ui.html(
                f'<div class="mt-right-item">'
                f'<div class="mt-right-id">{icon} {pid[:20]}</div>'
                f'<div class="mt-right-meta">'
                f'{cl}/{ct} клипов · {dur:.0f}с</div>'
                f'<div class="mt-right-ts">{ts}</div>'
                f'</div>'
            )

            # Что пересобирал чаще
            from collections import Counter
            pid_counts = Counter(h.get("project_id","") for h in history)
            most = [p for p, c in pid_counts.most_common(3) if c > 1]
            if most:
                ui.html('<div class="mt-right-sec" style="margin-top:10px">Пересобирал чаще всего</div>')
                for p in most:
                    cnt = pid_counts[p]
                    ui.html(
                        f'<div class="mt-right-item">'
                        f'<div class="mt-right-id">{p[:20]}</div>'
                        f'<div class="mt-right-meta">{cnt} раз</div>'
                        f'</div>'
                    )

            # Последняя ошибка
            errors = [
                (h.get("project_id",""), h.get("errors",[])[0])
                for h in history
                if h.get("errors")
            ]
            if errors:
                pid_err, err_text = errors[0]
                ui.html('<div class="mt-right-sec" style="margin-top:10px">Последняя ошибка</div>')
                ui.html(
                    f'<div class="mt-right-item">'
                    f'<div class="mt-right-id">{pid_err[:20]}</div>'
                    f'<div class="mt-right-meta" style="color:rgba(248,113,113,0.7)">'
                    f'{err_text[:60]}</div>'
                    f'</div>'
                )

            # Вся история
            if len(history) > 1:
                ui.html('<div class="mt-right-sec" style="margin-top:10px">История</div>')
                for h in history[1:8]:
                    s  = h.get("status","—")
                    ic = {"DONE":"✅","PARTIAL":"⚠️","FAILED":"❌"}.get(s,"—")
                    ts2 = h.get("assembled_at","")[:16].replace("T"," ")
                    ui.html(
                        f'<div class="mt-right-item">'
                        f'<div class="mt-right-id">{ic} {h.get("project_id","")[:18]}</div>'
                        f'<div class="mt-right-ts">{ts2}</div>'
                        f'</div>'
                    )

    # ── LAYOUT ───────────────────────────────────────────────────

    with ui.element("div").classes("asm-app"):

        # HEADER
        with ui.element("div").classes("area-header glass"):
            with ui.row().style(
                "width:100%;height:100%;align-items:center;"
                "padding:0 20px;gap:8px;"
            ):
                ui.button(
                    "← BACK",
                    on_click=lambda: ui.navigate.to("/workshop")
                ).props("flat dense").style(
                    "height:36px;padding:0 14px;border-radius:10px;"
                    "border:1px solid rgba(255,255,255,0.2);"
                    "background:rgba(255,255,255,0.06);"
                    "color:white;font-weight:800;font-size:11px;"
                )
                ui.html(
                    '<div style="flex:1;font-family:JetBrains Mono;'
                    'font-size:13px;font-weight:900;letter-spacing:0.15em;'
                    'color:rgba(255,255,255,0.85);">🎬 МАСТЕРСКАЯ</div>'
                )
                ui.button(
                    "🔄 ОБНОВИТЬ",
                    on_click=lambda: _refresh_queue()
                ).props("flat dense").style(
                    "height:36px;padding:0 14px;border-radius:10px;"
                    "border:1px solid rgba(0,204,255,0.3);"
                    "background:rgba(0,204,255,0.08);"
                    "color:rgba(0,204,255,0.9);font-weight:800;font-size:11px;"
                )

        # LEFT — заказы на верстак
        with ui.element("div").classes("area-left glass").style(
            "display:flex;flex-direction:column;overflow:hidden;"
        ):
            ui.html('<div class="panel-title">ЗАКАЗЫ</div>')
            refs["queue"] = ui.element("div").style(
                "flex:1;overflow-y:auto;padding:8px;scrollbar-width:thin;"
            )
            _refresh_queue()

        # CENTER — верстак + чат
        with ui.element("div").classes("area-stage glass").style(
            "display:flex;flex-direction:column;overflow:hidden;"
        ):
            # Верстак — всегда виден
            refs["workbench"] = ui.element("div").style(
                "flex:1;overflow-y:auto;padding:16px;"
                "scrollbar-width:thin;min-height:0;"
            )
            with refs["workbench"]:
                ui.html(
                    '<div class="mt-empty" style="margin-top:80px">'
                    'Выбери проект слева</div>'
                )

            # Чат — скрыт, появляется по кнопке под аватаром
            refs["chat_wrap"] = ui.element("div").style(
                "display:none;flex-direction:column;"
                "border-top:1px solid rgba(255,255,255,0.06);"
                "height:42%;flex-shrink:0;"
            )
            with refs["chat_wrap"]:
                refs["chat"] = ui.element("div").classes("mt-chat-body").style(
                    "flex:1;overflow-y:auto;padding:10px 16px;"
                    "scrollbar-width:thin;"
                )
                with ui.element("div").style(
                    "padding:8px 12px;border-top:1px solid rgba(255,255,255,0.05);"
                    "background:rgba(20,23,34,0.4);"
                ):
                    with ui.row().style("gap:6px;align-items:flex-end;"):
                        refs["chat_input"] = ui.textarea(
                            placeholder="скажи Монтажёру..."
                        ).props("borderless autogrow").style(
                            "flex:1;background:#141722;"
                            "border:1px solid rgba(99,130,255,0.08);"
                            "border-radius:6px;color:rgba(220,225,240,0.92);"
                            "font-family:JetBrains Mono;font-size:0.78rem;"
                            "padding:7px 10px;min-height:38px;max-height:90px;"
                        )
                        refs["chat_input"].on(
                            "keydown.ctrl.enter",
                            lambda e: _send()
                        )
                        ui.button("▶", on_click=lambda: _send()).style(
                            "background:rgba(108,140,255,0.12);"
                            "border:1px solid rgba(108,140,255,0.2);"
                            "color:#6c8cff;padding:7px 14px;"
                            "border-radius:6px;height:38px;font-size:0.85rem;"
                        )

        # RIGHT — мастер
        with ui.element("div").classes("area-right glass").style(
            "display:flex;flex-direction:column;overflow:hidden;"
        ):
            # Аватар
            info, dna = _load_monteur()
            avatar_name = info.get("avatar", "MONTEUR")
            avatar_url  = get_avatar_url(
                MONTEUR_ID, MONTEUR_DEPT, avatar_name
            )

            with ui.element("div").style(
                "padding:14px 12px 10px;"
                "border-bottom:1px solid rgba(255,255,255,0.06);"
                "flex-shrink:0;text-align:center;"
            ):
                # Аватар — картинка если есть, иначе заглушка с ID
                if avatar_url:
                    ui.element("div").classes("cab-detail-avatar").style(
                        f"background-image:url('{avatar_url}');"
                        "margin:0 auto 8px;"
                    )
                else:
                    ui.html(
                        f'<div style="width:72px;height:72px;border-radius:50%;'
                        f'background:rgba(108,140,255,0.08);'
                        f'border:1px solid rgba(108,140,255,0.2);'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-family:JetBrains Mono;font-size:0.5rem;'
                        f'color:rgba(108,140,255,0.6);'
                        f'margin:0 auto 8px;">'
                        f'{MONTEUR_ID}</div>'
                    )

                label = info.get("label", "Монтажёр")
                ui.html(
                    f'<div style="font-family:JetBrains Mono;font-size:0.75rem;'
                    f'font-weight:500;color:rgba(220,225,240,0.92);">{label}</div>'
                )
                greeting = info.get("greeting", "")
                if greeting:
                    ui.html(
                        f'<div style="font-family:JetBrains Mono;font-size:0.52rem;'
                        f'color:rgba(140,150,180,0.45);margin-top:3px;'
                        f'font-style:italic;">{greeting[:60]}</div>'
                    )

                # ДНК бары
                dynamic = dna.get("dynamic", {})
                if dynamic:
                    with ui.element("div").style("margin-top:10px;"):
                        for param in ["Respect","Patience","Stress","Internal_Light"]:
                            val   = float(dynamic.get(param, 0.5))
                            pct   = round(val * 100)
                            color = BAR_COLORS.get(param, "#6c8cff")
                            lbl   = BAR_LABELS.get(param, param[:3])
                            ui.html(
                                f'<div style="display:flex;align-items:center;'
                                f'gap:5px;margin-bottom:3px;">'
                                f'<span style="font-family:JetBrains Mono;'
                                f'font-size:0.48rem;color:rgba(140,150,180,0.4);'
                                f'width:26px;">{lbl}</span>'
                                f'<div style="flex:1;height:3px;background:'
                                f'rgba(255,255,255,0.06);border-radius:2px;">'
                                f'<div style="width:{pct}%;height:100%;'
                                f'background:{color};border-radius:2px;"></div>'
                                f'</div>'
                                f'<span style="font-family:JetBrains Mono;'
                                f'font-size:0.48rem;color:rgba(140,150,180,0.35);'
                                f'width:26px;text-align:right;">{val:.2f}</span>'
                                f'</div>'
                            )

                # Кнопка — поговорить с Монтажёром
                ui.element("div").classes("cab-talk-btn").style(
                    "margin-top:10px;"
                ).on("click", lambda e: _toggle_chat()).props(
                    'inner-html="💬 поговорить"'
                )

            # Опыт мастера
            ui.html('<div class="panel-title">ОПЫТ</div>')
            refs["right_body"] = ui.element("div").style(
                "flex:1;overflow-y:auto;padding:8px 10px;"
                "scrollbar-width:thin;"
            )
            _refresh_right()

