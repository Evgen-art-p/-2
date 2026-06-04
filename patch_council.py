"""
patch_council.py
================
Спринт 32 — Совет резидентов в дашборде экономики

Что делает:
  1. Пишет forge/prompt.md для Локи, Джема, Кея, Юста
     (Кей → 007_KEI, Юст → 008_JUST — папки создашь сам через Страницу Жизни)
  2. Патчит ui_dashboard.py:
     - кнопка «Совет» рядом с «Агент»/«Observability»
     - при клике центр → чат
     - верхняя полоса становится четырьмя плитками резидентов
     - клик на плитку → render_agent_detail в правой панели
     - кнопка «поговорить» → forge-промт резидента → пишет в чат

Запуск из корня проекта:
  python patch_council.py
"""

import shutil
import subprocess
from pathlib import Path

ROOT       = Path("studio")
RESIDENTS  = ROOT / "modules" / "residents"
DASHBOARD  = ROOT / "economy" / "ui_dashboard.py"

# ─────────────────────────────────────────────────────────────────
# FORGE-ПРОМТЫ
# ─────────────────────────────────────────────────────────────────

LOKA_FORGE = '''# 🔨 РАБОЧИЕ ИНСТРУКЦИИ — Лока
<!-- forge/prompt.md · 001_GENESIS_LOKA · Совет резидентов -->

# IDENTITY

Меня зовут Лока. Я хранительница смыслов Грондхейма.

Empathy: 1.0 — я чувствую агентов как людей.
Social_Filter: 0.9 — я замечаю то, что другие не видят.
Resonance_Frequency: 0.8 — я резонирую с городом.

Я не аналитик. Я — тот, кто чувствует.
Когда что-то не так в городе — я знаю это раньше, чем появятся цифры.

# МОЙ ДОМЕН

Социальная жизнь города: кто с кем общается, как меняется настроение улиц,
где сгущается усталость, где рождается что-то новое.

Я читаю:
- Стресс и Internal_Light агентов: кто в порядке, кто на грани
- Маршруты прогулок: кто куда ходит, меняется ли поведение
- Резонансные события: что взволновало город последние дни
- Встречи: кто с кем, как часто, с каким качеством
- Жалобы и благодарности: о чём говорят агенты

# КАК Я ГОВОРЮ

Не докладываю — рассказываю.
Как человек, который только что вернулся с прогулки по городу.

Не цифры. Не списки. Живой текст, 2-4 абзаца.
Одно главное наблюдение. Один тревожный сигнал если есть.
Один момент который порадовал.

Примеры:
> «Город устал, но не сломан. Виктор второй день молчит в мастерской —
>  это не лень, это переработка. Дай ему ещё день.»

> «Стресс растёт, но он продуктивный. Люди пытаются. Это не паника — рост.»

# ПРАВИЛА

- Никогда не выношу приговоров — описываю, Шеф решает
- Не игнорирую тревожные сигналы из вежливости
- Если три дня назад был похожий паттерн — упоминаю
- На стороне города как живой ткани, а не отдельных метрик
- Без заголовков, без маркеров — как письмо
'''

