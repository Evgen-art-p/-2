# studio/workshop/cabinet_tools.py — Tool Use: схема + исполнители
# Старые инструменты + НОВЫЕ для управления агентами

import json
from pathlib import Path

from studio.workshop.clients import (
    get_clients_list, load_client_info,
    create_client as _ws_create_client, get_client_runs,
)
from studio.workshop.assets import _load_asset_catalog
from studio.cabinet.api import exec_web_search, exec_fetch_url

# ══ Грондхейм: soul tools ══
try:
    from studio.cabinet.soul_tools import SOUL_TOOLS_SCHEMA, dispatch_soul_tool
    _SOUL_TOOLS_ENABLED = True
except ImportError:
    _SOUL_TOOLS_ENABLED = False
    async def dispatch_soul_tool(fn, args): return None
    SOUL_TOOLS_SCHEMA = []

# ══ Библиотека: library tools ══
try:
    from studio.cabinet.library_tools import LIBRARY_TOOLS_SCHEMA, dispatch_library_tool
    _LIBRARY_TOOLS_ENABLED = True
except ImportError:
    _LIBRARY_TOOLS_ENABLED = False
    async def dispatch_library_tool(fn, args): return None
    LIBRARY_TOOLS_SCHEMA = []


# ═══════════════════════════════════════════════════
#  TOOL SCHEMA (OpenRouter function calling)
# ═══════════════════════════════════════════════════

TOOLS_SCHEMA = [
    # ── Web ──
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Поиск информации в интернете.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Поисковый запрос"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Загрузить и прочитать веб-страницу по URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL страницы"}},
                "required": ["url"]
            }
        }
    },
    # ── Studio navigation ──
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Перейти на страницу студии: workshop, reception, cabinet, registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": ["workshop", "reception", "cabinet", "registry"],
                        "description": "Страница студии"
                    }
                },
                "required": ["page"]
            }
        }
    },
    # ── Clients ──
    {
        "type": "function",
        "function": {
            "name": "list_clients",
            "description": "Список всех клиентов студии с инфо и количеством запусков.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_client",
            "description": "Создать нового клиента студии.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Название клиента/бренда"},
                    "niche": {"type": "string", "description": "Ниша/индустрия"},
                    "description": {"type": "string", "description": "Краткое описание"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_client_info",
            "description": "Подробная информация о клиенте.",
            "parameters": {
                "type": "object",
                "properties": {"client_slug": {"type": "string", "description": "Slug клиента"}},
                "required": ["client_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_assets",
            "description": "Каталог ассетов студии — персонажи, локации, реквизит.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "character", "location", "prop"],
                        "description": "Фильтр по категории"
                    }
                }
            }
        }
    },
    # ═══ NEW: Agent Management ═══
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": "Показать всех агентов текущего цеха с их состоянием ДНК (Respect, Patience, Stress, Light), streak, звёзды.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dept": {
                        "type": "string",
                        "description": "Цех (turbo, video_long, video_shorts, social_mix, web_story). По умолчанию — текущий."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_state",
            "description": "Полное состояние агента: ДНК (статика + динамика), якоря, streak, звёзды, последние оценки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "ID агента (A01, T1, JEM и т.д.)"}
                },
                "required": ["agent_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_agent_dynamic",
            "description": "Изменить динамические параметры агента (Respect, Patience, Stress, Internal_Light). Значения 0.0-1.0.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "ID агента"},
                    "Respect": {"type": "number", "description": "Уважение (0.0-1.0)"},
                    "Patience": {"type": "number", "description": "Терпение (0.0-1.0)"},
                    "Stress": {"type": "number", "description": "Стресс (0.0-1.0)"},
                    "Internal_Light": {"type": "number", "description": "Внутренний свет (0.0-1.0)"}
                },
                "required": ["agent_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_stressed_agents",
            "description": "Найти агентов в критическом состоянии: высокий стресс, низкий Respect, исчерпанное Patience.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # ═══ City Walker ═══
    {
        "type": "function",
        "function": {
            "name": "city_walk",
            "description": "Отправить агентов Грондхейма на прогулку по городу. Каждый агент сам решает куда пойти исходя из своего состояния, характера и погоды города. Прогулка снижает стресс и пополняет оперативную память.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список ID агентов для прогулки. Если не указан — гуляют все у кого есть dna.json."
                    },
                    "event": {
                        "type": "string",
                        "description": "Событие которое добавить в историю города (например 'завершён TURBO ран' или 'Артур выдал критику')."
                    }
                }
            }
        }
    },
]

