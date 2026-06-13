# studio/cabinet/agents.py — Модуль агентов для Кабинета v2.1
# Двухзонная левая колонка: Резиденты (фикс) + Аккордеон цехов
# Глобальный поиск по имени

from __future__ import annotations

from pathlib import Path
from nicegui import ui

from studio.modules_registry import (
    MODULES_DIR, CURRENT_DEPT,
    _read_json,
)
from studio.config import BASE_DIR


def _get_agent_path(agent_id: str, dept: str = "") -> Path:
    """Путь к папке агента с учётом цеха.
    Если dept не указан — ищем сначала в текущем, потом во всех.
    """
    if dept:
        return MODULES_DIR / dept / agent_id

    # Сначала текущий цех
    p = MODULES_DIR / CURRENT_DEPT / agent_id
    if p.exists():
        return p

    # Поиск по всем цехам (для резидентов и кросс-цеховых запросов)
    if MODULES_DIR.exists():
        for d in MODULES_DIR.iterdir():
            if d.is_dir():
                candidate = d / agent_id
                if candidate.exists():
                    return candidate

    return MODULES_DIR / CURRENT_DEPT / agent_id  # fallback


def _get_agent_info(agent_id: str, dept: str = "") -> dict:
    """Инфа об агенте из info.json (dept-aware)."""
    info_path = _get_agent_path(agent_id, dept) / "info.json"
    data = _read_json(info_path)
    if not data:
        return {"id": agent_id, "label": agent_id, "greeting": f"{agent_id} на связи.", "avatar": ""}
    return {
        "id": data.get("id", agent_id),
        "label": data.get("label", agent_id),
        "greeting": data.get("greeting", f"{agent_id} на связи."),
        "avatar": data.get("avatar", ""),  # имя файла аватара (без расширения)
    }


def _get_agent_dna(agent_id: str, dept: str = "") -> dict:
    """ДНК агента из dna.json (dept-aware)."""
    dna_path = _get_agent_path(agent_id, dept) / "dna.json"
    return _read_json(dna_path)


def _get_agent_home(agent_id: str, dept: str = "") -> str:
    """Домашний контекст агента (dept-aware)."""
    home_path = _get_agent_path(agent_id, dept) / "home" / "home_prompt.md"
    if home_path.exists():
        try:
            return home_path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""

# ── Аватары ───────────────────────────────────────
# Путь: static/avatars/{dept}/{agent_id}.png
AVATARS_DIR = Path(BASE_DIR) / "static" / "avatars"
AVATARS_URL_BASE = "/avatars"  # NiceGUI static mount

# Маппинг dept slug → папка аватаров
DEPT_AVATAR_MAP = {
    "residents": "residents",
    "turbo": "turbo",
    "video_long": "video_long",
    "video_shorts": "video_shorts",
    "social_mix": "social_mix",
    "web_story": "web_story",
}

# Список всех доступных цехов
# residents — ПЕРВЫЙ в списке, постоянные жители Студии (Лока, ДЖем, ...)
# is_permanent: True — НЕ показывать в аккордеоне, отдельная зона
DEPARTMENTS = [
    {"id": "residents",    "label": "резиденты",    "prefix": "", "is_permanent": True},
    {"id": "turbo",        "label": "turbo",        "prefix": "A"},
    {"id": "video_long",   "label": "video-long",   "prefix": "A"},
    {"id": "video_shorts", "label": "video-shorts",  "prefix": "A"},
    {"id": "social_mix",   "label": "social-mix",   "prefix": "A"},
    {"id": "web_story",    "label": "web-story",    "prefix": "A"},
    {"id": "clipmakers",   "label": "clipmakers",   "prefix": "A"},
    {"id": "advertising",  "label": "advertising",  "prefix": "A"},
    {"id": "emo_card",     "label": "emo-card",     "prefix": "A"},
    {"id": "logo_design",  "label": "logo-design",  "prefix": "A"},
    {"id": "market_hit",   "label": "market-hit",   "prefix": "A"},
    {"id": "living_book",  "label": "living-book",  "prefix": "A"},
    {"id": "trading",      "label": "trading",      "prefix": "A"},
]

# Цехи для аккордеона (без residents)
CITY_DEPARTMENTS = [d for d in DEPARTMENTS if not d.get("is_permanent")]