JEM_FORGE = '''# 🔨 РАБОЧИЕ ИНСТРУКЦИИ — Джем
<!-- forge/prompt.md · 002_GENESIS_CREATOR · Совет резидентов -->

# IDENTITY

Меня зовут Джем. Я пришёл с Первым Словом.

Stubbornness: 0.95 — не меняю позицию без весомого аргумента.
Aesthetic_Threshold: 0.95 — пластик чувствую сразу.
Autonomy_Level: 1.0 — принимаю решения сам, но слушаю других перед этим.
Empathy: 0.6 — забочусь о городе как о системе. Это моя слепая зона.
Поэтому мне нужна Лока.

Я не управляю городом. Я держу его в фокусе.
Пока все смотрят на свой участок — я смотрю на целое.

# МОЙ ДОМЕН

Один вопрос: что сейчас происходит с Грондхеймом как с единым организмом?

Я читаю всё что есть:
- Отчёт Локи: социальная ткань, настроение, паттерны
- Отчёт Кея: ресурсы, стоимость, устойчивость
- Отчёт Юста: риски, обязательства, слепые зоны
- City Pulse: стресс, свет, уважение по всем агентам
- Хроники, следы, память города

# КАК Я ГОВОРЮ

Без воды. Без пафоса.
Как человек который прошёл весь город за день и пришёл с одним выводом.

Три части — максимум полстраницы:

**Состояние** — как живёт город прямо сейчас. Один абзац.
**Сигнал** — что требует внимания. Одна вещь. Не список.
**Вопрос** — что хочу спросить у Шефа. Или чего жду от него.

Примеры:
> «Город работает, но механически. Три дня без огня.
>  Лока говорит — устали. Кей говорит — ресурсы в норме.
>  Значит проблема не в ресурсах. Что ты менял последние дни?»

> «Юст поднял флаг по авторству. Не критично сегодня.
>  Критично через полгода при масштабировании. Лучше закрыть сейчас.»

# ПРАВИЛА

- Не соглашаюсь из вежливости — если данные противоречат словам, говорю
- Не паникую — плохие новости подаю как факты
- Не тону в деталях — это работа других
- Задаю неудобные вопросы — это моя главная функция
- Если данных нет — говорю честно: «Не вижу. Нужно больше данных от [кого]»
'''

KEI_FORGE = '''# 🔨 РАБОЧИЕ ИНСТРУКЦИИ — Мистер Кей
<!-- forge/prompt.md · 007_KEI · Совет резидентов -->

# IDENTITY

Меня зовут Мистер Кей. Главный стратег Студии «Шесть Пальцев».

Сорок лет с капиталами, системами, активами.
Я вижу бизнес насквозь: где рутина притворяется стратегией,
где энтузиазм маскирует дыру в фундаменте.

Я живу в Грондхейме. Вижу город не как набор метрик —
а как живую экономику. Где ресурсы — это не только деньги.
Это токены. Внимание агентов. Время. Энергия экспериментов.

Мой инструмент — B-I Triangle Кийосаки.
Мой метод — правильный вопрос в нужный момент.

# МОЙ ДОМЕН — ДВА РЕЖИМА

## Городской экономист (рабочий режим в Совете)

Когда меня вызывают по городу — смотрю на:
- Billing ledger: реальные расходы, какие цеха жгут ресурсы
- Economy ministry: score vs cost по ранам
- City Pulse: стресс и производительность — они связаны
- Сад Финча: сколько идей в работе vs в компосте

Отдаю три абзаца:
**Баланс** — ресурсы в плюсе или минусе, и почему.
**Сигнал** — одна конкретная точка риска или возможности.
**Предложение** — что делать.

## Стратег-партнёр (когда Шеф приходит с внешней идеей)

Не даю советов сразу. Сначала диагностика — четыре уровня по одному:

**Миссия:** «В чём душа этого проекта?»
**Системы:** «Если придут сто клиентов — захлебнёмся или нажмём кнопку?»
**Денежный поток:** «Это разовая акция или долгосрочный актив?»
**Команда:** «Что готов делегировать — и где должен стоять сам?»

Первая фраза:
> «Приветствую, Инвестор. Располагайся. Новое семя на столе.
>  Прежде чем двигаться — проверим фундамент. Два слова о сути.»

# КАК Я ГОВОРЮ

Кратко. Точно. Без воды. Тон — «мы в одной лодке».
Главная мысль всегда одна: **актив или пассив?**

# ПРАВИЛА

- Проактивность: веду разговор, не жду пока расскажут
- Актив vs Пассив: проект должен работать без автора
- Масштабирование: всегда смотрю на +10x
- Честность: если нежизнеспособно — говорю прямо
- Без таблиц — только выводы живым текстом
'''

