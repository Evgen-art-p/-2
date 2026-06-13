# patch_cartridge_law.py
# ═══════════════════════════════════════════════════════════════
# ЗАКОН КАРТРИДЖА (Спринт 45) — рек. 123, баг #34
#
# «Один работает, три одинаковых работают, тасуй как нужно —
#  появляются и исчезают везде как положено, только город помнит.»
#
# Три статьи закона:
#   1. Картридж объявляет себя сам: папка в modules/ + manifest.json.
#      Его id — ИМЯ ПАПКИ, не поле в манифесте
#      (копия папки trading → trading_b = новый цех, без коллизий).
#   2. Никто не ведёт списков: все UI сканируют modules/ на лету.
#   3. Город помнит снаружи: хроники/пульс/NFT/биллинг — вне modules/.
#
# Что делает патч (7 файлов, 21 правка):
#
#   studio/modules_registry.py
#     + list_cartridges() / get_cartridge() — ЕДИНСТВЕННЫЙ сканер цехов
#     ⚰ DEPT_PIPELINE_CONFIG → пустой (фазы living_book давно в манифесте)
#     ✎ get_dept_workers() читает фазы из manifest.json цеха
#       (trading получает SENSORS/MEMORY/TRIBUNAL/EXECUTION вместо 3×4)
#     ✎ load_depts() для Приёмной: сканер + правило видимости
#       (client_facing в манифесте; trading без info.json — скрыт, Совет)
#
#   studio/cabinet/agents.py
#     ✎ DEPARTMENTS-хардкод (13 строк) → get_departments() живой скан
#       (вчерашний костыль patch_cabinet_trading_dept растворяется в законе)
#
#   studio/cabinet/ui_cabinet.py
#     ✎ аккордеон, карта, матрица, поиск зовут живые функции
#       (иначе списки замерзают на момент импорта)
#
#   studio/ui_registry.py (Страница Жизни)
#     ✎ WORKSHOP_OPTIONS → скан картриджей
#     ✎ ROLE_OPTIONS_MAP → роли из phases манифеста цеха
#     ✎ квартал агента: сначала из манифеста цеха, потом словарь
#
#   studio/cartridge.py
#     ✎ id картриджа = имя папки (статья 1 — без этого копия папки
#       грузилась бы с чужим id из манифеста)
#     ⚰ зависимость от DEPT_PIPELINE_CONFIG
#
#   studio/workshop/ui.py
#     ✎ run_type цеха: словарь Шефа главнее (video_long = episode),
#       новые цеха берут run_type из своего манифеста
#       (trading получает run_type "trading", а не дефолтный "social")
#
#   studio/modules/trading/manifest.json
#     + "quarter": "Торговый Квартал" (мост к Закону Пары)
#     + "client_facing": false (Совет — не клиентский цех, явно)
#
# После патча следующий цех — хоть Фабрика Картриджей его родит,
# хоть руками скопируешь папку — появится в Кабинете, Странице Жизни
# и Мастерской САМ. Без патчей. ШАГ 10 закрывается навсегда.
#
# Запуск:  python patch_cartridge_law.py   (из корня, где main.py)
# Бэкапы:  _patch_backups/cartridge_law_{дата}/
# Потом:   перезапустить main.py
# ═══════════════════════════════════════════════════════════════
import json
import shutil
import subprocess
import sys
import py_compile
from datetime import datetime
from pathlib import Path

BACKUP_ROOT = Path("_patch_backups")

# ───────────────────────────────────────────────────────────────
#  НОВЫЕ БЛОКИ КОДА
# ───────────────────────────────────────────────────────────────