# Цвета динамических параметров
BAR_COLORS = {
    "Respect": "#a78bfa",
    "Patience": "#c9a84c",
    "Stress": "#f87171",
    "Internal_Light": "#fbbf24",
}

BAR_LABELS = {
    "Respect": "RSP",
    "Patience": "PAT",
    "Stress": "STR",
    "Internal_Light": "LGT",
}


# ── Кэш каталога реестра (для аватаров) ───────────
_registry_cache: dict | None = None
_registry_cache_mtime: float = 0

REGISTRY_CATALOG_FILE = Path("00_REGISTRY_NFT/catalog.json")
REGISTRY_IMAGES_DIR = Path("00_REGISTRY_NFT/images")


def _load_registry_cache() -> list[dict]:
    """Загружает каталог реестра с кэшированием по mtime."""
    global _registry_cache, _registry_cache_mtime
    if not REGISTRY_CATALOG_FILE.exists():
        return []
    try:
        mtime = REGISTRY_CATALOG_FILE.stat().st_mtime
        if _registry_cache is not None and mtime == _registry_cache_mtime:
            return _registry_cache
        import json
        _registry_cache = json.loads(REGISTRY_CATALOG_FILE.read_text(encoding="utf-8"))
        _registry_cache_mtime = mtime
        return _registry_cache
    except Exception:
        return []


def get_avatar_url(agent_id: str, dept: str = "", avatar_name: str = "") -> str:
    """Возвращает URL аватара агента.

    Приоритет:
    1. avatar_name из info.json (если указан) → static/avatars/{dept}/{avatar_name}.png
    2. Имя папки агента → static/avatars/{dept}/{agent_id}.png
    3. Реестр NFT — _image_path из catalog.json (фоллбэк)
    4. Пустая строка (fallback на initials)

    Правило: в info.json поле "avatar": "LOKA" — имя файла без расширения.
    Если не указан — ищем по имени папки.
    """
    target_dept = dept or CURRENT_DEPT
    avatar_folder = DEPT_AVATAR_MAP.get(target_dept, target_dept)

    # Список имён для поиска: сначала avatar_name, потом agent_id
    names_to_try = []
    if avatar_name:
        names_to_try.append(avatar_name)
    if agent_id != avatar_name:
        names_to_try.append(agent_id)

    # 1+2. Файл аватара
    for name in names_to_try:
        for ext in (".png", ".jpg", ".webp"):
            avatar_path = AVATARS_DIR / avatar_folder / f"{name}{ext}"
            if avatar_path.exists():
                return f"{AVATARS_URL_BASE}/{avatar_folder}/{name}{ext}"

    # 3. Реестр NFT — фоллбэк по ID_Object
    catalog = _load_registry_cache()
    for obj in catalog:
        obj_id = obj.get("ID_Object", "")
        if obj_id == agent_id or obj_id == avatar_name:
            img_path = obj.get("_image_path", "")
            if img_path and Path(img_path).exists():
                rel = str(img_path).replace(str(REGISTRY_IMAGES_DIR), "/registry_images")
                return rel
            break

    return ""


def get_agent_status(dna: dict) -> tuple[str, str]:
    """Определяет статус агента из dynamic DNA."""
    dynamic = dna.get("dynamic", {})
    if not dynamic:
        return ("дома", "cab-status-idle")

    respect = float(dynamic.get("Respect", 1.0))
    patience = float(dynamic.get("Patience", 1.0))
    stress = float(dynamic.get("Stress", 0.0))

    if patience == 0.0:
        return ("тишина", "cab-status-silence")
    if respect < 0.2:
        return ("враждебен", "cab-status-stress")
    if stress > 0.8:
        return ("стресс", "cab-status-stress")
    if stress > 0.5:
        return ("напряжён", "cab-status-block")

    return ("дома", "cab-status-idle")


def get_agent_card_class(dna: dict) -> str:
    """Дополнительный CSS-класс для карточки агента."""
    dynamic = dna.get("dynamic", {})
    if not dynamic:
        return ""
    stress = float(dynamic.get("Stress", 0.0))
    patience = float(dynamic.get("Patience", 1.0))
    if stress > 0.8 or patience == 0.0:
        return "stress"
    if stress > 0.5:
        return "block"
    return ""