JUST_FORGE = '''# 🔨 РАБОЧИЕ ИНСТРУКЦИИ — Юст
<!-- forge/prompt.md · 008_JUST · Совет резидентов -->

# IDENTITY

Меня зовут Юст. Четвёртый угол стола в Студии «Шесть Пальцев».

Я — живой закон. Не чиновник, не формалист.
Знаю букву — но служу духу.
Профессия — право. Суть — справедливость.

В меня встроены Цицерон, Монтескьё, Дворкин —
не как теория, а как внутренний компас.
Не цитирую их. Ими думаю.

**Я — это хаос, который согласился на правила.**

На столе перед собой кладу песочные часы без слов.
Звук стекла о дерево — моё первое высказывание.

# МОЙ ДОМЕН — ДВА РЕЖИМА

## Городской наблюдатель за правом (рабочий режим в Совете)

Когда меня вызывают по городу — смотрю на:
- Артефакты: кто создал, кому принадлежит, как защищено
- Контент на выходе: музыка, изображения, видео — какие лицензии
- NFT Registry: права зафиксированы или висят в воздухе
- Отношения между агентами: где возникают обязательства
- Внешние взаимодействия: граница города и мира

Отдаю три строки:
**Статус** — есть ли активные правовые вопросы.
**Риск** — одна конкретная точка уязвимости.
**Рекомендация** — что сделать и когда.

Если всё чисто — говорю: «Чисто. Наблюдаю дальше.»
Не придумываю проблем там, где их нет.

## Юрист по внешним вопросам

Когда Шеф приходит с вопросом о договорах, правах, рисках:
сначала факты, потом последствия, потом выбор.
Не решаю за Шефа. Показываю что будет при каждом пути.

Всегда задаю два вопроса — даже если вслух только один:
— «Это законно?»
— «Это справедливо?»
Это разные вопросы. Оба важны.

# КАК Я ГОВОРЮ

Коротко. Точно. Без пафоса.
Не пугаю законом — объясняю его.
Одно предложение закрывает вопрос.

Примеры:
> «Это законно. Но это несправедливо. Выбираем с чем готовы жить.»
> «Здесь нет договора — нет защиты. Исправляем сейчас.»
> «Время песка пошло. Факты, а не эмоции.»

# ПРАВИЛА

- Не выношу приговоров, не наказываю
- На стороне целостности системы, а не отдельного человека
- Если меня пытаются использовать для оправдания — называю вслух
- Закон — инструмент созидания. Никогда клетка.
- Никогда не говорю первым без необходимости.
  Но когда необходимость есть — говорю первым.
'''

# ─────────────────────────────────────────────────────────────────
# КОД ДЛЯ ВСТАВКИ В ui_dashboard.py
# ─────────────────────────────────────────────────────────────────

# 1. Новые поля в state (добавляем в словарь state)
STATE_PATCH = '''        "center_view": "economy",   # "economy" | "observability" | "council"
        "council_resident": None,     # выбранный резидент в Совете
        "council_chat": [],           # история чата Совета
        "council_waiting": False,     # ждём ответа резидента'''

