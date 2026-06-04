"""
patch_council_v2.py
===================
Спринт 32 — Исправление council_talk в ui_dashboard.py

Что исправляет:
  - council_talk() теперь использует полную механику памяти резидента:
      on_agent_wake()         → душа, якоря, резонанс, sensory memory
      build_agent_context()   → конспекты прошлых разговоров с Шефом
      finalize_agent_dialog() → сохраняет конспект после разговора
      record_sensory_event()  → факт разговора в sensory память
  - Каждый резидент получает свой срез данных по домену:
      Лока  → city_traces.json (паттерны) + fallback exec_city_pulse()
      Кей   → billing_ledger + city_traces.json
      Юст   → NFT Registry + city_traces.json
      Джем  → city_state.json + traces + pulse (всё)
  - Graceful fallback: если traces пусты → exec_city_pulse()
  - Утренний режим резидента инжектируется в контекст

Запуск из корня проекта:
  python patch_council_v2.py
"""

import shutil
import subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")

# ─────────────────────────────────────────────────────────────────
# НОВЫЕ ФУНКЦИИ — заменяют блок council_talk в ui_dashboard.py
# ─────────────────────────────────────────────────────────────────

NEW_COUNCIL_FUNCTIONS = '''
    # ── СОВЕТ РЕЗИДЕНТОВ ─────────────────────────────────────────
    COUNCIL_RESIDENTS = [
        {"id": "001_GENESIS_LOKA",    "label": "Лока",       "emoji": "🌿", "color": "#50fa7b"},
        {"id": "002_GENESIS_CREATOR", "label": "Джем",       "emoji": "🎯", "color": "#6c8cff"},
        {"id": "007_KEI",             "label": "Мистер Кей", "emoji": "📊", "color": "#c9a84c"},
        {"id": "008_JUST",            "label": "Юст",        "emoji": "⚖️", "color": "#a78bfa"},
    ]

    # Домен → что читает каждый резидент
    COUNCIL_DOMAIN = {
        "001_GENESIS_LOKA":    "social",   # city_traces → социальная ткань
        "002_GENESIS_CREATOR": "all",      # всё: traces + state + pulse
        "007_KEI":             "economy",  # billing_ledger + traces
        "008_JUST":            "legal",    # NFT Registry + traces
    }

    def _load_forge_prompt(resident_id: str) -> str:
        path = Path("studio/modules/residents") / resident_id / "forge" / "prompt.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _get_council_avatar(resident_id: str) -> str:
        from studio.cabinet.agents import get_avatar_url
        return get_avatar_url(resident_id, "residents")

    def _load_city_traces() -> dict:
        """Загружает city_traces.json. Возвращает {} если нет."""
        traces_path = Path("studio/city_traces.json")
        if not traces_path.exists():
            return {}
        try:
            import json as _j
            return _j.loads(traces_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _format_traces_for_loka(traces: dict) -> str:
        """Срез traces для Локи — социальная ткань города."""
        if not traces:
            return ""
        lines = ["=== СЛЕДЫ ГОРОДА (последние 30 дней) ==="]

        # Куда ходят чаще всего
        streaks = traces.get("location_streaks", {})
        if streaks:
            lines.append("\\nМаршруты жителей:")
            for agent, locs in list(streaks.items())[:8]:
                if locs:
                    top = locs[0]
                    lines.append(
                        f"  {agent}: чаще всего → {top['location']} "
                        f"({top['visits']} визитов, стресс {top.get('avg_stress', '?')})"
                    )

        # Встречи
        meetings = traces.get("meeting_frequency", {})
        if meetings:
            lines.append("\\nРегулярные встречи:")
            for pair, data in list(meetings.items())[:5]:
                lines.append(
                    f"  {data['agent_a']} ↔ {data['agent_b']}: "
                    f"{data['meetings']} встреч, "
                    f"качество {data.get('avg_quality', '?')}"
                )

        # Бунты
        revolts = traces.get("revolt_patterns", {})
        active_revolts = {a: r for a, r in revolts.items() if r.get("revolts", 0) > 0}
        if active_revolts:
            lines.append("\\nКто бунтовал:")
            for agent, r in list(active_revolts.items())[:5]:
                lines.append(
                    f"  {agent}: {r['revolts']} бунтов, "
                    f"стресс при срыве {r.get('avg_stress_at_revolt', '?')}"
                )

        # Голоса
        themes = traces.get("voice_themes", {})
        if themes:
            lines.append("\\nЧто повторяют:")
            for agent, words in list(themes.items())[:5]:
                top_words = ", ".join(w["word"] for w in words[:4])
                lines.append(f"  {agent}: {top_words}")

        lines.append("=== КОНЕЦ СЛЕДОВ ===")
        return "\\n".join(lines)

    def _format_traces_brief(traces: dict) -> str:
        """Краткий срез traces — для Кея и Юста."""
        if not traces:
            return ""
        lines = ["=== ПАТТЕРНЫ ГОРОДА ==="]
        revolts = traces.get("revolt_patterns", {})
        active = {a: r for a, r in revolts.items() if r.get("revolts", 0) > 0}
        if active:
            names = ", ".join(list(active.keys())[:5])
            lines.append(f"Бунтовавшие агенты: {names}")
        meetings = traces.get("meeting_frequency", {})
        lines.append(f"Регулярных пар встреч: {len(meetings)}")
        lines.append("=== КОНЕЦ ПАТТЕРНОВ ===")
        return "\\n".join(lines)

    def _format_economy_context() -> str:
        """Контекст для Кея — billing_ledger."""
        lines = ["=== ЭКОНОМИКА ГОРОДА ==="]
        try:
            from studio.billing_ledger import get_economy_data
            eco = get_economy_data(7)
            total = eco.get("total", 0)
            burn  = eco.get("burn_rate", 0) * 60
            lines.append(f"Расходы за 7 дней: ${total:.4f}")
            lines.append(f"Burn rate: ${burn:.4f}/час")
            by_slot = eco.get("by_slot", {})
            if by_slot:
                top = sorted(by_slot.items(), key=lambda x: x[1], reverse=True)[:3]
                lines.append("Топ цехов по расходам:")
                for slot, cost in top:
                    lines.append(f"  {slot}: ${cost:.4f}")
            by_agent = eco.get("by_agent", {})
            if by_agent:
                top_a = sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:3]
                lines.append("Топ агентов:")
                for aid, cost in top_a:
                    lines.append(f"  {aid}: ${cost:.4f}")
        except Exception as e:
            lines.append(f"(billing_ledger недоступен: {e})")

        try:
            from studio.economy import ministry as _min
            import json as _j
            outcomes_path = Path("studio/economy/data/ministry_outcomes.jsonl")
            if outcomes_path.exists():
                recs = [
                    _j.loads(l) for l in
                    outcomes_path.read_text(encoding="utf-8").strip().split("\\n")
                    if l.strip()
                ][-10:]
                if recs:
                    avg_score = sum(r.get("score", 0) for r in recs) / len(recs)
                    lines.append(f"Средний score последних 10 ранов: {avg_score:.2f}")
        except Exception:
            pass

        try:
            garden_path = Path("studio/garden.jsonl")
            if garden_path.exists():
                import json as _j
                seeds = [
                    _j.loads(l) for l in
                    garden_path.read_text(encoding="utf-8").strip().split("\\n")
                    if l.strip()
                ]
                lines.append(f"Сад Финча: {len(seeds)} артефактов")
        except Exception:
            pass

        lines.append("=== КОНЕЦ ЭКОНОМИКИ ===")
        return "\\n".join(lines)

    def _format_legal_context() -> str:
        """Контекст для Юста — NFT Registry + артефакты."""
        lines = ["=== ПРАВОВОЙ СТАТУС ГОРОДА ==="]
        try:
            import json as _j
            nft_path = Path("studio/00_REGISTRY_NFT/catalog.json")
            if nft_path.exists():
                items = _j.loads(nft_path.read_text(encoding="utf-8"))
                if isinstance(items, dict):
                    items = items.get("items", [])
                lines.append(f"NFT Registry: {len(items)} записей")
                recent = items[-5:] if items else []
                for item in recent:
                    lines.append(
                        f"  · {item.get('title', '?')} — "
                        f"автор: {item.get('author', '?')}"
                    )
            else:
                lines.append("NFT Registry: файл не найден")
        except Exception as e:
            lines.append(f"(NFT Registry недоступен: {e})")

        try:
            import json as _j
            garden_path = Path("studio/garden.jsonl")
            if garden_path.exists():
                recs = [
                    _j.loads(l) for l in
                    garden_path.read_text(encoding="utf-8").strip().split("\\n")
                    if l.strip()
                ][-5:]
                if recs:
                    lines.append("Последние артефакты в саду:")
                    for r in recs:
                        lines.append(
                            f"  · {r.get('title', '?')} — "
                            f"посадил {r.get('planted_by', '?')}"
                        )
        except Exception:
            pass

        lines.append("=== КОНЕЦ ПРАВОВОГО СТАТУСА ===")
        return "\\n".join(lines)

    def _format_city_state_context() -> str:
        """Контекст из city_state.json — для Джема."""
        lines = ["=== СОСТОЯНИЕ ГОРОДА СЕГОДНЯ ==="]
        try:
            import json as _j
            state_path = Path("studio/city_state.json")
            if state_path.exists():
                cs = _j.loads(state_path.read_text(encoding="utf-8"))
                lines.append(f"Дата: {cs.get('date', '?')}")
                lines.append(f"Погода: {cs.get('weather', '?')}")
                lines.append(f"Тонус города: {cs.get('energy', '?')}")
                lines.append(f"Средний стресс: {cs.get('avg_stress', '?')}")
                lines.append(f"Прогулок сегодня: {cs.get('walk_count', 0)}")
                modes = cs.get("morning_modes", {})
                if modes:
                    from collections import Counter
                    mode_counts = Counter(
                        v.get("mode", "?")
                        for v in modes.values()
                        if isinstance(v, dict)
                    )
                    lines.append(
                        f"Режимы утром: "
                        + " | ".join(f"{m}={c}" for m, c in mode_counts.items())
                    )
                recent = cs.get("recent_events", [])
                if recent:
                    lines.append("Последние события:")
                    for ev in recent[-3:]:
                        lines.append(f"  · {ev}")
            else:
                lines.append("(city_state.json не найден)")
        except Exception as e:
            lines.append(f"(city_state недоступен: {e})")
        lines.append("=== КОНЕЦ СОСТОЯНИЯ ===")
        return "\\n".join(lines)

    def _get_morning_mode_context(resident_id: str, resident_name: str) -> str:
        """Утренний режим резидента из city_state."""
        try:
            import json as _j
            state_path = Path("studio/city_state.json")
            if not state_path.exists():
                return ""
            cs = _j.loads(state_path.read_text(encoding="utf-8"))
            modes = cs.get("morning_modes", {})
            # Ищем по имени резидента
            for key, mode_data in modes.items():
                if isinstance(mode_data, dict):
                    if resident_name.lower() in key.lower():
                        from studio.morning_checkout import format_morning_mode_for_prompt
                        return format_morning_mode_for_prompt(mode_data)
        except Exception:
            pass
        return ""

    def _build_domain_context(resident_id: str, traces: dict, pulse_fallback: str) -> str:
        """Собирает контекст по домену резидента."""
        domain = COUNCIL_DOMAIN.get(resident_id, "social")

        if domain == "social":
            traces_text = _format_traces_for_loka(traces)
            if traces_text:
                return traces_text
            # Fallback — старый пульс
            return f"=== ПУЛЬС ГОРОДА ===\\n{pulse_fallback}\\n=== КОНЕЦ ПУЛЬСА ==="

        elif domain == "economy":
            parts = [_format_economy_context()]
            brief = _format_traces_brief(traces)
            if brief:
                parts.append(brief)
            return "\\n\\n".join(parts)

        elif domain == "legal":
            parts = [_format_legal_context()]
            brief = _format_traces_brief(traces)
            if brief:
                parts.append(brief)
            return "\\n\\n".join(parts)

        elif domain == "all":
            # Джем видит всё
            parts = [_format_city_state_context()]
            traces_text = _format_traces_for_loka(traces)
            if traces_text:
                parts.append(traces_text)
            parts.append(_format_economy_context())
            parts.append(_format_legal_context())
            if not traces_text:
                parts.append(
                    f"=== ПУЛЬС ГОРОДА ===\\n{pulse_fallback}\\n=== КОНЕЦ ПУЛЬСА ==="
                )
            return "\\n\\n".join(parts)

        return f"=== ПУЛЬС ГОРОДА ===\\n{pulse_fallback}\\n=== КОНЕЦ ПУЛЬСА ==="

    def select_council_resident(resident: dict):
        """Клик на плитку резидента — показываем его карточку в правой панели."""
        state["council_resident"] = resident
        render_council_detail()

    def render_council_detail():
        """Правая панель в режиме Совета."""
        el = refs["detail_panel"]
        if not el:
            return
        el.clear()
        resident = state.get("council_resident")
        if not resident:
            with el:
                ui.html(\'<div class="dashboard-empty-state">выбери резидента выше</div>\')
            return

        rid    = resident["id"]
        label  = resident["label"]
        emoji  = resident["emoji"]
        color  = resident["color"]
        avatar = _get_council_avatar(rid)

        with el:
            if avatar:
                ui.html(
                    f\'<div class="dashboard-detail-avatar" \
style="background-image:url(\\\'{ avatar }\\\')"></div>\'
                )
            else:
                ui.html(
                    f\'<div class="dashboard-detail-avatar" \
style="display:flex;align-items:center;justify-content:center;\
font-size:2rem;">{emoji}</div>\'
                )
            ui.label(label).classes("dashboard-detail-name")
            ui.html(
                f\'<div class="dashboard-detail-id" style="color:{color}">\
резидент совета</div>\'
            )
            ui.html(\'<hr class="dashboard-detail-divider">\')

            forge_path = (
                Path("studio/modules/residents") / rid / "forge" / "prompt.md"
            )
            has_forge = forge_path.exists() and forge_path.stat().st_size > 50
            status_color = "#50fa7b" if has_forge else "#f87171"
            status_text  = "рабочий промт готов" if has_forge else "промт не заполнен"
            ui.html(
                f\'<div style="font-family:JetBrains Mono;font-size:0.58rem;\
color:{status_color};margin-bottom:12px;">{status_text}</div>\'
            )

            # Память резидента
            try:
                from studio.cabinet.archive import load_agent_memory
                memories = load_agent_memory(rid, "residents")
                if memories:
                    ui.html(
                        f\'<div style="font-family:JetBrains Mono;font-size:0.55rem;\
color:rgba(140,150,180,0.6);margin-bottom:8px;">\
🧠 помнит {len(memories)} разговоров с тобой</div>\'
                    )
            except Exception:
                pass

            async def _talk(r=resident):
                await council_talk(r)

            ui.button(
                f"💬 поговорить с {label}",
                on_click=_talk,
            ).style(
                f"width:100%;background:rgba(108,140,255,0.08);"
                f"border:1px solid {color}44;color:{color};"
                f"font-family:JetBrains Mono;font-size:0.65rem;"
                f"border-radius:6px;padding:10px;margin-top:4px;"
            )

            if state["council_chat"]:
                ui.html(\'<hr class="dashboard-detail-divider">\')
                ui.html(
                    \'<div class="dashboard-detail-section-title">💬 история</div>\'
                )
                ui.html(
                    f\'<div style="font-family:JetBrains Mono;font-size:0.56rem;\
color:rgba(140,150,180,0.5);">\
{len(state["council_chat"])} сообщений</div>\'
                )
                ui.button(
                    "🗑 очистить",
                    on_click=clear_council_chat,
                ).props("flat dense").style(
                    "font-family:JetBrains Mono;font-size:0.55rem;"
                    "color:rgba(180,190,220,0.4);margin-top:4px;"
                )

    async def council_talk(resident: dict):
        """
        Вызываем резидента с forge-промтом.
        Полная механика: душа + память + домен + запись после.
        """
        if state["council_waiting"]:
            return

        rid   = resident["id"]
        label = resident["label"]

        forge = _load_forge_prompt(rid)
        if not forge:
            _add_council_message(
                "system",
                f"⚠ Forge-промт {label} не найден. Создай папку через Страницу Жизни.",
                label,
            )
            render_council_chat()
            return

        state["council_waiting"] = True

        # ── 1. Душа резидента (якоря, резонанс, sensory memory) ──
        soul_ctx = ""
        try:
            from studio.grondheim_memory import on_agent_wake
            soul_ctx = on_agent_wake(rid, "residents") or ""
            if soul_ctx:
                print(f"[COUNCIL] 🧬 Душа {rid}: {len(soul_ctx)} симв.")
        except Exception as e:
            print(f"[COUNCIL] ⚠ on_agent_wake: {e}")

        # ── 2. Память разговоров с Шефом ─────────────────────────
        memory_ctx = ""
        try:
            from studio.cabinet.archive import build_agent_context
            memory_ctx = build_agent_context(rid, "residents", is_resident=True)
            if memory_ctx:
                print(f"[COUNCIL] 🧠 Память {rid}: {len(memory_ctx)} симв.")
        except Exception as e:
            print(f"[COUNCIL] ⚠ build_agent_context: {e}")

        # ── 3. Утренний режим ─────────────────────────────────────
        morning_ctx = _get_morning_mode_context(rid, label)

        # ── 4. Данные по домену ───────────────────────────────────
        traces = _load_city_traces()

        pulse_fallback = ""
        try:
            from studio.cabinet.soul_tools import exec_city_pulse
            pulse_fallback = await exec_city_pulse()
        except Exception:
            pulse_fallback = "(пульс недоступен)"

        domain_ctx = _build_domain_context(rid, traces, pulse_fallback)

        # ── 5. Собираем system prompt ─────────────────────────────
        sys_parts = [forge]
        if morning_ctx:
            sys_parts.append(morning_ctx)
        if soul_ctx:
            sys_parts.append(soul_ctx)
        if memory_ctx:
            sys_parts.append(memory_ctx)
        system_prompt = "\\n\\n".join(sys_parts)

        # ── 6. Сообщение пользователя ────────────────────────────
        user_content = (
            f"{domain_ctx}\\n\\n"
            f"Дай отчёт по своему домену. "
            f"Живым текстом. По своим правилам. "
            f"Помни наши прошлые разговоры если они есть."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # История чата — контекст разговора
        for m in state["council_chat"][-8:]:
            if m["role"] in ("user", "assistant"):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_content})

        try:
            from studio.cabinet.api import call_openrouter, DEFAULT_MODEL
            reply = await call_openrouter(messages, DEFAULT_MODEL)
            _add_council_message("assistant", reply, label)

            # ── 7. Записываем факт разговора в sensory память ──
            try:
                from studio.grondheim_memory import record_sensory_event, sync_to_dna
                record_sensory_event(
                    agent_id=rid,
                    content=f"Отчёт Шефу в Совете резидентов: {reply[:150]}",
                    event_type="work",
                    source="council",
                    emotional_weight=0.5,
                    dept="residents",
                )
                sync_to_dna(rid, "cabinet_chat", intensity=0.8, dept="residents")
                print(f"[COUNCIL] 🧠 {rid}: sensory + DNA обновлены")
            except Exception as e:
                print(f"[COUNCIL] ⚠ record_sensory_event: {e}")

            # ── 8. Финализируем диалог → конспект в memory ───────
            if len(state["council_chat"]) >= 2:
                try:
                    from studio.cabinet.api import call_openrouter as _cor
                    from studio.cabinet.archive import finalize_agent_dialog
                    chat_text = "\\n".join([
                        f"{'ШЕФ' if m['role'] == 'user' else label}: "
                        f"{m['content'][:300]}"
                        for m in state["council_chat"][-10:]
                    ])
                    summary_msgs = [
                        {"role": "system", "content": (
                            f"Ты — архивариус {label}. "
                            f"Сожми диалог в конспект (3-5 предложений). "
                            f"Что обсуждали с Шефом, выводы, решения. "
                            f"От третьего лица."
                        )},
                        {"role": "user", "content": f"Сожми:\\n{chat_text}"},
                    ]
                    summary = await _cor(summary_msgs, DEFAULT_MODEL)
                    council_history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in state["council_chat"]
                        if m["role"] in ("user", "assistant")
                    ]
                    finalize_agent_dialog(
                        agent_id=rid,
                        chat_history=council_history,
                        summary=summary,
                        model=DEFAULT_MODEL,
                        dept="residents",
                        is_resident=True,
                    )
                    print(f"[COUNCIL] 💾 {rid}: конспект сохранён")
                except Exception as e:
                    print(f"[COUNCIL] ⚠ finalize_agent_dialog: {e}")

        except Exception as e:
            _add_council_message("system", f"⚠ Ошибка вызова: {e}", label)
        finally:
            state["council_waiting"] = False

        render_council_chat()
        render_council_detail()

    def _add_council_message(role: str, content: str, speaker: str = ""):
        from datetime import datetime as _dt
        state["council_chat"].append({
            "role":    role,
            "content": content,
            "speaker": speaker,
            "time":    _dt.now().strftime("%H:%M"),
        })

    def clear_council_chat():
        state["council_chat"].clear()
        render_council_chat()
        render_council_detail()

    def render_council_chat():
        """Рендерит чат Совета в центральной области."""
        el = refs.get("council_chat_el")
        if not el:
            return
        el.clear()
        with el:
            if not state["council_chat"]:
                ui.html(
                    \'<div style="text-align:center;padding:40px 20px;\
font-family:JetBrains Mono;font-size:0.6rem;\
color:rgba(140,150,180,0.3);">\
выбери резидента справа<br>\
<span style="font-size:0.52rem;color:rgba(140,150,180,0.2);">\
он прочитает свои следы и расскажет о городе</span></div>\'
                )
                return

            for msg in state["council_chat"]:
                speaker = msg.get("speaker", "")
                content = msg["content"]
                time_   = msg.get("time", "")
                role    = msg["role"]

                if role == "system":
                    bg, border, color = (
                        "rgba(248,113,113,0.06)",
                        "rgba(248,113,113,0.2)",
                        "rgba(248,113,113,0.8)",
                    )
                elif role == "assistant":
                    bg, border, color = (
                        "rgba(108,140,255,0.05)",
                        "rgba(108,140,255,0.15)",
                        "rgba(200,210,240,0.9)",
                    )
                else:
                    bg, border, color = (
                        "rgba(80,250,123,0.04)",
                        "rgba(80,250,123,0.12)",
                        "rgba(200,210,240,0.8)",
                    )

                escaped = (
                    content
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                ui.html(
                    f\'<div style="margin:8px 0;padding:12px 16px;\
background:{bg};border:1px solid {border};\
border-radius:8px;">\
<div style="font-family:JetBrains Mono;font-size:0.55rem;\
color:rgba(140,150,180,0.5);margin-bottom:6px;">\
{speaker or role} · {time_}</div>\
<div style="font-family:JetBrains Mono;font-size:0.75rem;\
color:{color};line-height:1.55;white-space:pre-wrap;">\
{escaped}</div></div>\'
                )
        ui.run_javascript(
            \'const el=document.querySelector(".council-chat-scroll");\
if(el) el.scrollTop=el.scrollHeight;\'
        )

    def render_council_grid():
        """Центральная область в режиме Совета."""
        el = refs["metrics_grid"]
        if not el:
            return
        el.clear()
        el.style(
            "display:flex;flex-direction:column;"
            "gap:0;margin:0;flex:1;min-height:0;"
        )
        with el:
            with ui.element("div").style(
                "padding:12px 20px 8px;flex-shrink:0;"
                "border-bottom:1px solid rgba(99,130,255,0.08);"
            ):
                with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                    refs["council_input"] = ui.textarea(
                        placeholder="задай вопрос выбранному резиденту..."
                    ).props("borderless autogrow").style(
                        "flex:1;background:#141722;"
                        "border:1px solid rgba(99,130,255,0.08);"
                        "border-radius:6px;color:rgba(220,225,240,0.92);"
                        "font-family:JetBrains Mono;font-size:0.8rem;"
                        "padding:8px 12px;min-height:44px;max-height:100px;"
                    )
                    refs["council_input"].on(
                        "keydown.ctrl.enter",
                        lambda e: send_council_message()
                    )
                    ui.button(
                        "▶ спросить",
                        on_click=send_council_message,
                    ).style(
                        "background:rgba(108,140,255,0.12);"
                        "border:1px solid rgba(108,140,255,0.2);"
                        "color:#6c8cff;font-family:JetBrains Mono;"
                        "font-size:0.65rem;padding:8px 16px;"
                        "border-radius:6px;height:36px;"
                    )
                ui.html(
                    \'<div style="font-family:JetBrains Mono;font-size:0.5rem;\
color:rgba(140,150,180,0.3);margin-top:4px;">\
Ctrl+Enter · выбери резидента справа</div>\'
                )

            refs["council_chat_el"] = ui.element("div").classes(
                "council-chat-scroll"
            ).style(
                "flex:1;overflow-y:auto;padding:12px 20px;"
                "scrollbar-width:thin;"
            )
            render_council_chat()

    async def send_council_message():
        """Произвольный вопрос к выбранному резиденту."""
        inp = refs.get("council_input")
        if not inp:
            return
        text = (inp.value or "").strip()
        if not text or state["council_waiting"]:
            return
        resident = state.get("council_resident")
        if not resident:
            return

        inp.set_value("")
        _add_council_message("user", text, "Шеф")
        render_council_chat()
        await _council_talk_with_text(resident, text)

    async def _council_talk_with_text(resident: dict, user_text: str):
        """Вызов резидента с конкретным вопросом — та же полная механика."""
        if state["council_waiting"]:
            return

        rid   = resident["id"]
        label = resident["label"]
        forge = _load_forge_prompt(rid)
        if not forge:
            _add_council_message(
                "system",
                f"⚠ Forge-промт {label} не найден.",
                label,
            )
            render_council_chat()
            return

        state["council_waiting"] = True

        # Душа + память
        soul_ctx = ""
        try:
            from studio.grondheim_memory import on_agent_wake
            soul_ctx = on_agent_wake(rid, "residents") or ""
        except Exception:
            pass

        memory_ctx = ""
        try:
            from studio.cabinet.archive import build_agent_context
            memory_ctx = build_agent_context(rid, "residents", is_resident=True)
        except Exception:
            pass

        morning_ctx = _get_morning_mode_context(rid, label)

        sys_parts = [forge]
        if morning_ctx:
            sys_parts.append(morning_ctx)
        if soul_ctx:
            sys_parts.append(soul_ctx)
        if memory_ctx:
            sys_parts.append(memory_ctx)
        system_prompt = "\\n\\n".join(sys_parts)

        messages = [{"role": "system", "content": system_prompt}]
        for m in state["council_chat"][-10:]:
            if m["role"] in ("user", "assistant"):
                messages.append({"role": m["role"], "content": m["content"]})

        try:
            from studio.cabinet.api import call_openrouter, DEFAULT_MODEL
            reply = await call_openrouter(messages, DEFAULT_MODEL)
            _add_council_message("assistant", reply, label)

            try:
                from studio.grondheim_memory import record_sensory_event, sync_to_dna
                record_sensory_event(
                    agent_id=rid,
                    content=f"Шеф спросил: {user_text[:100]} / Ответил: {reply[:100]}",
                    event_type="social",
                    source="council",
                    emotional_weight=0.6,
                    dept="residents",
                )
                sync_to_dna(rid, "cabinet_chat", intensity=1.0, dept="residents")
            except Exception:
                pass

        except Exception as e:
            _add_council_message("system", f"⚠ {e}", label)
        finally:
            state["council_waiting"] = False

        render_council_chat()
        render_council_detail()
'''