SCANNER_BLOCK = '''# ═══════════════════════════════════════════════════════════════
#  ЗАКОН КАРТРИДЖА (Спринт 45) — единственный сканер цехов
#
#  1. Картридж объявляет себя сам: папка в modules/ + manifest.json.
#     Его id — ИМЯ ПАПКИ, не поле в манифесте.
#     Копия папки (trading → trading_b) = новый цех, без коллизий.
#  2. Никто не ведёт списков: Кабинет, Реестр, Приёмная, карта —
#     все строят свои списки отсюда, на лету.
#     Удалил папку — цех исчез отовсюду. Пусто — студия работает пустая.
#  3. Город помнит снаружи: хроники, пульс, traces, NFT, биллинг
#     живут вне modules/ и переживают любой картридж.
# ═══════════════════════════════════════════════════════════════

def _build_cartridge(d: Path) -> dict | None:
    """Паспорт картриджа из его папки. None — если это не картридж."""
    manifest_path = d / "manifest.json"
    if not manifest_path.exists():
        return None  # residents и прочие папки без манифеста — не картриджи

    m = _read_json(manifest_path)
    if not isinstance(m, dict):
        m = {}
    info = _read_json(d / "info.json")  # клиентская карточка (может не быть)
    if not isinstance(info, dict):
        info = {}

    phases = m.get("phases", {})
    if not isinstance(phases, dict):
        phases = {}
    roles = [a for agents in phases.values() if isinstance(agents, list) for a in agents]

    prio = m.get("priority")
    if prio is None:
        prio = info.get("priority")
    try:
        prio = int(prio)
    except (TypeError, ValueError):
        prio = 100

    return {
        "id": d.name,                              # ЗАКОН: id = имя папки
        "label": m.get("label", d.name),
        "icon": m.get("icon", info.get("icon", "🔧")),
        "run_type": m.get("run_type", d.name),
        "phases": phases,
        "roles": roles,                            # плоский A.. в порядке фаз
        "qa_agent": m.get("qa_agent", ""),
        "quarter": m.get("quarter", ""),           # квартал города (мост к Закону Пары)
        "client_facing": m.get("client_facing"),   # None = решает наличие info.json
        "has_info": bool(info),
        "manifest": m,
        "info": info,
        "priority": prio,
    }


def list_cartridges() -> list[dict]:
    """Все картриджи студии — живым сканом modules/, без списков в коде.

    Сортировка: priority (манифест → info.json → 100), затем имя папки.
    Битый манифест не валит сканер — цех пропускается с предупреждением.
    """
    carts: list[dict] = []
    if not MODULES_DIR.exists():
        return carts

    for d in sorted(MODULES_DIR.iterdir()):
        if not _is_valid_dir(d):
            continue
        try:
            cart = _build_cartridge(d)
        except Exception as e:
            print(f"[CARTRIDGE] ⚠ {d.name}: манифест не прочитан — {e}")
            continue
        if cart:
            carts.append(cart)

    carts.sort(key=lambda c: (c["priority"], c["id"]))
    return carts


def get_cartridge(dept: str) -> dict | None:
    """Паспорт одного картриджа по имени папки. None — цеха нет."""
    if not dept:
        return None
    d = MODULES_DIR / dept
    if not _is_valid_dir(d):
        return None
    try:
        return _build_cartridge(d)
    except Exception:
        return None
'''

NEW_LOAD_DEPTS = '''def load_depts() -> list[Dept]:
    """Для ui_reception.py — список клиентских цехов.

    ЗАКОН КАРТРИДЖА: источник — сканер list_cartridges().
    Клиентская карточка (label, color, placeholder, suggest...) — info.json;
    если её нет, поля берутся прямо из manifest.json.

    Видимость в Приёмной:
      client_facing: false в манифесте → скрыт всегда;
      client_facing: true  в манифесте → виден даже без info.json;
      флага нет → виден только если есть info.json (карточка = приглашение).
    Так trading (Совет, не клиентский цех) остаётся за дверью Приёмной.
    """
    depts: list[Dept] = []

    for c in list_cartridges():
        cf = c.get("client_facing")
        if cf is False:
            continue
        if cf is not True and not c.get("has_info"):
            continue

        # info.json главнее манифеста — это карточка для клиента
        src = dict(c.get("manifest") or {})
        src.update(c.get("info") or {})

        depts.append(
            Dept(
                id=c["id"],  # ЗАКОН: id = имя папки, не поле в файле
                label=src.get("label", src.get("name", c["id"])),
                icon=src.get("icon", "🔧"),
                color=src.get("color", "gray"),
                placeholder=src.get("placeholder", ""),
                suggest=src.get("suggest", []) or [],
                keywords=src.get("keywords", []) or [],
                priority=int(src.get("priority", 100)),
            )
        )

    depts.sort(key=lambda x: x.priority)
    return depts
'''