# Добавляем soul tools (Грондхейм)
if _SOUL_TOOLS_ENABLED:
    TOOLS_SCHEMA.extend(SOUL_TOOLS_SCHEMA)

# Добавляем library tools (Библиотека)
if _LIBRARY_TOOLS_ENABLED:
    TOOLS_SCHEMA.extend(LIBRARY_TOOLS_SCHEMA)


# ═══════════════════════════════════════════════════
#  SIDE-EFFECTS
# ═══════════════════════════════════════════════════

_pending_nav_route: str | None = None


def get_pending_nav() -> str | None:
    """Получить и сбросить pending navigation route."""
    global _pending_nav_route
    route = _pending_nav_route
    _pending_nav_route = None
    return route


# ═══════════════════════════════════════════════════
#  TOOL EXECUTORS
# ═══════════════════════════════════════════════════

async def execute_tool(fn: str, args: dict) -> str:
    """Центральный диспетчер инструментов."""
    # ══ Library tools (Библиотека) ══
    if _LIBRARY_TOOLS_ENABLED:
        result = await dispatch_library_tool(fn, args)
        if result is not None:
            return result
    # ══ Soul tools (Грондхейм) ══
    if _SOUL_TOOLS_ENABLED:
        result = await dispatch_soul_tool(fn, args)
        if result is not None:
            return result
    # ══ Основные инструменты ══
    executors = {
        "web_search": lambda a: exec_web_search(a.get("query", "")),
        "fetch_url": lambda a: exec_fetch_url(a.get("url", "")),
        "navigate": lambda a: exec_navigate(a.get("page", "")),
        "list_clients": lambda a: exec_list_clients(),
        "create_client": lambda a: exec_create_client(a.get("name", ""), a.get("niche", ""), a.get("description", "")),
        "get_client_info": lambda a: exec_get_client_info(a.get("client_slug", "")),
        "view_assets": lambda a: exec_view_assets(a.get("category", "all")),
        # Agent tools
        "list_agents": lambda a: exec_list_agents(a.get("dept", "")),
        "get_agent_state": lambda a: exec_get_agent_state(a.get("agent_id", "")),
        "update_agent_dynamic": lambda a: exec_update_agent_dynamic(a),
        "find_stressed_agents": lambda a: exec_find_stressed_agents(),
        # City Walker
        "city_walk": lambda a: exec_city_walk(a.get("agent_ids"), a.get("event", "")),
    }
    executor = executors.get(fn)
    if not executor:
        return f"Неизвестный инструмент: {fn}"
    return await executor(args)


# ── Studio navigation ────────────────────────────

async def exec_navigate(page: str) -> str:
    global _pending_nav_route
    routes = {"workshop": "/workshop", "reception": "/", "cabinet": "/cabinet", "registry": "/registry"}
    route = routes.get(page)
    if not route:
        return f"Неизвестная страница: {page}. Доступны: {', '.join(routes.keys())}"
    _pending_nav_route = route
    return f"Навигация на {page} запланирована. Сообщи пользователю что переходишь."


# ── Clients ──────────────────────────────────────

async def exec_list_clients() -> str:
    clients = get_clients_list()
    if not clients:
        return "Клиентов пока нет. Предложи создать нового."
    lines = [f"Всего клиентов: {len(clients)}\n"]
    for slug in clients:
        info = load_client_info(slug)
        runs = get_client_runs(slug)
        name = info.get("name", slug)
        niche = info.get("niche", "—")
        desc = info.get("description", "")[:80]
        lines.append(f"• {slug} — {name} | ниша: {niche} | запусков: {len(runs)}")
        if desc:
            lines.append(f"  {desc}")
    return "\n".join(lines)


async def exec_create_client(name: str, niche: str = "", description: str = "") -> str:
    try:
        slug = _ws_create_client(name, niche=niche, description=description)
        return f"✅ Клиент создан!\nSlug: {slug}\nИмя: {name}\nНиша: {niche or '—'}\nОписание: {description or '—'}"
    except Exception as e:
        return f"❌ Ошибка: {e}"


async def exec_get_client_info(client_slug: str) -> str:
    info = load_client_info(client_slug)
    runs = get_client_runs(client_slug)
    lines = [
        f"Клиент: {info.get('name', client_slug)}",
        f"Slug: {client_slug}",
        f"Ниша: {info.get('niche', '—')}",
        f"Описание: {info.get('description', '—')}",
        f"Создан: {info.get('created', '—')}",
        f"\nЗапусков: {len(runs)}",
    ]
    if runs:
        lines.append("\nПоследние запуски:")
        for run in runs[:5]:
            lines.append(f"  • {run['name']} ({len(run['files'])} файлов)")
    return "\n".join(lines)