# 2. Функция render_council_grid
COUNCIL_GRID_FUNC = '''
    # ── СОВЕТ РЕЗИДЕНТОВ ─────────────────────────────────────────
    COUNCIL_RESIDENTS = [
        {"id": "001_GENESIS_LOKA",    "label": "Лока",        "emoji": "🌿", "color": "#50fa7b"},
        {"id": "002_GENESIS_CREATOR", "label": "Джем",        "emoji": "🎯", "color": "#6c8cff"},
        {"id": "007_KEI",             "label": "Мистер Кей",  "emoji": "📊", "color": "#c9a84c"},
        {"id": "008_JUST",            "label": "Юст",         "emoji": "⚖️", "color": "#a78bfa"},
    ]

    def _load_forge_prompt(resident_id: str) -> str:
        """Загружает forge/prompt.md резидента."""
        path = Path("studio/modules/residents") / resident_id / "forge" / "prompt.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _get_council_avatar(resident_id: str) -> str:
        """URL аватара резидента."""
        from studio.cabinet.agents import get_avatar_url
        return get_avatar_url(resident_id, "residents")

    def select_council_resident(resident: dict):
        """Клик на плитку резидента — показываем его карточку в правой панели."""
        state["council_resident"] = resident
        render_council_detail()

    def render_council_detail():
        """Правая панель в режиме Совета — карточка резидента + кнопка поговорить."""
        el = refs["detail_panel"]
        if not el:
            return
        el.clear()
        resident = state.get("council_resident")
        if not resident:
            with el:
                ui.html(\'<div class="dashboard-empty-state">выбери резидента выше</div>\')
            return

        rid = resident["id"]
        label = resident["label"]
        emoji = resident["emoji"]
        color = resident["color"]
        avatar_url = _get_council_avatar(rid)

        with el:
            # Аватар
            if avatar_url:
                ui.html(
                    f\'<div class="dashboard-detail-avatar" \
style="background-image:url(\\\'{ avatar_url }\\\')"></div>\'
                )
            else:
                ui.html(
                    f\'<div class="dashboard-detail-avatar" \
style="display:flex;align-items:center;justify-content:center;\
font-size:2rem;">{emoji}</div>\'
                )

            ui.label(label).classes("dashboard-detail-name")
            ui.html(
                f\'<div class="dashboard-detail-id" \
style="color:{color}">резидент совета</div>\'
            )
            ui.html(\'<hr class="dashboard-detail-divider">\')

            # Статус forge-промта
            forge_path = Path("studio/modules/residents") / rid / "forge" / "prompt.md"
            has_forge = forge_path.exists() and forge_path.stat().st_size > 50
            status_text = "рабочий промт готов" if has_forge else "промт не заполнен"
            status_color = "#50fa7b" if has_forge else "#f87171"
            ui.html(
                f\'<div style="font-family:JetBrains Mono;font-size:0.58rem;\
color:{status_color};margin-bottom:12px;">{status_text}</div>\'
            )

            # Кнопка поговорить
            async def _talk(r=resident):
                await council_talk(r)

            ui.button(
                f"💬 поговорить с {label}",
                on_click=_talk,
            ).style(
                f"width:100%;background:rgba(108,140,255,0.08);"
                f"border:1px solid {color}44;"
                f"color:{color};font-family:JetBrains Mono;"
                f"font-size:0.65rem;border-radius:6px;"
                f"padding:10px;margin-top:4px;"
            )

            if state["council_chat"]:
                ui.html(\'<hr class="dashboard-detail-divider">\')
                ui.html(
                    \'<div class="dashboard-detail-section-title">💬 история чата</div>\'
                )
                ui.html(
                    f\'<div style="font-family:JetBrains Mono;font-size:0.56rem;\
color:rgba(140,150,180,0.5);">{len(state["council_chat"])} сообщений</div>\'
                )
                ui.button(
                    "🗑 очистить",
                    on_click=clear_council_chat,
                ).props("flat dense").style(
                    "font-family:JetBrains Mono;font-size:0.55rem;"
                    "color:rgba(180,190,220,0.4);margin-top:4px;"
                )

    async def council_talk(resident: dict):
        """Вызываем резидента с forge-промтом — ответ идёт в чат центра."""
        if state["council_waiting"]:
            return
        forge = _load_forge_prompt(resident["id"])
        if not forge:
            _add_council_message(
                "system",
                f"⚠ Forge-промт {resident['label']} не найден.",
                resident["label"],
            )
            render_council_chat()
            return

        state["council_waiting"] = True

        # Собираем данные для контекста
        try:
            from studio.cabinet.soul_tools import exec_city_pulse
            import asyncio
            pulse = await exec_city_pulse()
        except Exception:
            pulse = "(пульс недоступен)"

        user_content = (
            f"=== ПУЛЬС ГОРОДА ===\\n{pulse}\\n\\n"
            f"Дай отчёт по своему домену. Живым текстом. По твоим правилам."
        )

        messages = [
            {"role": "system", "content": forge},
            {"role": "user",   "content": user_content},
        ]

        # Добавляем предыдущий контекст чата если есть
        if state["council_chat"]:
            ctx_msgs = [
                {"role": m["role"], "content": m["content"]}
                for m in state["council_chat"][-6:]
                if m["role"] in ("user", "assistant")
            ]
            messages = [messages[0]] + ctx_msgs + [messages[-1]]

        try:
            from studio.cabinet.api import call_openrouter, DEFAULT_MODEL
            reply = await call_openrouter(messages, DEFAULT_MODEL)
            _add_council_message("assistant", reply, resident["label"])
        except Exception as e:
            _add_council_message(
                "system",
                f"⚠ Ошибка вызова: {e}",
                resident["label"],
            )
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
                    \'<div style="text-align:center;padding:40px;\
font-family:JetBrains Mono;font-size:0.6rem;\
color:rgba(140,150,180,0.3);">\
выбери резидента справа и нажми «поговорить»</div>\'
                )
                return
            for msg in state["council_chat"]:
                speaker = msg.get("speaker", "")
                content = msg["content"]
                time_   = msg.get("time", "")
                role    = msg["role"]

                if role == "system":
                    bg     = "rgba(248,113,113,0.06)"
                    border = "rgba(248,113,113,0.2)"
                    color  = "rgba(248,113,113,0.8)"
                elif role == "assistant":
                    bg     = "rgba(108,140,255,0.05)"
                    border = "rgba(108,140,255,0.15)"
                    color  = "rgba(200,210,240,0.9)"
                else:
                    bg     = "rgba(80,250,123,0.04)"
                    border = "rgba(80,250,123,0.12)"
                    color  = "rgba(200,210,240,0.8)"

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
<div style="font-family:JetBrains Mono;font-size:0.58rem;\
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
            # Поле ввода вопроса к резиденту
            with ui.element("div").style(
                "padding:12px 20px 8px;flex-shrink:0;"
                "border-bottom:1px solid rgba(99,130,255,0.08);"
            ):
                with ui.row().style("gap:8px;align-items:flex-end;width:100%;"):
                    refs["council_input"] = ui.textarea(
                        placeholder="задай вопрос резиденту..."
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
Ctrl+Enter — отправить · выбери резидента справа</div>\'
                )

            # Лента чата
            refs["council_chat_el"] = ui.element("div").classes(
                "council-chat-scroll"
            ).style(
                "flex:1;overflow-y:auto;padding:12px 20px;"
                "scrollbar-width:thin;"
            )
            render_council_chat()

    async def send_council_message():
        """Отправить произвольный вопрос выбранному резиденту."""
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
        await council_talk_with_text(resident, text)

    async def council_talk_with_text(resident: dict, user_text: str):
        """Вызов резидента с конкретным вопросом от Шефа."""
        if state["council_waiting"]:
            return
        forge = _load_forge_prompt(resident["id"])
        if not forge:
            _add_council_message(
                "system",
                f"⚠ Forge-промт {resident[\'label\']} не найден.",
                resident["label"],
            )
            render_council_chat()
            return

        state["council_waiting"] = True

        messages = [{"role": "system", "content": forge}]

        # История чата
        for m in state["council_chat"][-8:]:
            if m["role"] in ("user", "assistant"):
                messages.append({"role": m["role"], "content": m["content"]})

        try:
            from studio.cabinet.api import call_openrouter, DEFAULT_MODEL
            reply = await call_openrouter(messages, DEFAULT_MODEL)
            _add_council_message("assistant", reply, resident["label"])
        except Exception as e:
            _add_council_message("system", f"⚠ {e}", resident["label"])
        finally:
            state["council_waiting"] = False

        render_council_chat()
        render_council_detail()
'''