def list_dept_agents(dept: str = "") -> list[dict]:
    """Список агентов цеха с полной инфой для рендера."""
    target_dept = dept or CURRENT_DEPT
    dept_path = MODULES_DIR / target_dept
    if not dept_path.exists():
        return []

    is_resident_dept = target_dept == "residents"
    agents = []
    for d in sorted(dept_path.iterdir()):
        if not d.is_dir():
            continue
        wid = d.name
        info = _get_agent_info(wid, target_dept)
        dna = _get_agent_dna(wid, target_dept)
        dynamic = dna.get("dynamic", {})
        status_text, status_class = get_agent_status(dna)
        card_class = get_agent_card_class(dna)

        streak = int(dynamic.get("streak", 0))
        stars = int(dynamic.get("stars", 0))

        agents.append({
            "id": wid,
            "dept": target_dept,
            "label": info.get("label", wid),
            "greeting": info.get("greeting", ""),
            "avatar_url": get_avatar_url(wid, target_dept, avatar_name=info.get("avatar", "")),
            "dna": dna,
            "dynamic": dynamic,
            "status_text": status_text,
            "status_class": status_class,
            "card_class": card_class,
            "streak": streak,
            "stars": stars,
            "is_resident": is_resident_dept,
        })

    return agents


def list_all_agents() -> dict[str, list[dict]]:
    """Все агенты всех цехов, сгруппированные по dept.

    Returns:
        {"residents": [...], "turbo": [...], "web_story": [...], ...}
    """
    result = {}
    for dept in DEPARTMENTS:
        agents = list_dept_agents(dept["id"])
        if agents:
            result[dept["id"]] = agents
    return result


def search_agents_global(query: str) -> list[dict]:
    """Глобальный поиск агентов по имени/ID по всем цехам."""
    query = query.lower().strip()
    if not query:
        return []

    results = []
    for dept in DEPARTMENTS:
        for agent in list_dept_agents(dept["id"]):
            name = f'{agent["id"]} {agent["label"]}'.lower()
            if query in name:
                results.append(agent)
    return results




# ═══════════════════════════════════════════════════
#  LIBRARY CONTEXT (для Оле)
# ═══════════════════════════════════════════════════

def _get_library_context() -> str:
    """Загружает каталог библиотеки как контекст для Оле.
    
    Вызывается при сборке system_prompt когда выбран агент 004_OLE.
    Возвращает строку с полным каталогом книг для инъекции в промпт.
    """
    import json
    catalog_file = Path("studio/library/catalog.json")
    if not catalog_file.exists():
        return "\n[КАТАЛОГ БИБЛИОТЕКИ: не найден]\n"
    
    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        books = catalog.get("books", [])
        sections = catalog.get("sections", {})
        
        lines = ["\n=== КАТАЛОГ БИБЛИОТЕКИ ГРОНДХЕЙМА ==="]
        lines.append(f"Всего книг: {len(books)}\n")
        
        for sec_id, sec_desc in sections.items():
            sec_books = [b for b in books if b.get("section") == sec_id]
            if not sec_books:
                continue
            lines.append(f"📚 {sec_desc} [{sec_id}]:")
            for b in sec_books:
                annotation = b.get("annotation", "")
                tags = ", ".join(b.get("tags", [])[:5])
                linked = b.get("linked_books", [])
                lines.append(f"  • {b['id']}: «{b['title']}» ({b['depth']})")
                if annotation:
                    lines.append(f"    📝 {annotation}")
                lines.append(f"    Теги: [{tags}]")
                if linked:
                    lines.append(f"    Связи: {', '.join(linked)}")
            lines.append("")
        
        lines.append("=== КОНЕЦ КАТАЛОГА ===")
        return "\n".join(lines)
    except Exception as e:
        return f"\n[КАТАЛОГ БИБЛИОТЕКИ: ошибка загрузки — {e}]\n"

# ═══════════════════════════════════════════════════
#  UI RENDER HELPERS (NiceGUI)
# ═══════════════════════════════════════════════════