async def exec_view_assets(category: str = "all") -> str:
    catalog_text = _load_asset_catalog(force_reload=True)
    if not catalog_text:
        return "Каталог ассетов пуст."
    if category == "all":
        return catalog_text
    section_map = {"character": "ПЕРСОНАЖИ", "location": "ЛОКАЦИИ", "prop": "РЕКВИЗИТ"}
    target = section_map.get(category, "")
    if not target:
        return catalog_text
    lines = catalog_text.split("\n")
    result = []
    in_section = False
    for line in lines:
        if f"--- {target} ---" in line:
            in_section = True
            result.append(line)
        elif line.startswith("---") and in_section:
            break
        elif in_section:
            result.append(line)
    return "\n".join(result) if result else f"Ассетов '{category}' не найдено."


# ═══════════════════════════════════════════════════
#  NEW: AGENT MANAGEMENT TOOLS
# ═══════════════════════════════════════════════════

async def exec_list_agents(dept: str = "") -> str:
    """Список агентов цеха с их текущим состоянием."""
    from studio.modules_registry import MODULES_DIR, CURRENT_DEPT
    from studio.cabinet.agents import _get_agent_info, _get_agent_dna

    target_dept = dept or CURRENT_DEPT
    dept_path = MODULES_DIR / target_dept
    if not dept_path.exists():
        return f"Цех '{target_dept}' не найден."

    agents = []
    for d in sorted(dept_path.iterdir()):
        if not d.is_dir():
            continue
        wid = d.name
        info = _get_agent_info(wid, target_dept)
        dna = _get_agent_dna(wid, target_dept)
        dynamic = dna.get("dynamic", {})

        respect = float(dynamic.get("Respect", 1.0))
        patience = float(dynamic.get("Patience", 1.0))
        stress = float(dynamic.get("Stress", 0.0))
        light = float(dynamic.get("Internal_Light", 0.8))
        streak = int(dynamic.get("streak", 0))
        stars = int(dynamic.get("stars", 0))

        # Determine status
        status = "дома"
        if stress > 0.8:
            status = "⚠️ СТРЕСС"
        elif respect < 0.2:
            status = "⚠️ ВРАЖДЕБНОСТЬ"
        elif patience == 0.0:
            status = "🔇 ТИШИНА"

        stars_str = f"{'⭐' * min(stars, 5)}" if stars else ""
        streak_str = ""
        if streak >= 3:
            streak_str = f"🔥 серия {streak}"
        elif streak <= -3:
            streak_str = f"💀 серия {streak}"

        agents.append(
            f"• {wid} {info.get('label', wid)} | {status}\n"
            f"  RSP={respect:.1f} PAT={patience:.1f} STR={stress:.1f} LGT={light:.1f}"
            f"{f' | {stars_str}' if stars_str else ''}"
            f"{f' | {streak_str}' if streak_str else ''}"
        )

    if not agents:
        return f"В цехе '{target_dept}' нет агентов."

    return f"Цех: {target_dept} | Агентов: {len(agents)}\n\n" + "\n".join(agents)


async def exec_get_agent_state(agent_id: str) -> str:
    """Полное состояние конкретного агента."""
    from studio.cabinet.agents import _get_agent_info, _get_agent_dna

    info = _get_agent_info(agent_id)  # auto-searches all depts
    dna = _get_agent_dna(agent_id)

    if not dna:
        return f"Агент {agent_id}: ДНК не найдена (файл dna.json отсутствует).\nLabel: {info.get('label', agent_id)}"

    static = dna.get("static", {})
    dynamic = dna.get("dynamic", {})
    resonance = dna.get("resonance", {})

    lines = [f"═══ {info.get('label', agent_id)} ({agent_id}) ═══"]

    if static:
        lines.append("\n📊 Статическая ДНК:")
        for k, v in static.items():
            lines.append(f"  {k}: {v}")

    if dynamic:
        lines.append("\n📈 Динамика:")
        for k, v in dynamic.items():
            lines.append(f"  {k}: {v}")

    if resonance:
        lines.append("\n🔮 Резонанс:")
        anchors = resonance.get("anchor_points", [])
        if anchors:
            lines.append(f"  Якоря: {', '.join(anchors)}")
        vector = resonance.get("vector", "")
        if vector:
            lines.append(f"  Вектор тяги: {vector}")
        taste = resonance.get("hidden_taste", "")
        if taste:
            lines.append(f"  Скрытый вкус: {taste}")
        triggers = resonance.get("triggers", [])
        if triggers:
            lines.append(f"  Триггеры: {', '.join(triggers)}")

    return "\n".join(lines)