# ─────────────────────────────────────────────────────────────────
# ПАТЧ
# ─────────────────────────────────────────────────────────────────

OLD_MARKER = "    # ── ПЕРЕКЛЮЧАТЕЛЬ ЦЕНТРАЛЬНОЙ СЕТКИ"


def patch():
    if not DASHBOARD.exists():
        print(f"❌ {DASHBOARD} не найден")
        return False

    src = DASHBOARD.read_text(encoding="utf-8")

    # Удаляем старый блок Совета если уже был вставлен patch_council v1
    # Ищем от начала нового блока до маркера переключателя
    old_block_start = "\n    # ── СОВЕТ РЕЗИДЕНТОВ"
    if old_block_start in src:
        idx_start = src.index(old_block_start)
        idx_end   = src.index(OLD_MARKER)
        src = src[:idx_start] + "\n" + src[idx_end:]
        print("  🗑  Старый блок Совета удалён")

    if OLD_MARKER not in src:
        print(f"  ❌ Маркер не найден: {OLD_MARKER!r}")
        return False

    src = src.replace(
        OLD_MARKER,
        NEW_COUNCIL_FUNCTIONS + "\n" + OLD_MARKER
    )
    print("  ✅ Новый блок Совета вставлен")

    # Добавляем council в render_center_grid если ещё нет
    OLD_CENTER = (
        '        if state["center_view"] == "observability":\n'
        '            render_observability_grid()\n'
        '        else:'
    )
    NEW_CENTER = (
        '        if state["center_view"] == "observability":\n'
        '            render_observability_grid()\n'
        '        elif state["center_view"] == "council":\n'
        '            render_council_grid()\n'
        '        else:'
    )
    if OLD_CENTER in src and "council" not in src.split(OLD_CENTER)[0].split("render_center_grid")[-1]:
        src = src.replace(OLD_CENTER, NEW_CENTER)
        print("  ✅ render_center_grid обновлён")

    # Добавляем state если нет
    if '"council_chat": []' not in src:
        OLD_STATE = '"center_view": "economy",   # "economy" | "observability"'
        NEW_STATE = (
            '"center_view": "economy",   # "economy" | "observability" | "council"\n'
            '        "council_resident": None,\n'
            '        "council_chat": [],\n'
            '        "council_waiting": False,'
        )
        if OLD_STATE in src:
            src = src.replace(OLD_STATE, NEW_STATE)
            print("  ✅ state расширен")

    # Добавляем refs если нет
    if '"council_chat_el"' not in src:
        OLD_REFS = (
            '        "ec_obs_pressure": None,\n'
            '    }'
        )
        NEW_REFS = (
            '        "ec_obs_pressure": None,\n'
            '        "council_chat_el": None,\n'
            '        "council_input":   None,\n'
            '    }'
        )
        if OLD_REFS in src:
            src = src.replace(OLD_REFS, NEW_REFS)
            print("  ✅ refs расширены")

    # Кнопка Совет если нет
    if "set_center_view('council')" not in src:
        OLD_BTN = (
            "ui.button('Observability', "
            "on_click=lambda: set_center_view('observability'))"
        )
        NEW_BTN = (
            "ui.button('Совет', on_click=lambda: set_center_view('council')"
            ").props('flat dense').style(\n"
            "                            'font-family:JetBrains Mono;font-size:0.55rem;'\n"
            "                            'letter-spacing:0.06em;color:rgba(180,190,220,0.6);'\n"
            "                            'padding:2px 8px;border-radius:4px;'\n"
            "                            'background:rgba(99,130,255,0.08);'\n"
            "                            'border:1px solid rgba(99,130,255,0.15);'\n"
            "                        )\n"
            "                        ui.button('Observability', "
            "on_click=lambda: set_center_view('observability'))"
        )
        if OLD_BTN in src:
            src = src.replace(OLD_BTN, NEW_BTN)
            print("  ✅ кнопка «Совет» добавлена")

    # set_center_view — скрываем top_bar
    if "top_bar" not in src:
        OLD_SET = (
            "    def set_center_view(view: str):\n"
            "        state[\"center_view\"] = view\n"
            "        render_center_grid()"
        )
        NEW_SET = (
            "    def set_center_view(view: str):\n"
            "        state[\"center_view\"] = view\n"
            "        top = refs.get('top_bar')\n"
            "        if top:\n"
            "            top.style(\n"
            "                'display:none' if view == 'council' else\n"
            "                'display:flex;align-items:stretch;gap:20px;margin:20px;'\n"
            "                'width:calc(100% - 40px);flex-shrink:0;'\n"
            "            )\n"
            "        render_center_grid()\n"
            "        if view == 'council':\n"
            "            render_council_detail()"
        )
        if OLD_SET in src:
            src = src.replace(OLD_SET, NEW_SET)
            print("  ✅ set_center_view обновлён")

    # Верхняя полоса → refs['top_bar']
    if "refs['top_bar']" not in src:
        OLD_TOP = (
            "                # ── Верхняя полоса: статы (refs) + кнопки провайдеров — НЕ ТРОГАТЬ ──\n"
            "                with ui.element('div').style(\n"
            "                    'display:flex; align-items:stretch; gap:20px; margin:20px; "
            "width:calc(100% - 40px); flex-shrink:0;'\n"
            "                ):"
        )
        NEW_TOP = (
            "                # ── Верхняя полоса: статы + провайдеры ──\n"
            "                refs['top_bar'] = ui.element('div').style(\n"
            "                    'display:flex; align-items:stretch; gap:20px; margin:20px; "
            "width:calc(100% - 40px); flex-shrink:0;'\n"
            "                )\n"
            "                with refs['top_bar']:"
        )
        if OLD_TOP in src:
            src = src.replace(OLD_TOP, NEW_TOP)
            print("  ✅ top_bar обёрнут в ref")

    DASHBOARD.write_text(src, encoding="utf-8")
    return True