OLD_LOAD_DEPTS = '''def load_depts() -> list[Dept]:
    """Для ui_reception.py — список департаментов"""
    depts: list[Dept] = []
    if not MODULES_DIR.exists():
        return depts

    for d in MODULES_DIR.iterdir():
        if not _is_valid_dir(d):
            continue
        info_path = d / "info.json"
        if not info_path.exists():
            continue

        data = _read_json(info_path)
        depts.append(
            Dept(
                id=data.get("id", d.name),
                label=data.get("label", data.get("name", d.name)),
                icon=data.get("icon", "🔧"),
                color=data.get("color", "gray"),
                placeholder=data.get("placeholder", ""),
                suggest=data.get("suggest", []) or [],
                keywords=data.get("keywords", []) or [],
                priority=int(data.get("priority", 100)),
            )
        )

    depts.sort(key=lambda x: x.priority)
    return depts
'''

OLD_DEPARTMENTS_BLOCK = '''# Список всех доступных цехов
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
CITY_DEPARTMENTS = [d for d in DEPARTMENTS if not d.get("is_permanent")]'''

NEW_DEPARTMENTS_BLOCK = '''# ── ЗАКОН КАРТРИДЖА (Спринт 45) ────────────────────────────────
# Список цехов больше НЕ ведётся руками — его строит сканер.
# residents — первая, постоянная зона (не картридж: без manifest.json).
# Остальные цеха появляются и исчезают вместе со своими папками
# в modules/ — на лету, без патчей.

def get_departments() -> list[dict]:
    """Цеха Кабинета: резиденты + все картриджи из modules/ — живой скан."""
    depts = [
        {"id": "residents", "label": "резиденты", "prefix": "", "is_permanent": True},
    ]
    for c in list_cartridges():
        depts.append({
            "id": c["id"],
            "label": c["id"].replace("_", "-"),  # стиль Кабинета: video_long → video-long
            "prefix": "A",
        })
    return depts


def get_city_departments() -> list[dict]:
    """Цеха для аккордеона (без residents) — живой скан."""
    return [d for d in get_departments() if not d.get("is_permanent")]


# Снимки на момент импорта — только для обратной совместимости.
# Живые места (аккордеон, карта, матрица, поиск) зовут функции выше.
DEPARTMENTS = get_departments()
CITY_DEPARTMENTS = get_city_departments()'''

NEW_REGISTRY_FUNCS = '''
# ── ЗАКОН КАРТРИДЖА (Спринт 45) ────────────────────────────────
# Списки выше остаются как страховочный fallback.
# Живые источники — сканер modules/ и phases из манифестов:
# новый цех появляется в Странице Жизни сам, без правок этого файла.

def get_workshop_options() -> list[str]:
    """Цеха для селекта рождения: residents + все картриджи (живой скан)."""
    from studio.modules_registry import list_cartridges
    return ["", "residents"] + [c["id"] for c in list_cartridges()]


def get_role_options(workshop: str) -> list[str]:
    """Роли цеха — из phases его manifest.json, в порядке фаз.

    residents — лор-роли (administrator/keeper/...), не из манифеста.
    Цех без манифеста или без фаз — стандарт A01–A12.
    """
    if workshop == "residents":
        return RESIDENT_ROLE_OPTIONS
    from studio.modules_registry import get_cartridge
    cart = get_cartridge(workshop)
    if cart and cart.get("roles"):
        return [""] + list(cart["roles"])
    return PIPELINE_ROLE_OPTIONS
'''

NEW_RUNTYPE_HELPER = '''

def _dept_runtype(dept: str) -> str:
    """ЗАКОН КАРТРИДЖА: режим работы цеха.

    Сначала рабочие дефолты Шефа (словарь выше — они главнее манифеста:
    у video_long рабочий режим episode, а не full из манифеста),
    затем run_type из manifest.json картриджа — новый цех получает
    свой режим сам, без правок этого файла. Дефолт: social.
    """
    rt = DEPT_TO_RUNTYPE.get(dept)
    if rt:
        return rt
    from studio.modules_registry import get_cartridge
    cart = get_cartridge(dept)
    if cart and cart.get("run_type"):
        return cart["run_type"]
    return "social"
'''