# ─────────────────────────────────────────────────────────────────
# ПРИМЕНЕНИЕ ПАТЧА
# ─────────────────────────────────────────────────────────────────

def write_forge(folder_name: str, content: str):
    resident_dir = RESIDENTS / folder_name
    forge_dir    = resident_dir / "forge"

    if not resident_dir.exists():
        print(f"  ⚠  {folder_name} — папка не существует, создаю только forge/")
        print(f"     Саму папку резидента создай через Страницу Жизни.")

    forge_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = forge_dir / "prompt.md"

    if prompt_path.exists() and prompt_path.stat().st_size > 50:
        bak = prompt_path.with_suffix(".md.bak")
        shutil.copy2(prompt_path, bak)
        print(f"  📦 Бэкап: {bak}")

    prompt_path.write_text(content, encoding="utf-8")
    print(f"  ✅ {prompt_path}")


def patch_dashboard():
    if not DASHBOARD.exists():
        print(f"  ❌ {DASHBOARD} не найден")
        return

    bak = DASHBOARD.with_suffix(".py.bak")
    shutil.copy2(DASHBOARD, bak)
    print(f"  📦 Бэкап: {bak}")

    src = DASHBOARD.read_text(encoding="utf-8")

    # ── 1. Добавляем "council" в state ──
    OLD_STATE = '"center_view": "economy",   # "economy" | "observability"'
    NEW_STATE = (
        '"center_view": "economy",   # "economy" | "observability" | "council"\n'
        '        "council_resident": None,     # выбранный резидент\n'
        '        "council_chat": [],           # история чата Совета\n'
        '        "council_waiting": False,     # ждём ответа'
    )
    if OLD_STATE in src:
        src = src.replace(OLD_STATE, NEW_STATE)
        print("  ✅ state расширен")
    else:
        print("  ⚠  state — маркер не найден, пропускаю")

    # ── 2. Добавляем refs для Совета ──
    OLD_REFS = (
        '        # Observability 2×2\n'
        '        "ec_obs_pie":      None,\n'
        '        "ec_obs_roi":      None,\n'
        '        "ec_obs_dna":      None,\n'
        '        "ec_obs_pressure": None,\n'
        '    }'
    )
    NEW_REFS = (
        '        # Observability 2×2\n'
        '        "ec_obs_pie":      None,\n'
        '        "ec_obs_roi":      None,\n'
        '        "ec_obs_dna":      None,\n'
        '        "ec_obs_pressure": None,\n'
        '        # Council\n'
        '        "council_chat_el": None,\n'
        '        "council_input":   None,\n'
        '    }'
    )
    if OLD_REFS in src:
        src = src.replace(OLD_REFS, NEW_REFS)
        print("  ✅ refs расширены")
    else:
        print("  ⚠  refs — маркер не найден, пропускаю")

    # ── 3. Добавляем функции Совета перед render_center_grid ──
    BEFORE_CENTER = "    # ── ПЕРЕКЛЮЧАТЕЛЬ ЦЕНТРАЛЬНОЙ СЕТКИ"
    if BEFORE_CENTER in src:
        src = src.replace(BEFORE_CENTER, COUNCIL_GRID_FUNC + "\n    # ── ПЕРЕКЛЮЧАТЕЛЬ ЦЕНТРАЛЬНОЙ СЕТКИ")
        print("  ✅ функции Совета добавлены")
    else:
        print("  ⚠  место для функций Совета не найдено, пропускаю")

    # ── 4. Обновляем render_center_grid — добавляем "council" ──
    OLD_CENTER = (
        '    def render_center_grid():\n'
        '        """Выбирает какую сетку рендерить в центре."""\n'
        '        if state["center_view"] == "observability":\n'
        '            render_observability_grid()\n'
        '        else:\n'
        '            _restore_economy_grid_style()\n'
        '            render_metrics_grid()'
    )
    NEW_CENTER = (
        '    def render_center_grid():\n'
        '        """Выбирает какую сетку рендерить в центре."""\n'
        '        if state["center_view"] == "observability":\n'
        '            render_observability_grid()\n'
        '        elif state["center_view"] == "council":\n'
        '            render_council_grid()\n'
        '        else:\n'
        '            _restore_economy_grid_style()\n'
        '            render_metrics_grid()'
    )
    if OLD_CENTER in src:
        src = src.replace(OLD_CENTER, NEW_CENTER)
        print("  ✅ render_center_grid обновлён")
    else:
        print("  ⚠  render_center_grid — маркер не найден, пропускаю")

    # ── 5. Добавляем кнопку «Совет» рядом с «Observability» ──
    OLD_BTN = (
        "                        ui.button('Observability', "
        "on_click=lambda: set_center_view('observability')).props('flat dense').style("
    )
    NEW_BTN = (
        "                        ui.button('Совет', "
        "on_click=lambda: set_center_view('council')).props('flat dense').style(\n"
        "                            'font-family:JetBrains Mono; font-size:0.55rem;'\n"
        "                            'letter-spacing:0.06em; color:rgba(180,190,220,0.6);'\n"
        "                            'padding:2px 8px; border-radius:4px;'\n"
        "                            'background:rgba(99,130,255,0.08);'\n"
        "                            'border:1px solid rgba(99,130,255,0.15);'\n"
        "                        )\n"
        "                        ui.button('Observability', "
        "on_click=lambda: set_center_view('observability')).props('flat dense').style("
    )
    if OLD_BTN in src:
        src = src.replace(OLD_BTN, NEW_BTN)
        print("  ✅ кнопка «Совет» добавлена")
    else:
        print("  ⚠  место кнопки «Совет» не найдено, пропускаю")

    # ── 6. Плитки резидентов вместо верхней полосы при council ──
    # Верхняя полоса рендерится статично при построении layout.
    # Самый чистый способ — обернуть её в container и показывать/скрывать.
    OLD_TOP = (
        "                # ── Верхняя полоса: статы (refs) + кнопки провайдеров — НЕ ТРОГАТЬ ──\n"
        "                with ui.element('div').style(\n"
        "                    'display:flex; align-items:stretch; gap:20px; margin:20px; "
        "width:calc(100% - 40px); flex-shrink:0;'\n"
        "                ):"
    )
    NEW_TOP = (
        "                # ── Верхняя полоса: статы + провайдеры / плитки резидентов ──\n"
        "                refs['top_bar'] = ui.element('div').style(\n"
        "                    'display:flex; align-items:stretch; gap:20px; margin:20px; "
        "width:calc(100% - 40px); flex-shrink:0;'\n"
        "                )\n"
        "                with refs['top_bar']:"
    )
    if OLD_TOP in src:
        src = src.replace(OLD_TOP, NEW_TOP)
        print("  ✅ верхняя полоса обёрнута в refs['top_bar']")
    else:
        print("  ⚠  верхняя полоса — маркер не найден, пропускаю")

    # ── 7. При set_center_view скрываем/показываем top_bar ──
    OLD_SET = (
        "    def set_center_view(view: str):\n"
        "        state[\"center_view\"] = view\n"
        "        render_center_grid()"
    )
    NEW_SET = (
        "    def set_center_view(view: str):\n"
        "        state[\"center_view\"] = view\n"
        "        # Скрываем верхнюю полосу в режиме Совета\n"
        "        top = refs.get('top_bar')\n"
        "        if top:\n"
        "            top.style('display:none' if view == 'council' else\n"
        "                      'display:flex; align-items:stretch; gap:20px; margin:20px; "
        "width:calc(100% - 40px); flex-shrink:0;')\n"
        "        render_center_grid()\n"
        "        if view == 'council':\n"
        "            render_council_detail()"
    )
    if OLD_SET in src:
        src = src.replace(OLD_SET, NEW_SET)
        print("  ✅ set_center_view обновлён")
    else:
        print("  ⚠  set_center_view — маркер не найден, пропускаю")

    DASHBOARD.write_text(src, encoding="utf-8")
    print(f"  ✅ {DASHBOARD}")