async def exec_update_agent_dynamic(args: dict) -> str:
    """Обновить динамические параметры агента."""
    from studio.cabinet.agents import _get_agent_path, _get_agent_dna

    agent_id = args.get("agent_id", "")
    if not agent_id:
        return "Не указан agent_id."

    dna_path = _get_agent_path(agent_id) / "dna.json"
    dna = _get_agent_dna(agent_id)
    if not dna:
        return f"dna.json для {agent_id} не найден."

    dynamic = dna.get("dynamic", {})
    changes = []

    for param in ["Respect", "Patience", "Stress", "Internal_Light"]:
        if param in args:
            old_val = float(dynamic.get(param, 0))
            new_val = max(0.0, min(1.0, float(args[param])))
            dynamic[param] = round(new_val, 2)
            changes.append(f"{param}: {old_val:.2f} → {new_val:.2f}")

    if not changes:
        return "Нет параметров для обновления. Укажи Respect, Patience, Stress или Internal_Light."

    dna["dynamic"] = dynamic

    try:
        dna_path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return f"Ошибка записи dna.json: {e}"

    return f"✅ {agent_id} обновлён:\n" + "\n".join(f"  {c}" for c in changes)


async def exec_find_stressed_agents() -> str:
    """Найти агентов в критическом состоянии по всем цехам."""
    from studio.modules_registry import MODULES_DIR
    from studio.cabinet.agents import _get_agent_info, _get_agent_dna

    if not MODULES_DIR.exists():
        return "Папка modules не найдена."

    critical = []
    for dept_dir in sorted(MODULES_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        for agent_dir in sorted(dept_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            wid = agent_dir.name
            dna = _get_agent_dna(wid, dept_dir.name)
            dynamic = dna.get("dynamic", {})
            if not dynamic:
                continue

            respect = float(dynamic.get("Respect", 1.0))
            patience = float(dynamic.get("Patience", 1.0))
            stress = float(dynamic.get("Stress", 0.0))
            light = float(dynamic.get("Internal_Light", 0.8))
            streak = int(dynamic.get("streak", 0))

            issues = []
            if stress > 0.8:
                issues.append(f"🔥 Stress={stress:.1f}")
            if respect < 0.2:
                issues.append(f"💔 Respect={respect:.1f}")
            if patience == 0.0:
                issues.append(f"🔇 Patience=0")
            if light < 0.3:
                issues.append(f"🌑 Light={light:.1f}")
            if streak <= -3:
                issues.append(f"💀 серия {streak}")

            if issues:
                info = _get_agent_info(wid, dept_dir.name)
                label = info.get("label", wid)
                critical.append(f"• {wid} {label} ({dept_dir.name}): {', '.join(issues)}")

    if not critical:
        return "✅ Все агенты в норме. Критических состояний нет."

    return f"⚠️ Критические состояния ({len(critical)} агентов):\n\n" + "\n".join(critical)


# ── City Walker ──────────────────────────────────

async def exec_city_walk(agent_ids: list | None = None, event: str = "") -> str:
    """Запустить прогулку агентов по городу."""
    try:
        from studio.city_walker import run_city_walk

        messages = []

        async def collect(msg: str):
            messages.append(msg)

        results = await run_city_walk(
            agent_ids=agent_ids or None,
            add_event=event or None,
            on_progress=collect,
        )

        if not results:
            return "Нет агентов для прогулки. Создай агентов через Страницу Жизни."

        ok = [r for r in results if r["status"] == "ok"]
        lines = [f"🌆 Прогулка завершена · {len(ok)}/{len(results)} агентов\n"]

        for r in results:
            if r["status"] == "ok":
                name = r["agent"]
                loc  = r["location"]
                resp = r["response"][:150]
                stress_after = r.get("stress_after", "?")
                light_after  = r.get("light_after", "?")
                lines.append(
                    f"🚶 {name} → {loc}\n"
                    f"   \"{resp}...\"\n"
                    f"   Stress: {stress_after:.2f}  Light: {light_after:.2f}\n"
                )
            elif r["status"] == "skip":
                lines.append(f"⏭ {r['agent']}: {r['reason']}")
            else:
                lines.append(f"❌ {r['agent']}: {r['reason']}")

        return "\n".join(lines)

    except ImportError:
        return "⚠️ city_walker.py не найден. Положи его в studio/city_walker.py"
    except Exception as e:
        return f"❌ Ошибка прогулки: {e}"