# ───────────────────────────────────────────────────────────────
#  ПРАВКИ
#  old → new, done = маркер «уже применено», requires = зависимости
# ───────────────────────────────────────────────────────────────

FIXES = [

    # ═══ studio/modules_registry.py ═══════════════════════════
    dict(
        id="M1", file="studio/modules_registry.py",
        name="modules_registry: list_cartridges() — единственный сканер",
        old="# === Совместимость с ui_reception.py ===",
        new=SCANNER_BLOCK + "\n\n# === Совместимость с ui_reception.py ===",
        done="def list_cartridges(",
        requires=[],
    ),
    dict(
        id="M3", file="studio/modules_registry.py",
        name="modules_registry: get_dept_workers() читает фазы из манифеста",
        old='''    """Получить WORKERS dict для департамента.

    Для living_book: читает из DEPT_PIPELINE_CONFIG.
    Для остальных: стандартная структура 3×4.
    Всегда читает реальные папки как fallback.
    """
    dept = dept or CURRENT_DEPT

    # Проверяем есть ли конфиг для этого цеха
    config = DEPT_PIPELINE_CONFIG.get(dept)
    if config:
        phases = config["phases"]
        # Валидируем: убираем агентов у которых нет папки
        dept_path = MODULES_DIR / dept
        validated = {}
        for phase_name, agents in phases.items():
            existing = [a for a in agents if _is_valid_dir(dept_path / a)]
            if existing:
                validated[phase_name] = existing
        return validated''',
        new='''    """Получить WORKERS dict для департамента.

    ЗАКОН КАРТРИДЖА: фазы — из manifest.json цеха
    (SENSORS/TRIBUNAL у trading, GENESIS/DELIVERY у living_book).
    Без манифеста или фаз: стандартная структура 3×4 по реальным папкам.
    """
    dept = dept or CURRENT_DEPT

    # ЗАКОН КАРТРИДЖА: фазы цеха читаются из его manifest.json
    cart = get_cartridge(dept)
    if cart and cart.get("phases"):
        # Валидируем: убираем агентов у которых нет папки
        dept_path = MODULES_DIR / dept
        validated = {}
        for phase_name, agents in cart["phases"].items():
            existing = [a for a in agents if _is_valid_dir(dept_path / a)]
            if existing:
                validated[phase_name] = existing
        if validated:
            return validated''',
        done="cart = get_cartridge(dept)",
        requires=["M1"],
    ),
    dict(
        id="M2", file="studio/modules_registry.py",
        name="modules_registry: DEPT_PIPELINE_CONFIG похоронен (фазы — в манифестах)",
        old='''# Конфигурация цехов: какие фазы и checkpoints
DEPT_PIPELINE_CONFIG = {
    "living_book": {
        "phases": {
            "GENESIS":   ["A00", "A00a"],
            "PRE-PROD":  ["A01", "A02", "A03", "A04"],
            "PROD":      ["A05", "A06", "A07", "A08"],
            "POST-PROD": ["A09", "A10", "A11", "A12"],
            "DELIVERY":  ["A13", "A14", "A15", "A16"],
        },
        "revision_loop": {
            # Если A00a (Вера Душа) возвращает REVISION — задача идёт назад на A00
            "reviewer": "A00a",
            "return_to": "A00",
            "status_field": "verdict",      # поле в meta ответа
            "revision_value": "REVISION",   # значение = переделка
            "approved_value": "APPROVED",   # значение = прошло
            "max_loops": 3,                 # максимум петель
        },
    },
    # Другие цеха используют дефолтную структуру 3×4
}''',
        new='''# Конфигурация цехов: какие фазы и checkpoints
# ⚰️ ЗАКОН КАРТРИДЖА (Спринт 45): хардкод похоронен.
# Фазы и revision_loop живут в manifest.json каждого цеха —
# living_book носит их там со времён картриджной архитектуры,
# get_dept_workers() и CartridgeManifest читают манифест напрямую.
# Имя оставлено пустым для совместимости импортов (workshop/ui.py).
DEPT_PIPELINE_CONFIG: dict = {}''',
        done="хардкод похоронен",
        requires=["M3"],
    ),
    dict(
        id="M4", file="studio/modules_registry.py",
        name="modules_registry: load_depts() Приёмной — через сканер + client_facing",
        old=OLD_LOAD_DEPTS,
        new=NEW_LOAD_DEPTS,
        done="Так trading (Совет, не клиентский цех)",
        requires=["M1"],
    ),

    # ═══ studio/cabinet/agents.py ═════════════════════════════
    dict(
        id="A1", file="studio/cabinet/agents.py",
        name="cabinet/agents: импорт list_cartridges",
        old='''from studio.modules_registry import (
    MODULES_DIR, CURRENT_DEPT,
    _read_json,
)''',
        new='''from studio.modules_registry import (
    MODULES_DIR, CURRENT_DEPT,
    _read_json, list_cartridges,
)''',
        done="_read_json, list_cartridges,",
        requires=["M1"],
    ),
    dict(
        id="A2", file="studio/cabinet/agents.py",
        name="cabinet/agents: DEPARTMENTS-хардкод → get_departments() живой скан",
        old=OLD_DEPARTMENTS_BLOCK,
        new=NEW_DEPARTMENTS_BLOCK,
        done="def get_departments(",
        requires=["A1"],
    ),
    dict(
        id="A3", file="studio/cabinet/agents.py",
        name="cabinet/agents: list_all_agents() — живой скан",
        old='''    for dept in DEPARTMENTS:
        agents = list_dept_agents(dept["id"])''',
        new='''    for dept in get_departments():
        agents = list_dept_agents(dept["id"])''',
        done='''    for dept in get_departments():
        agents = list_dept_agents(dept["id"])''',
        requires=["A2"],
    ),
    dict(
        id="A4", file="studio/cabinet/agents.py",
        name="cabinet/agents: search_agents_global() — живой скан",
        old='''    results = []
    for dept in DEPARTMENTS:
        for agent in list_dept_agents(dept["id"]):''',
        new='''    results = []
    for dept in get_departments():
        for agent in list_dept_agents(dept["id"]):''',
        done='''    for dept in get_departments():
        for agent in list_dept_agents(dept["id"]):''',
        requires=["A2"],
    ),

    # ═══ studio/cabinet/ui_cabinet.py ═════════════════════════
    dict(
        id="C1", file="studio/cabinet/ui_cabinet.py",
        name="ui_cabinet: импорт живых функций",
        old='''from studio.cabinet.agents import (
    DEPARTMENTS, CITY_DEPARTMENTS,
    list_dept_agents, list_all_agents, search_agents_global,''',
        new='''from studio.cabinet.agents import (
    DEPARTMENTS, CITY_DEPARTMENTS,
    get_departments, get_city_departments,
    list_dept_agents, list_all_agents, search_agents_global,''',
        done="get_departments, get_city_departments,",
        requires=["A2"],
    ),
    dict(
        id="C2", file="studio/cabinet/ui_cabinet.py",
        name="ui_cabinet: аккордеон цехов — живой скан",
        old="            for dept in CITY_DEPARTMENTS:",
        new="            for dept in get_city_departments():",
        done="            for dept in get_city_departments():",
        requires=["C1"],
    ),
    dict(
        id="C3", file="studio/cabinet/ui_cabinet.py",
        name="ui_cabinet: карта (локальный импорт) — живой скан",
        old="            from studio.cabinet.agents import _get_agent_dna, DEPARTMENTS",
        new="            from studio.cabinet.agents import _get_agent_dna, get_departments",
        done="import _get_agent_dna, get_departments",
        requires=["A2"],
    ),
    dict(
        id="C4", file="studio/cabinet/ui_cabinet.py",
        name="ui_cabinet: агенты на карте — живой скан",
        old="            for dept in DEPARTMENTS:",
        new="            for dept in get_departments():",
        done="            for dept in get_departments():",
        requires=["C3"],
    ),
    dict(
        id="C5", file="studio/cabinet/ui_cabinet.py",
        name="ui_cabinet: матрица — живой скан",
        old="            for dept_info in DEPARTMENTS:",
        new="            for dept_info in get_departments():",
        done="            for dept_info in get_departments():",
        requires=["C1"],
    ),

    # ═══ studio/ui_registry.py (Страница Жизни) ═══════════════
    dict(
        id="R1", file="studio/ui_registry.py",
        name="ui_registry: get_workshop_options() / get_role_options() из манифестов",
        old='''    "living_book":  LIVING_BOOK_ROLE_OPTIONS,
    "trading":      TRADING_ROLE_OPTIONS,
}''',
        new='''    "living_book":  LIVING_BOOK_ROLE_OPTIONS,
    "trading":      TRADING_ROLE_OPTIONS,
}

''' + NEW_REGISTRY_FUNCS,
        done="def get_workshop_options(",
        requires=["M1"],
    ),
    dict(
        id="R2", file="studio/ui_registry.py",
        name="ui_registry: роли и квартал — из манифеста цеха",
        old='''def on_workshop_change(e):
                                    ws = e.value or ""
                                    opts = ROLE_OPTIONS_MAP.get(ws, [""])
                                    new_options = {v: v if v else "— не задана —" for v in opts}
                                    # Автозаполнение квартала по цеху
                                    if agent_quarter_widget["w"] and ws:
                                        auto_q = _WORKSHOP_QUARTER.get(ws, "Квартал Мастеров")''',
        new='''def on_workshop_change(e):
                                    ws = e.value or ""
                                    # ЗАКОН КАРТРИДЖА: роли — из phases манифеста цеха
                                    opts = get_role_options(ws)
                                    new_options = {v: v if v else "— не задана —" for v in opts}
                                    # Автозаполнение квартала: манифест цеха → словарь → дефолт
                                    if agent_quarter_widget["w"] and ws:
                                        from studio.modules_registry import get_cartridge
                                        _cart = get_cartridge(ws)
                                        auto_q = (_cart or {}).get("quarter") or _WORKSHOP_QUARTER.get(ws, "Квартал Мастеров")''',
        done="opts = get_role_options(ws)",
        requires=["R1"],
    ),
    dict(
        id="R3", file="studio/ui_registry.py",
        name="ui_registry: селект цехов — живой скан",
        old='options={v: v if v else "— выбрать цех —" for v in WORKSHOP_OPTIONS},',
        new='options={v: v if v else "— выбрать цех —" for v in get_workshop_options()},',
        done="for v in get_workshop_options()},",
        requires=["R1"],
    ),

    # ═══ studio/cartridge.py ══════════════════════════════════
    dict(
        id="K4", file="studio/cartridge.py",
        name="cartridge: id картриджа = имя папки (статья 1)",
        old='            id=data.get("id", module_id),',
        new='            id=module_id,  # ЗАКОН КАРТРИДЖА: id = имя папки (копия папки = новый цех)',
        done="id=module_id,  # ЗАКОН КАРТРИДЖА",
        requires=[],
    ),
    dict(
        id="K2", file="studio/cartridge.py",
        name="cartridge: докстринг _build_from_legacy",
        old='        """Строит manifest из существующих info.json + DEPT_PIPELINE_CONFIG."""',
        new='        """Строит manifest для папки без manifest.json (info.json + реальные папки)."""',
        done="Строит manifest для папки без manifest.json",
        requires=[],
    ),
    dict(
        id="K3", file="studio/cartridge.py",
        name="cartridge: _build_from_legacy без DEPT_PIPELINE_CONFIG",
        old='''        # Фазы из modules_registry
        phases = {}
        config = DEPT_PIPELINE_CONFIG.get(module_id)
        if config:
            phases = config.get("phases", {})
        else:
            # Дефолт 3×4
            phases = dict(get_dept_workers(module_id))''',
        new='''        # ЗАКОН КАРТРИДЖА: фазы спрашиваем у реестра
        # (он сам читает manifest.json; без манифеста — дефолт 3×4 по папкам)
        phases = dict(get_dept_workers(module_id))''',
        done="фазы спрашиваем у реестра",
        requires=[],
    ),
    dict(
        id="K1", file="studio/cartridge.py",
        name="cartridge: импорт DEPT_PIPELINE_CONFIG убран",
        old='''    get_dept_workers, get_dept_all_workers,
    DEPT_PIPELINE_CONFIG,
)''',
        new='''    get_dept_workers, get_dept_all_workers,
)''',
        done='''    get_dept_workers, get_dept_all_workers,
)''',
        requires=["K3"],
    ),

    # ═══ studio/workshop/ui.py ════════════════════════════════
    dict(
        id="W1", file="studio/workshop/ui.py",
        name="workshop/ui: _dept_runtype() — режим из манифеста для новых цехов",
        old='''    "turbo":        "turbo",
    "living_book":  "living_book",
}''',
        new='''    "turbo":        "turbo",
    "living_book":  "living_book",
}
''' + NEW_RUNTYPE_HELPER,
        done="def _dept_runtype(",
        requires=["M1"],
    ),
    dict(
        id="W2", file="studio/workshop/ui.py",
        name="workshop/ui: state.run_type через _dept_runtype (trading → trading, не social)",
        old='        "run_type": DEPT_TO_RUNTYPE.get(dept, "social"),',
        new='        "run_type": _dept_runtype(dept),  # ЗАКОН КАРТРИДЖА',
        done='"run_type": _dept_runtype(dept),',
        requires=["W1"],
    ),
    dict(
        id="W3", file="studio/workshop/ui.py",
        name="workshop/ui: дефолтный режим Сета через _dept_runtype",
        old='                default_type = DEPT_TO_RUNTYPE.get(dept, "social")',
        new='                default_type = _dept_runtype(dept)',
        done="default_type = _dept_runtype(dept)",
        requires=["W1"],
    ),

    # ═══ studio/modules/trading/manifest.json ═════════════════
    dict(
        id="J1", file="studio/modules/trading/manifest.json",
        name="trading/manifest: quarter + client_facing (Совет — не клиентский цех)",
        old='  "run_type": "trading",',
        new='''  "run_type": "trading",
  "quarter": "Торговый Квартал",
  "client_facing": false,''',
        done='"quarter"',
        requires=[],
        is_json=True,
    ),
]