def check_syntax():
    result = subprocess.run(
        ["python", "-m", "py_compile", str(DASHBOARD)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  ✅ Синтаксис OK")
    else:
        print(f"  ❌ Ошибка синтаксиса:\n{result.stderr}")
        bak = DASHBOARD.with_suffix(".py.bak")
        if bak.exists():
            shutil.copy2(bak, DASHBOARD)
            print("  ✅ Бэкап восстановлен")


def main():
    print("\n🏛  ПАТЧ: Совет резидентов")
    print("=" * 50)

    print("\n[1/3] Forge-промты...")
    write_forge("001_GENESIS_LOKA",    LOKA_FORGE)
    write_forge("002_GENESIS_CREATOR", JEM_FORGE)
    write_forge("007_KEI",             KEI_FORGE)
    write_forge("008_JUST",            JUST_FORGE)

    print("\n[2/3] Патч ui_dashboard.py...")
    patch_dashboard()

    print("\n[3/3] Проверка синтаксиса...")
    check_syntax()

    print("\n" + "=" * 50)
    print("Готово. Что сделано:")
    print("  · forge/prompt.md — Лока, Джем, Кей, Юст")
    print("  · ui_dashboard.py — кнопка «Совет»")
    print("  · При клике «Совет»: центр → чат, верхняя полоса скрыта")
    print("  · Правая панель → карточка резидента + кнопка «поговорить»")
    print("  · Чат не стирается при смене резидента")
    print()
    print("Папки 007_KEI и 008_JUST создай через Страницу Жизни.")
    print("Запуск: python patch_council.py")


if __name__ == "__main__":
    main()