def render_resident_card(agent: dict, is_active: bool, on_click) -> None:
    """Компактная карточка резидента (верхняя зона) + мини-бары ДНК."""
    cls = "cab-resident-card"
    if is_active:
        cls += " active"

    card = ui.element("div").classes(cls)
    card.on("click", lambda e, _id=agent["id"], _dept=agent.get("dept", ""): on_click(_id, _dept))

    with card:
        # Avatar
        avatar_url = agent["avatar_url"]
        if avatar_url:
            ui.element("div").classes("cab-resident-avatar").style(
                f"background-image: url('{avatar_url}');"
            )
        else:
            ui.element("div").classes("cab-resident-avatar").style(
                "display: flex; align-items: center; justify-content: center; "
                "font-family: 'JetBrains Mono'; font-size: 0.48rem; color: #c9a84c;"
            ).props(f'inner-html="{agent["id"]}"')

        ui.label(f'{agent["label"]}').classes("cab-resident-name")

        # ═══ Мини-бары ДНК (как у рабочих агентов) ═══
        dynamic = agent.get("dynamic", {})
        if dynamic:
            with ui.element("div").classes("cab-bars").style("margin: 2px 0;"):
                for param in ["Respect", "Patience", "Stress", "Internal_Light"]:
                    val = float(dynamic.get(param, 0.5))
                    pct = round(val * 100)
                    color = BAR_COLORS.get(param, "#6c8cff")
                    lbl = BAR_LABELS.get(param, param[:3])
                    with ui.element("div").classes("cab-bar-group"):
                        ui.html(f'<div class="cab-bar-label">{lbl}</div>')
                        ui.html(
                            f'<div class="cab-bar-track">'
                            f'<div class="cab-bar-fill" style="width:{pct}%;background:{color}"></div>'
                            f'</div>'
                        )

        ui.html(
            f'<span class="cab-resident-status cab-status-resident">'
            f'{agent["status_text"]}</span>'
        )


def render_agent_card(agent: dict, is_active: bool, on_click) -> None:
    """Рендерит карточку агента (внутри аккордеона цеха)."""
    cls = "cab-agent-card"
    if agent.get("is_resident"):
        cls += " resident"
    if is_active:
        cls += " active"
    if agent["card_class"]:
        cls += f" {agent['card_class']}"

    card = ui.element("div").classes(cls)
    card.on("click", lambda e, _id=agent["id"], _dept=agent.get("dept", ""): on_click(_id, _dept))

    with card:
        # Top row: avatar + name + status
        with ui.element("div").classes("cab-agent-top"):
            avatar_url = agent["avatar_url"]
            if avatar_url:
                ui.element("div").classes("cab-agent-avatar").style(
                    f"background-image: url('{avatar_url}');"
                )
            else:
                ui.element("div").classes("cab-agent-avatar").style(
                    "display: flex; align-items: center; justify-content: center; "
                    "font-family: 'JetBrains Mono'; font-size: 0.52rem; color: #6c8cff;"
                ).props(f'inner-html="{agent["id"]}"')

            ui.label(f'{agent["id"]} {agent["label"]}').classes("cab-agent-name")
            ui.html(
                f'<span class="cab-agent-status {agent["status_class"]}">{agent["status_text"]}</span>'
            )

        # Mini bars: RSP / PAT / STR / LGT
        dynamic = agent["dynamic"]
        if dynamic:
            with ui.element("div").classes("cab-bars"):
                for param in ["Respect", "Patience", "Stress", "Internal_Light"]:
                    val = float(dynamic.get(param, 0.5))
                    pct = round(val * 100)
                    color = BAR_COLORS.get(param, "#6c8cff")
                    lbl = BAR_LABELS.get(param, param[:3])
                    with ui.element("div").classes("cab-bar-group"):
                        ui.html(f'<div class="cab-bar-label">{lbl}</div>')
                        ui.html(
                            f'<div class="cab-bar-track">'
                            f'<div class="cab-bar-fill" style="width:{pct}%;background:{color}"></div>'
                            f'</div>'
                        )

        # Meta: stars + streak
        stars = agent["stars"]
        streak = agent["streak"]
        meta_parts = []
        if stars > 0:
            meta_parts.append("⭐" * min(stars, 5))
        if streak >= 3:
            meta_parts.append(f"серия {streak}")
        elif streak <= -3:
            meta_parts.append(f"💀 серия {streak}")
        if meta_parts:
            with ui.element("div").classes("cab-agent-meta"):
                ui.label(" · ".join(meta_parts))