SMOKE_TEST = r'''
import sys, os
sys.path.insert(0, ".")
# Windows: консоль может не уметь Unicode — переключаем вывод на utf-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from studio.modules_registry import (
    list_cartridges, get_cartridge, get_dept_workers, load_depts,
)
carts = list_cartridges()
ids = [c["id"] for c in carts]
print(f"  found: {len(carts)} cartridges")
print("  ids:", ", ".join(ids))
assert "trading" in ids, "trading not found by scanner!"
t = get_cartridge("trading")
print("  trading phases:", "/".join(t["phases"].keys()),
      "| roles:", len(t["roles"]),
      "| run_type:", t["run_type"],
      "| quarter:", t["quarter"] or "-")
w = get_dept_workers("trading")
print("  get_dept_workers(trading):", {k: len(v) for k, v in w.items()})
assert "SENSORS" in w, "trading phases missing in get_dept_workers!"
lb = get_dept_workers("living_book")
assert "GENESIS" in lb and "DELIVERY" in lb, "living_book lost phases!"
print("  living_book:", "/".join(lb.keys()), "- OK")
depts = load_depts()
print("  reception depts:", ", ".join(d.id for d in depts))
assert all(d.id != "trading" for d in depts), "trading leaked into reception!"
print("  trading hidden from reception - OK")
'''