def main():
    print("\n🏛  ПАТЧ v2: Совет резидентов с полной механикой памяти")
    print("=" * 56)

    bak = DASHBOARD.with_suffix(".py.bak2")
    shutil.copy2(DASHBOARD, bak)
    print(f"📦 Бэкап: {bak}")

    print("\n[1/2] Патч ui_dashboard.py...")
    ok = patch()
    if not ok:
        print("❌ Патч не применён")
        return

    print("\n[2/2] Проверка синтаксиса...")
    result = subprocess.run(
        ["python", "-m", "py_compile", str(DASHBOARD)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  ✅ Синтаксис OK")
    else:
        print(f"  ❌ Ошибка:\n{result.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("  ✅ Бэкап восстановлен")
        return

    print("\n" + "=" * 56)
    print("Готово. Что изменилось в council_talk:")
    print()
    print("  on_agent_wake()         → душа, якоря, sensory память")
    print("  build_agent_context()   → конспекты прошлых разговоров")
    print("  _get_morning_mode()     → знает свой режим дня")
    print("  _build_domain_context() → свой срез данных по домену:")
    print("    Лока  → city_traces.json (паттерны) / fallback pulse")
    print("    Кей   → billing_ledger + traces")
    print("    Юст   → NFT Registry + traces")
    print("    Джем  → city_state + traces + economy + legal")
    print("  record_sensory_event()  → факт разговора в память")
    print("  finalize_agent_dialog() → конспект после разговора")
    print()
    print("Запуск: python patch_council_v2.py")
    print("(сначала запусти patch_council.py если ещё не запускал)")


if __name__ == "__main__":
    main()