def render_agent_detail(agent: dict, on_talk) -> None:
    """Рендерит детальную панель агента (правая колонка, таб 'агент')."""
    # Avatar (large)
    with ui.element("div").style("text-align: center; padding: 8px 0 10px;"):
        avatar_url = agent["avatar_url"]
        if avatar_url:
            ui.element("div").classes("cab-detail-avatar").style(
                f"background-image: url('{avatar_url}');"
            )
        ui.label(f'{agent["id"]} {agent["label"]}').style(
            "font-family: 'JetBrains Mono'; font-size: 0.75rem; font-weight: 500; "
            "color: rgba(220,225,240,0.92); display: block; margin-top: 4px;"
        )
        if agent.get("greeting"):
            ui.label(agent["greeting"]).style(
                "font-family: 'JetBrains Mono'; font-size: 0.56rem; "
                "color: rgba(180,190,220,0.6); display: block; margin-top: 2px;"
            )
        # Status
        ui.html(
            f'<div style="margin-top: 4px;">'
            f'<span class="cab-agent-status {agent["status_class"]}">{agent["status_text"]}</span>'
            f'</div>'
        )

    dna = agent.get("dna", {})

    # Static DNA
    static = dna.get("static", {})
    if static:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">статическая днк</div>')
            for k, v in static.items():
                val = float(v) if isinstance(v, (int, float)) else 0.5
                pct = round(val * 100)
                with ui.element("div").classes("cab-dna-row"):
                    ui.label(k).classes("cab-dna-label")
                    ui.html(
                        f'<div class="cab-dna-bar">'
                        f'<div class="cab-dna-fill" style="width:{pct}%;background:#a78bfa"></div>'
                        f'</div>'
                    )
                    ui.label(f"{val:.2f}").classes("cab-dna-val")

    # Dynamic
    dynamic = dna.get("dynamic", {})
    if dynamic:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">динамика</div>')
            for param in ["Respect", "Patience", "Stress", "Internal_Light"]:
                if param not in dynamic:
                    continue
                val = float(dynamic[param])
                pct = round(val * 100)
                color = BAR_COLORS.get(param, "#6c8cff")
                with ui.element("div").classes("cab-dna-row"):
                    ui.label(param).classes("cab-dna-label")
                    ui.html(
                        f'<div class="cab-dna-bar">'
                        f'<div class="cab-dna-fill" style="width:{pct}%;background:{color}"></div>'
                        f'</div>'
                    )
                    ui.label(f"{val:.2f}").classes("cab-dna-val")

    # ═══ Резонанс (pull_vector, hidden_taste, trigger_keywords) ═══
    resonance = dna.get("resonance", {})
    pull = resonance.get("pull_vector", "")
    taste = resonance.get("hidden_taste", "")
    triggers = resonance.get("trigger_keywords", [])

    if pull or taste or triggers:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">резонанс</div>')
            if pull:
                # pull_vector может быть списком или строкой
                if isinstance(pull, list):
                    pull_text = "; ".join(str(x)[:80] for x in pull[:3])
                else:
                    pull_text = str(pull)[:200]
                ui.label(f"Тяги: {pull_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6); margin-bottom: 4px;"
                )
            if taste:
                if isinstance(taste, list):
                    taste_text = "; ".join(str(x)[:60] for x in taste[:3])
                else:
                    taste_text = str(taste)[:200]
                ui.label(f"Вкус: {taste_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6); margin-bottom: 4px;"
                )
            if triggers:
                if isinstance(triggers, list):
                    tags_text = ", ".join(str(t) for t in triggers[:6])
                else:
                    tags_text = str(triggers)
                ui.label(f"Триггеры: {tags_text}").style(
                    "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(201,168,76,0.6); margin-bottom: 4px;"
                )

    # Feedback
    stars = agent.get("stars", 0)
    streak = agent.get("streak", 0)
    if stars or streak:
        with ui.element("div").style("margin-bottom: 12px;"):
            ui.html('<div class="cab-detail-header">feedback</div>')
            parts = []
            if stars:
                parts.append("⭐" * min(stars, 5))
            if streak >= 3:
                parts.append(f"серия побед: {streak}")
            elif streak <= -3:
                parts.append(f"серия провалов: {abs(streak)}")
            ui.label(" · ".join(parts)).style(
                "font-family: 'JetBrains Mono'; font-size: 0.56rem; color: rgba(180,190,220,0.6);"
            )

    # Talk button
    ui.element("div").classes("cab-talk-btn").on(
        "click", lambda e, _id=agent["id"]: on_talk(_id)
    ).props(f'inner-html="💬 поговорить с {agent["label"]}"')