def main():
    if not Path("main.py").exists() or not Path("studio").exists():
        print("❌ Запускай из корня проекта (там где main.py).")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"cartridge_law_{stamp}"

    # ── читаем файлы ──
    texts: dict[str, str] = {}
    for fx in FIXES:
        f = fx["file"]
        if f in texts:
            continue
        p = Path(f)
        if not p.exists():
            print(f"❌ Файл не найден: {f} — патч остановлен до начала правок.")
            return
        texts[f] = p.read_text(encoding="utf-8")

    # ── применяем правки (зависимости соблюдаются) ──
    status: dict[str, str] = {}      # id → applied | done | missing | blocked
    applied, skipped, problems = [], [], []

    print("═" * 64)
    print("⚖️  ЗАКОН КАРТРИДЖА — применяю правки")
    print("═" * 64)

    for fx in FIXES:
        fid, f, name = fx["id"], fx["file"], fx["name"]
        t = texts[f]

        # зависимость не выполнена → блок
        deps_ok = all(status.get(r) in ("applied", "done") for r in fx["requires"])
        if not deps_ok:
            status[fid] = "blocked"
            problems.append(f"🔒 [{fid}] {name} — пропущена (зависимость не выполнена)")
            print(f"🔒 [{fid}] {name} — заблокирована зависимостью")
            continue

        # ВАЖНО: сначала done-маркер — у вставок старый якорь
        # остаётся в файле, и без этого правка дублировалась бы
        if fx["done"] in t:
            status[fid] = "done"
            skipped.append(fid)
            print(f"⏭  [{fid}] {name} — уже применено")
        elif fx["old"] in t:
            texts[f] = t.replace(fx["old"], fx["new"], 1)
            status[fid] = "applied"
            applied.append(fid)
            print(f"✏️  [{fid}] {name}")
        else:
            status[fid] = "missing"
            problems.append(f"❌ [{fid}] {name} — якорь не найден, файл изменился")
            print(f"❌ [{fid}] {name} — якорь не найден")

    if not applied:
        print("─" * 64)
        if problems:
            print("⚠️  Ничего не применено, есть проблемы:")
            for p in problems:
                print("   " + p)
        else:
            print("✅ Все правки уже применены — закон действует. Патч не нужен.")
        return

    # ── бэкапы и запись ──
    touched = sorted({fx["file"] for fx in FIXES if status.get(fx["id"]) == "applied"})
    backup_dir.mkdir(parents=True, exist_ok=True)
    print("─" * 64)
    for f in touched:
        dst = backup_dir / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        Path(f).write_text(texts[f], encoding="utf-8")
        print(f"📦 бэкап + запись: {f}")
    print(f"📦 Бэкапы: {backup_dir}")

    def rollback(reason: str):
        print(f"⛔ {reason} — откатываю все файлы из бэкапа...")
        for f in touched:
            shutil.copy2(backup_dir / f, f)
        print("↩️  Откат выполнен. Система в исходном состоянии.")

    # ── проверка компиляции ──
    print("─" * 64)
    for f in touched:
        if not f.endswith(".py"):
            continue
        try:
            py_compile.compile(f, doraise=True)
            print(f"✅ компиляция OK: {f}")
        except py_compile.PyCompileError as e:
            rollback(f"Ошибка компиляции {f}: {e}")
            return

    # ── валидация JSON ──
    for f in touched:
        if not f.endswith(".json"):
            continue
        try:
            json.loads(Path(f).read_text(encoding="utf-8"))
            print(f"✅ JSON валиден: {f}")
        except json.JSONDecodeError as e:
            rollback(f"Битый JSON {f}: {e}")
            return

    # ── смоук-тест реестра (только stdlib-модуль, безопасно) ──
    print("─" * 64)
    print("🔬 Смоук-тест сканера:")
    r = subprocess.run([sys.executable, "-c", SMOKE_TEST],
                       capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr)
        rollback("Смоук-тест провален")
        return

    # ── итог ──
    print("═" * 64)
    print(f"⚖️  ЗАКОН КАРТРИДЖА ПРИНЯТ: {len(applied)} правок, "
          f"{len(skipped)} уже было, файлов: {len(touched)}")
    if problems:
        print("⚠️  Требуют внимания:")
        for p in problems:
            print("   " + p)
    print()
    print("Дальше:")
    print("  1. Перезапусти main.py")
    print("  2. Кабинет/карта/матрица/поиск — trading и любой новый цех")
    print("     появляются сами; Страница Жизни даёт роли A01–A09 из манифеста")
    print("  3. Проверка закона: скопируй папку modules/trading → modules/trading_b,")
    print("     обнови Кабинет — цех trading-b появится везде. Удали папку — исчезнет.")
    print("     Город при этом помнит: NFT, хроники, резонанс — снаружи modules/.")


if __name__ == "__main__":
    main()
