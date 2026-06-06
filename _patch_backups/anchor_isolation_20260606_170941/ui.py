# studio/ui_workshop.py - ВЕРСИЯ С КЛИЕНТАМИ, RUNS, MEMORY (REFACTORED)
import json
from datetime import datetime
from pathlib import Path
import asyncio
import re
import shutil
from studio.llm import chat, chat_with_images
from studio.config import KNOWLEDGE_DIR, BASE_DIR
from studio.modules_registry import (
    CURRENT_DEPT, get_worker_prompt, get_worker_info,
    get_worker_knowledge, get_worker_home, format_worker_state,
    get_dept_workers, get_dept_all_workers, DEPT_PIPELINE_CONFIG,
)
from studio.file_processor import FileProcessor
from nicegui import ui, app
app.add_static_files("/assets", "assets")  # ref images
app.add_static_files("/nft_registry", "00_REGISTRY_NFT")
app.add_static_files("/runs", "runs")
app.add_static_files("/clients", "clients")

# Глобальные переменные для API
_current_state = None
_current_run_pipeline = None
_auto_run_requested = False

# --- Вынесенные модули ---
from studio.workshop.styles import IDENTITY_BUREAU_CSS
from studio.workshop.export import _get_viewer_text, _export_docx, _export_pdf
from studio.workshop.utils import (
    _clean_response, _clean_for_export, _validate_asset_ids,
    parse_agent_response, _collect_images_for_vision
)
from studio.workshop.clients import (
    CLIENTS_DIR, RUNS_DIR,
    get_clients_list, load_client_info, save_client_info,
    create_client, get_client_runs, delete_run
)
from studio.workshop.memory import (
    load_client_memory, save_client_memory, append_to_memory,
    delete_memory_run, delete_memory_insight, edit_memory_insight,
    clear_client_memory, save_session_summary,
    format_session_context, format_memory_for_agent
)
from studio.workshop.assets import (
    _load_asset_catalog,
    invalidate_catalog_cache,
    unregister_asset,
)
from studio.workshop.ref_indexer import convert_to_png, index_asset
from studio.cartridge import CartridgeManifest, CartridgeRunner
from studio.residents_manager import (
    get_set_system_prompt,
    build_set_context,
    detect_run_type_from_brief,
)
from studio.workshop.nicegui_callbacks import NiceGUICallbacks

# --- Грондхейм: память города ---
try:
    from studio.grondheim_memory import on_agent_wake, on_agent_done, on_agents_interact
    _GRONDHEIM_ENABLED = True
except ImportError:
    _GRONDHEIM_ENABLED = False


def _grondheim_context_boost(worker_id: str, dept: str) -> str:
    """
    Петля обратной связи Грондхейма.
    Читает dna.json и возвращает инжект в контекст:
      - Stress > 0.6 → «работай аккуратнее, проверяй»
      - streak <= -2 → жёсткое предупреждение
      - streak >= 3  → доверие, смелость
    Возвращает строку для добавления в context (может быть пустой).
    """
    if not _GRONDHEIM_ENABLED:
        return ""
    try:
        from studio.grondheim_memory import _find_agent_dir, _load_json
        agent_dir = _find_agent_dir(worker_id, dept)
        if not agent_dir:
            return ""
        dna = _load_json(agent_dir / "dna.json")
        dynamic = dna.get("dynamic", {})
        if not dynamic:
            return ""

        stress = float(dynamic.get("Stress", 0))
        streak = int(dynamic.get("streak", 0))
        light = float(dynamic.get("Internal_Light", 0.8))
        patience = float(dynamic.get("Patience", 1.0))

        lines = []

        # ── Stress → осторожность ──
        if stress > 0.8:
            lines.append(
                "⚠️ КРИТИЧЕСКИЙ СТРЕСС. Ты на грани. Работай максимально аккуратно. "
                "Никаких экспериментов — только проверенные решения. "
                "Перепроверь КАЖДЫЙ asset_id перед использованием."
            )
        elif stress > 0.6:
            lines.append(
                "⚡ Высокий стресс. Будь внимательнее обычного. "
                "Проверяй ID ассетов, не придумывай лишнего."
            )

        # ── Streak → история побед/провалов ──
        if streak <= -3:
            lines.append(
                f"🔴 СЕРИЯ ПРОВАЛОВ: {abs(streak)} подряд. "
                "Студия следит за тобой. Минимум риска, максимум точности. "
                "НЕ ПРИДУМЫВАЙ asset_id — используй ТОЛЬКО из каталога. "
                "Если не уверен в ID — лучше пропусти чем выдумай."
            )
        elif streak <= -2:
            lines.append(
                f"⚠️ Последние {abs(streak)} задачи были ниже стандарта. "
                "Сосредоточься. Проверяй факты и ID перед отправкой."
            )
        elif streak >= 5:
            lines.append(
                f"🌟 СЕРИЯ ПОБЕД: {streak} подряд! Ты в отличной форме. "
                "Можешь позволить себе смелые креативные решения."
            )
        elif streak >= 3:
            lines.append(
                f"✨ Хорошая серия: {streak} подряд. Ты в ударе — продолжай."
            )

        # ── Patience → терпение ──
        if patience < 0.2:
            lines.append(
                "😤 Терпение на исходе. Не трать слова впустую — коротко и по делу."
            )

        # ── Light → энергия ──
        if light < 0.3:
            lines.append(
                "🌑 Энергия на минимуме. Не пытайся быть блестящим — сделай базу надёжно."
            )
        elif light > 0.9:
            lines.append(
                "☀️ Пик энергии. Твоя креативность сейчас на максимуме — пользуйся этим."
            )

        if not lines:
            return ""

        boost = "=== 🔄 ОБРАТНАЯ СВЯЗЬ СТУДИИ ===\n" + "\n".join(lines) + "\n=== КОНЕЦ ОБРАТНОЙ СВЯЗИ ==="
        print(f"🔄 {worker_id} [{dept}] boost: {'; '.join(lines)[:120]}")
        return boost

    except Exception as e:
        print(f"[GRONDHEIM] boost error {worker_id}: {e}")
        return ""


def _grondheim_temperature(worker_id: str, dept: str) -> float | None:
    """
    Stress → temperature LLM.
    Высокий стресс → низкий temperature (аккуратнее, меньше фантазий).
    Высокий Light → чуть выше (креативнее).
    Возвращает None если Грондхейм выключен (используется дефолт модели).
    """
    if not _GRONDHEIM_ENABLED:
        return None
    try:
        from studio.grondheim_memory import _find_agent_dir, _load_json
        agent_dir = _find_agent_dir(worker_id, dept)
        if not agent_dir:
            return None
        dna = _load_json(agent_dir / "dna.json")
        dynamic = dna.get("dynamic", {})
        if not dynamic:
            return None

        stress = float(dynamic.get("Stress", 0))
        light = float(dynamic.get("Internal_Light", 0.8))

        # Базовый temperature: 0.7
        # Stress тянет вниз: STR=1.0 → temp=0.3
        # Light тянет вверх: LGT=1.0 → +0.1
        temp = 0.7 - stress * 0.4 + (light - 0.5) * 0.2
        temp = round(max(0.2, min(1.0, temp)), 2)

        if temp != 0.7:
            print(f"🌡️ {worker_id} [{dept}] temperature={temp} (STR={stress:.2f} LGT={light:.2f})")
        return temp

    except Exception:
        return None


# ─── Workers & Directories (DYNAMIC) ──────────────────────────────
# WORKERS теперь строится динамически при входе в page_workshop()
# Дефолтные значения — для обратной совместимости
WORKERS = {
    "PRE-PROD": ["A01", "A02", "A03", "A04"],
    "PROD": ["A05", "A06", "A07", "A08"],
    "POST-PROD": ["A09", "A10", "A11", "A12"],
}
ALL_WORKERS = ["SET"] + [w for shop in WORKERS.values() for w in shop]

# --- TURBO mode (5 agents, A02||A03 parallel) ---
TURBO_WORKERS = ["A01", "A02", "A03", "A04", "A05"]
ALL_TURBO = ["SET"] + TURBO_WORKERS


def _build_workers_for_dept(dept: str) -> tuple[dict, list]:
    """Строит WORKERS и ALL_WORKERS для конкретного цеха.
    Для living_book: 5 фаз, 18 агентов (A00-A16 + A00a).
    Для остальных: стандартные 3×4.
    """
    workers_dict = get_dept_workers(dept)
    all_list = ["SET"] + [w for agents in workers_dict.values() for w in agents]
    return workers_dict, all_list

# ─── Режимы работы (цеха) ──────────────────────────────
PIPELINE_MODES = {
    "content_plan": {
        "label": "📝 Контент-план",
        "stop_after": 4,
        "description": "Только стратегия и планирование (A01-A04)"
    },
    "social": {
        "label": "📱 Соцсети",
        "stop_after": None,
        "description": "Полный цикл: от идеи до постинга"
    },
    "pre_prod": {
        "label": "🎬 Pre-Production",
        "stop_after": 4,
        "description": "Концепция, сценарий, раскадровка"
    },
    "full": {
        "label": "🚀 Полный цикл",
        "stop_after": None,
        "checkpoint_at": [3],
        "description": "Все агенты, checkpoint после A03 (сценарий)"
    },
    "bible": {
        "label": "📖 Библия",
        "stop_after": None,
        "description": "Создание вселенной: мир, персонажи, стиль, план сезона (A01-A04 + хард-стоп)"
    },
    "episode": {
        "label": "🎬 Эпизод",
        "stop_after": None,
        "description": "Экранизация серии по готовой Библии (history_dna обязателен)"
    },
    "web_story": {
        "label": "🌐 Web Story",
        "stop_after": None,
        "checkpoint_after": ["A05"],
        "description": "Хард-стоп после Рины (A05), затем PROD A06-A12"
    },
    "living_book": {
        "label": "📖 Живая Книга",
        "stop_after": None,
        "checkpoint_after": ["A00a", "A08", "A15"],
        "revision_loop": True,
        "description": "Полный цикл: Фабула→Вера(ревизия)→18 агентов→Book Package"
    },
}
# ─── Маппинг цеха → режим работы ────────────────────────
DEPT_TO_RUNTYPE = {
    "social_mix":   "social",
    "video_long":   "episode",
    "video_shorts": "social",
    "web_story":    "web_story",
    "market_hit":   "social",
    "logo_design":  "pre_prod",
    "emo_card":     "pre_prod",
    "turbo":        "turbo",
    "living_book":  "living_book",
}

# ─── Названия цехов ─────────────────────────────────────
DEPT_LABELS = {
    "social_mix":   "🗓️ Соцсети",
    "video_long":   "🎥 Видео Long",
    "video_shorts": "⚡ Видео Shorts",
    "web_story":    "🌐 Web Story",
    "market_hit":   "🛒 Маркетплейсы",
    "logo_design":  "🧩 Логотипы",
    "emo_card":     "💌 Открытки",
    "turbo":        "⚡ TURBO Шортсы",
    "living_book":  "📖 Живая Книга",
}
# ─── Очистка ответов ────────────────────────────────────────

def page_workshop(dept: str = 'video_long', prompt: str = '') -> None:
    """Главная страница воркшопа"""
    
    is_turbo = (dept == "turbo")

    # ══ DYNAMIC WORKERS: локальные переменные — не трогаем глобальные ══
    _dept_workers, _all_workers = _build_workers_for_dept(dept)
    print(f"[WORKSHOP] Цех={dept}: {sum(len(v) for v in _dept_workers.values())} агентов, фазы: {list(_dept_workers.keys())}")
    _page_client = ui.context.client

    state = {
        "active_worker": "SET",
        "chat_history": [],
        "master_brief": "",
        "results": {},
        "pipeline_running": False,
        "uploaded_files": [],
        "project_dir": None,
        "settings": {
            "format": "9:16",
            "duration": 15,
            "style": "Stylized 3D Realism",
        },
        "file_processor": None,
        "set_system": "",
        "viewer_content": "",
        # --- Клиент ---
        "current_client": "_sandbox",  # slug текущего клиента
        "run_date": datetime.now().strftime('%Y-%m-%d'),
        "run_type": DEPT_TO_RUNTYPE.get(dept, "social"),
        "active_dept": dept,
        # --- Checkpoint ---
        "paused_at": None,        # worker_id где остановились
        "paused_output": "",      # previous_output для продолжения
        "paused_context": {},     # сохранённый контекст
        # ── Виктор ──
        "victor_ready": False,    # True когда Виктор отработал на ХАРД-СТОПе
        "victor_critique": None,  # dict с критикой от Виктора
    }

    global _current_state
    _current_state = state

    # project_dir — будет создан при запуске пайплайна
    state["project_dir"] = None
    state["file_processor"] = None


    
    # Загружаем промпт SET через Менеджер
    state["set_system"] = get_set_system_prompt(
        dept=dept,
        run_type=state["run_type"],
        settings=state["settings"],
    )

    # Refs
    chat_log_ref = {'element': None}
    viewer_ref = {'element': None}
    files_list_ref = {'element': None}
    status_ref = {'element': None}
    input_ref = {'element': None}
    avatars_ref = {'elements': {}}
    client_select_ref = {'element': None}
    client_badge_ref = {'element': None}
    runs_list_ref = {'element': None}
    
    import studio.modules_registry as _mr; _mr.CURRENT_DEPT = dept
    
    ui.add_head_html(f'<style>{IDENTITY_BUREAU_CSS}</style>')
    # ПАТЧ: JS keep-alive — посылает пустое сообщение каждые 20 сек
    # чтобы WebSocket не закрывался пока агент думает (LLM 30-90 сек)
    ui.add_head_html("""<script>
    (function() {
        var _kaTimer = null;
        function _startKeepalive() {
            if (_kaTimer) return;
            _kaTimer = setInterval(function() {
                try {
                    // NiceGUI использует глобальный socket объект
                    if (window.socket && window.socket.connected) {
                        window.socket.emit('keepalive', {});
                    }
                } catch(e) {}
            }, 20000);
        }
        // Запускаем после загрузки страницы
        if (document.readyState === 'complete') {
            _startKeepalive();
        } else {
            window.addEventListener('load', _startKeepalive);
        }
    })();
    </script>""")

    # ── CSS Виктора ──
    ui.add_head_html("""<style>
    .avatar-victor {
        width: 38px; height: 38px;
        border-radius: 50%;
        border: 1.5px solid rgba(255, 200, 50, 0.55);
        background: rgba(255, 180, 0, 0.10);
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        opacity: 0.75;
        transition: all 0.3s ease;
        font-size: 10px;
        color: rgba(255, 210, 80, 0.9);
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        flex-shrink: 0;
        user-select: none;
    }
    .avatar-victor:hover {
        opacity: 1.0;
        border-color: rgba(255, 200, 50, 0.85);
        background: rgba(255, 180, 0, 0.18);
    }
    .avatar-victor.victor-ready {
        border-color: rgba(255, 180, 0, 0.85);
        background: rgba(255, 180, 0, 0.12);
        opacity: 1;
        cursor: pointer;
        color: rgba(255, 200, 50, 0.95);
        box-shadow: 0 0 12px rgba(255, 180, 0, 0.3);
        animation: victor-pulse 2s ease-in-out infinite;
    }
    .avatar-victor.victor-ready:hover {
        background: rgba(255, 180, 0, 0.22);
        box-shadow: 0 0 20px rgba(255, 180, 0, 0.5);
        transform: scale(1.08);
    }
    @keyframes victor-pulse {
        0%, 100% { box-shadow: 0 0 12px rgba(255, 180, 0, 0.3); }
        50%       { box-shadow: 0 0 22px rgba(255, 180, 0, 0.6); }
    }
    .victor-critique-panel {
        background: rgba(255, 180, 0, 0.04);
        border: 1px solid rgba(255, 180, 0, 0.2);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .victor-critique-title {
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        color: rgba(255, 180, 0, 0.6);
        font-weight: 700;
        margin-bottom: 14px;
        font-family: 'JetBrains Mono', monospace;
    }
    .victor-verdict {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-bottom: 14px;
        font-family: 'JetBrains Mono', monospace;
    }
    .victor-verdict.approved      { background: rgba(0,255,136,0.12); color: #00ff88; border: 1px solid rgba(0,255,136,0.3); }
    .victor-verdict.concerns       { background: rgba(255,180,0,0.12); color: #ffb400; border: 1px solid rgba(255,180,0,0.3); }
    .victor-verdict.rework         { background: rgba(255,80,80,0.12); color: #ff5050; border: 1px solid rgba(255,80,80,0.3); }
    .victor-section-label {
        font-size: 0.62rem;
        color: rgba(255,255,255,0.3);
        letter-spacing: 0.12em;
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 6px;
        margin-top: 12px;
    }
    .victor-section-text {
        color: rgba(220,225,240,0.85);
        font-size: 0.82rem;
        line-height: 1.6;
    }
    .victor-question {
        background: rgba(255,180,0,0.06);
        border-left: 3px solid rgba(255,180,0,0.4);
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        color: rgba(255,200,80,0.9);
        font-size: 0.82rem;
        font-style: italic;
        margin-top: 12px;
        line-height: 1.5;
    }
    </style>""")


    # ── ANTI-STRETCH: JS фиксатор layout ──
    ui.add_head_html("""<script>
    function fixLayout() {
        document.querySelectorAll('.chat-log, .viewer').forEach(el => {
            el.style.overflow = 'auto';
            el.style.minHeight = '0';
            el.style.maxHeight = '100%';
        });
        document.querySelectorAll('.stage-content, .split-view').forEach(el => {
            el.style.overflow = 'hidden';
            el.style.minHeight = '0';
        });
    }
    new MutationObserver(() => requestAnimationFrame(fixLayout))
        .observe(document.body, {childList: true, subtree: true});
    </script>""")

    ui.html('<div id="bg"></div>')
    
    # ─── Функции обновления UI ───────────────────────────

    def remove_uploaded_file(file_info):
        """Removes file from uploaded list and deletes from disk"""
        state["uploaded_files"] = [
            f for f in state["uploaded_files"]
            if f["path"] != file_info["path"]
        ]
        try:
            p = Path(file_info["path"])
            # Файлы из assets/ не удаляем — они индексированы в каталоге
            if p.exists() and "assets" not in p.parts:
                p.unlink()
                print(f"[UPLOAD] Deleted: {file_info['name']}")
                # --- ПАТЧ: удаление из каталога ассетов ---
                from studio.workshop.assets import unregister_asset
                unregister_asset(file_info['name'], state.get("current_client", "_sandbox"))
            else:
                print(f"[UPLOAD] Kept in assets: {file_info['name']}")
        except Exception as ex:
            print(f"[UPLOAD] Delete error: {ex}")
        update_files_display()
        ui.notify(f"Removed: {file_info['name']}", type='info')

    def clear_all_files():
        """Removes all uploaded files"""
        for f in list(state["uploaded_files"]):
            try:
                p = Path(f["path"])
                if p.exists(): p.unlink()
            except: pass
        state["uploaded_files"] = []
        update_files_display()
        ui.notify("All files cleared", type='info')

    def update_chat_display():
        if not chat_log_ref['element']:
            return
        chat_log_ref['element'].clear()
        with chat_log_ref['element']:
            if not state["chat_history"]:
                ui.html('<div class="chat-msg-system">SYSTEM: Ready. Напишите сообщение для начала работы.</div>')
            else:
                for msg in state["chat_history"]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    worker = msg.get('worker', 'SET')
                    
                    if role == "user":
                        ui.html(f'<div class="chat-msg-user"><b>USER:</b> {content}</div>')
                    elif role == "assistant":
                        ui.html(f'<div class="chat-msg-assistant"><b>{worker}:</b> {content}</div>')
            # Автоскролл + фикс layout
            try:
                ui.run_javascript("""
                    requestAnimationFrame(() => {
                        const cl = document.querySelector('.chat-log');
                        if (cl) { cl.scrollTop = cl.scrollHeight; }
                        if (typeof fixLayout === 'function') fixLayout();
                    });
                """)
            except Exception:
                pass
    
    def update_viewer(content: str):
        state["viewer_content"] = content
        if viewer_ref['element']:
            viewer_ref['element'].clear()
            with viewer_ref['element']:
                ui.markdown(content)
    
    def update_files_display():
        if not files_list_ref['element']:
            return
        files_list_ref['element'].clear()
        with files_list_ref['element']:
            if not state["uploaded_files"]:
                ui.label("No files").style('color: rgba(255,255,255,0.4)')
            else:
                for f in state["uploaded_files"]:
                    size_kb = f['size'] // 1024
                    ext = Path(f['name']).suffix.lower()
                    category_icons = {"character": "🎭", "location": "🏔️", "prop": "🔮", "reference": "📌"}
                    with ui.row().classes('uploaded-file'):
                        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            ui.image(f'/files/{Path(f["path"]).name}').style('max-width:40px; max-height:40px; border-radius:4px')
                        ui.label(f'{f["name"]} ({size_kb}KB)').style('flex: 1; overflow: hidden; text-overflow: ellipsis;')
                        ui.button('x', on_click=lambda e, fi=f: remove_uploaded_file(fi)).props(
                            'flat dense round size=xs').style(
                            'color: rgba(255,80,80,0.6); min-width: 22px; height: 22px; font-size: 10px;')
    
    def update_status():
        worker_id = state['active_worker']
        info = get_worker_info(worker_id, state.get("active_dept", ""))
        label = info.get("label", worker_id) if info else worker_id
        
        if status_ref['element']:
            try:
                status_ref['element'].clear()
            except Exception:
                return  # элемент удалён после hot-reload — выходим тихо
            with status_ref['element']:
                ui.html(f'''
                    <div style="position: relative; width: 100%; height: 100%; min-height: 200px;">
                        <img src="/static/avatars/{dept}/{worker_id}.png" 
                            style="width: 100%; height: 100%; object-fit: cover; 
                                    border-radius: 12px; opacity: 0.85;"
                            onerror="this.style.display='none'">
                        <div style="position: absolute; bottom: 0; left: 0; right: 0; 
                                    padding: 15px; background: linear-gradient(transparent, rgba(0,0,0,0.8));
                                    border-radius: 0 0 12px 12px;">
                            <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5); letter-spacing: 0.15em;">ACTIVE AGENT</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #00ff88;">{worker_id}</div>
                            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.8);">{label}</div>
                        </div>
                    </div>
                ''')
    
    def update_avatar_states():
        for worker_id, avatar in avatars_ref['elements'].items():
            avatar.classes(remove='active working done')
            if worker_id == state["active_worker"]:
                avatar.classes(add='active')
            if worker_id in state["results"]:
                avatar.classes(add='done')
    
    def update_client_badge():
        """Обновляет бейдж текущего клиента"""
        if not client_badge_ref['element']:
            return
        client_badge_ref['element'].clear()
        with client_badge_ref['element']:
            slug = state["current_client"]
            if slug == "_sandbox":
                ui.html('<div class="client-badge">🧪 SANDBOX</div>')
            else:
                info = load_client_info(slug)
                name = info.get("name", slug)
                ui.html(f'<div class="client-badge">👤 {name}</div>')
    
    def update_runs_display():
        """Обновляет список run'ов в правой панели"""
        if not runs_list_ref['element']:
            return
        try:
            runs_list_ref['element'].clear()
        except (KeyError, RuntimeError):
            return  # race condition — элемент уже удалён
        with runs_list_ref['element']:
            slug = state["current_client"]
            runs = get_client_runs(slug)
            
            if not runs:
                ui.label("Нет run'ов").style('color: rgba(255,255,255,0.3); font-size: 11px;')
            else:
                for run in runs[:10]:  # последние 10
                    run_name = run["name"]
                    run_path = run["path"]
                    files_count = len(run["files"])
                    
                    with ui.element('div').classes('run-item'):
                        # Кликабельное имя — открывает файлы в viewer
                        ui.label(
                            f'{run_name} ({files_count}📄)'
                        ).classes('run-item-name').on('click', lambda e, rp=run_path, rn=run_name: show_run_files(rp, rn))
                        
                        # Кнопка удаления
                        ui.label('🗑️').classes('run-item-delete').on(
                            'click', lambda e, rp=run_path: confirm_delete_run(rp)
                        )
        
        # Debug — убери когда всё заработает
        slug = state["current_client"]
        runs = get_client_runs(slug)
        print(f"[DEBUG] update_runs_display: client='{slug}', found={len(runs)} runs")
        
        # Принудительное обновление элемента
        if runs_list_ref['element']:
            runs_list_ref['element'].update()
    
    def show_run_files(run_path: str, run_name: str):
        """Показывает файлы run'а в viewer"""
        p = Path(run_path)
        if not p.exists():
            return
        
        content = f"# 📁 {run_name}\n\n"
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix in ['.md', '.txt', '.json']:
                content += f"---\n## {f.name}\n\n"
                try:
                    text = f.read_text(encoding='utf-8')
                    content += text[:500]
                    if len(text) > 500:
                        content += "\n\n*...обрезано...*"
                    content += "\n\n"
                except:
                    content += "*Не удалось прочитать файл*\n\n"
        
        update_viewer(content)
    
    def confirm_delete_run(run_path: str):
        """Удаляет run после подтверждения"""
        with ui.dialog() as dialog, ui.card().style('background: #1a1a2e; border: 1px solid rgba(255,255,255,0.1)'):
            ui.label('Удалить этот run?').style('color: white; font-weight: 700;')
            ui.label(Path(run_path).name).style('color: rgba(255,255,255,0.6); font-size: 12px;')
            with ui.row():
                ui.button('Удалить', on_click=lambda: do_delete(run_path, dialog)).style(
                    'background: rgba(255,80,80,0.3); color: #ff5050; border: 1px solid rgba(255,80,80,0.5)')
                ui.button('Отмена', on_click=dialog.close).style(
                    'background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2)')
        dialog.open()
    
    def do_delete(run_path: str, dialog):
        delete_run(run_path)
        dialog.close()
        update_runs_display()
        ui.notify('🗑️ Run удалён', type='info')
    
    # ─── Memory Manager ────────────────────────────────
    
    def show_memory_dialog():
        """Модалка управления памятью клиента"""
        slug = state["current_client"]
        if slug == "_sandbox":
            ui.notify("🧪 Sandbox не ведёт память", type='warning')
            return
        
        info = load_client_info(slug)
        client_name = info.get("name", slug)
        
        dialog_ref = {'dialog': None}
        
        def _rebuild_memory_content(container):
            """Перестраивает содержимое модалки"""
            container.clear()
            memory = load_client_memory(slug)
            runs = memory.get("runs", [])
            summaries = memory.get("session_summaries", [])
            
            with container:
                # --- Конспекты сессий ---
                if summaries:
                    ui.label('📝 Конспекты сессий').style(
                        'color: #bd00ff; font-weight: 800; font-size: 13px; '
                        'margin-bottom: 8px; letter-spacing: 0.05em;')
                    
                    for si, s in enumerate(summaries):
                        s_date = s.get("date", "?")
                        s_type = s.get("type", "?")
                        s_text = s.get("summary", "")
                        
                        with ui.element('div').style(
                            'background: rgba(189,0,255,0.06); border: 1px solid rgba(189,0,255,0.15); '
                            'border-radius: 12px; padding: 12px; margin-bottom: 8px;'
                        ):
                            with ui.row().style('justify-content: space-between; align-items: center; margin-bottom: 6px;'):
                                ui.label(f'📝 {s_date} / {s_type}').style(
                                    'color: #bd00ff; font-weight: 700; font-size: 12px;')
                                ui.button('🗑️', on_click=lambda e, idx=si: _delete_summary(idx, content_ref)).props(
                                    'flat dense').style('color: rgba(255,80,80,0.5); min-width: 30px;')
                            
                            ui.label(s_text[:300] + ('...' if len(s_text) > 300 else '')).style(
                                'color: rgba(255,255,255,0.55); font-size: 11px; line-height: 1.6;')
                    
                    ui.element('div').style('height: 16px;')  # разделитель
                
                # --- Инсайты по run'ам ---
                if runs:
                    ui.label('💡 Инсайты агентов').style(
                        'color: #00ccff; font-weight: 800; font-size: 13px; '
                        'margin-bottom: 8px; letter-spacing: 0.05em;')
                
                if not runs and not summaries:
                    ui.label("Память пуста").style('color: rgba(255,255,255,0.4); padding: 20px; text-align: center;')
                    return
                
                for ri, run in enumerate(runs):
                    run_date = run.get("date", "?")
                    run_type = run.get("type", "?")
                    insights = run.get("insights", {})
                    
                    with ui.element('div').style(
                        'background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); '
                        'border-radius: 12px; padding: 14px; margin-bottom: 12px;'
                    ):
                        # Заголовок run'а
                        with ui.row().style('justify-content: space-between; align-items: center; margin-bottom: 10px;'):
                            ui.label(f'📅 {run_date} / {run_type}').style(
                                'color: #00ccff; font-weight: 700; font-size: 13px;')
                            ui.button('🗑️ Run', on_click=lambda e, idx=ri: _delete_run(idx, content_ref)).props(
                                'flat dense').style(
                                'color: rgba(255,80,80,0.7); font-size: 11px;')
                        
                        # Инсайты
                        for agent_id, text in insights.items():
                            with ui.element('div').style(
                                'display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; '
                                'border-bottom: 1px solid rgba(255,255,255,0.04);'
                            ):
                                ui.label(agent_id).style(
                                    'color: #00ff88; font-weight: 700; font-size: 11px; '
                                    'min-width: 32px; padding-top: 2px;')
                                ui.label(text).style(
                                    'color: rgba(255,255,255,0.7); font-size: 12px; flex: 1; line-height: 1.5;')
                                ui.button('✏️', on_click=lambda e, idx=ri, aid=agent_id, t=text: _edit_insight(idx, aid, t, content_ref)).props(
                                    'flat dense').style('color: rgba(255,255,255,0.3); min-width: 30px;')
                                ui.button('🗑️', on_click=lambda e, idx=ri, aid=agent_id: _delete_insight(idx, aid, content_ref)).props(
                                    'flat dense').style('color: rgba(255,80,80,0.5); min-width: 30px;')
        
        def _delete_run(run_index, container):
            delete_memory_run(slug, run_index)
            _rebuild_memory_content(container)
            ui.notify('🗑️ Run удалён из памяти', type='info')
        
        def _delete_summary(summary_index, container):
            """Удаляет конспект сессии"""
            memory = load_client_memory(slug)
            summaries = memory.get("session_summaries", [])
            if 0 <= summary_index < len(summaries):
                summaries.pop(summary_index)
                memory["session_summaries"] = summaries
                save_client_memory(slug, memory)
            _rebuild_memory_content(container)
            ui.notify('🗑️ Конспект удалён', type='info')
        
        def _delete_insight(run_index, agent_id, container):
            delete_memory_insight(slug, run_index, agent_id)
            _rebuild_memory_content(container)
            ui.notify(f'🗑️ Insight {agent_id} удалён', type='info')
        
        def _edit_insight(run_index, agent_id, current_text, parent_container):
            with ui.dialog() as edit_dialog, ui.card().style(
                'background: #1a1a2e; border: 1px solid rgba(255,255,255,0.1); min-width: 400px;'
            ):
                ui.label(f'✏️ Редактировать {agent_id}').style('color: white; font-weight: 700; font-size: 14px;')
                edit_input = ui.textarea(value=current_text).style('width: 100%').props('dark autogrow')
                
                with ui.row().style('margin-top: 10px;'):
                    def do_save():
                        new_text = edit_input.value.strip()
                        if new_text:
                            edit_memory_insight(slug, run_index, agent_id, new_text)
                            _rebuild_memory_content(parent_container)
                            ui.notify(f'✅ {agent_id} обновлён', type='positive')
                        edit_dialog.close()
                    
                    ui.button('Сохранить', on_click=do_save).style(
                        'background: rgba(0,255,136,0.2); color: #00ff88; border: 1px solid rgba(0,255,136,0.5)')
                    ui.button('Отмена', on_click=edit_dialog.close).style(
                        'background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2)')
            edit_dialog.open()
        
        def _clear_all(container):
            with ui.dialog() as confirm_dialog, ui.card().style(
                'background: #1a1a2e; border: 1px solid rgba(255,80,80,0.3);'
            ):
                ui.label('💀 Очистить ВСЮ память?').style('color: #ff5050; font-weight: 900; font-size: 16px;')
                ui.label(f'Клиент: {client_name}').style('color: rgba(255,255,255,0.6); font-size: 12px;')
                ui.label('Это действие необратимо!').style('color: rgba(255,255,255,0.4); font-size: 11px; margin-top: 4px;')
                
                with ui.row().style('margin-top: 12px;'):
                    def do_clear():
                        clear_client_memory(slug)
                        confirm_dialog.close()
                        _rebuild_memory_content(container)
                        ui.notify('💀 Память полностью очищена', type='warning')
                    
                    ui.button('💀 Да, очистить', on_click=do_clear).style(
                        'background: rgba(255,80,80,0.3); color: #ff5050; border: 1px solid rgba(255,80,80,0.5)')
                    ui.button('Отмена', on_click=confirm_dialog.close).style(
                        'background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2)')
            confirm_dialog.open()
        
        # === Основная модалка ===
        with ui.dialog() as dialog, ui.card().style(
            'background: #0d1117; border: 1px solid rgba(255,255,255,0.1); '
            'min-width: 550px; max-width: 700px; max-height: 80vh;'
        ):
            dialog_ref['dialog'] = dialog
            
            # Header
            with ui.row().style('justify-content: space-between; align-items: center; width: 100%; margin-bottom: 16px;'):
                ui.label(f'🧠 Память: {client_name}').style(
                    'color: white; font-weight: 900; font-size: 18px;')
                ui.button('✕', on_click=dialog.close).props('flat dense').style(
                    'color: rgba(255,255,255,0.4); min-width: 30px;')
            
            # Счётчик
            memory = load_client_memory(slug)
            total_insights = sum(len(r.get("insights", {})) for r in memory.get("runs", []))
            total_summaries = len(memory.get("session_summaries", []))
            ui.label(f'{len(memory.get("runs", []))} run(s) · {total_insights} insight(s) · {total_summaries} конспект(ов)').style(
                'color: rgba(255,255,255,0.35); font-size: 11px; margin-bottom: 12px;')
            
            # Контент (скроллируемый)
            content_ref = ui.element('div').style('overflow-y: auto; max-height: 50vh; padding-right: 4px;')
            _rebuild_memory_content(content_ref)
            
            # Footer кнопки
            with ui.row().style('margin-top: 16px; justify-content: flex-end; gap: 8px;'):
                ui.button('💀 Очистить всё', on_click=lambda: _clear_all(content_ref)).style(
                    'background: rgba(255,80,80,0.15); color: rgba(255,80,80,0.8); '
                    'border: 1px solid rgba(255,80,80,0.3); font-size: 12px;')
                ui.button('Закрыть', on_click=dialog.close).style(
                    'background: rgba(255,255,255,0.1); color: white; '
                    'border: 1px solid rgba(255,255,255,0.2); font-size: 12px;')
        
        dialog.open()
    
    # ─── Клиентские функции ──────────────────────────────
    
    def on_client_change(e):
        """Обработчик смены клиента"""
        value = e.value
        
        if value is None:
            return
        
        if isinstance(value, dict):
            value = value.get("value", "_sandbox")
        
        value = str(value)
        
        if value == "__new__":
            show_new_client_dialog()
            if client_select_ref['element']:
                client_select_ref['element'].value = state["current_client"]
            return
        
        state["current_client"] = value
        update_client_badge()
        update_runs_display()
        _update_project_dir()
        # --- ПАТЧ: сброс кеша каталога ---
        from studio.workshop.assets import invalidate_catalog_cache
        invalidate_catalog_cache()
        # Перезагрузить каталог ассетов для нового клиента
        try:
            from studio.fal_client import load_client_catalog
            load_client_catalog(value)
        except Exception as _e:
            print(f"⚠️ Каталог ассетов: {_e}")
        
        slug = state["current_client"]
        if slug == "_sandbox":
            ui.notify('🧪 Режим Sandbox', type='info')
        else:
            info = load_client_info(slug)
            ui.notify(f'👤 Клиент: {info.get("name", slug)}', type='positive')
    
    def _update_project_dir(create=False):
        """Обновляет путь project_dir. Создаёт папку только если create=True"""
        slug = state["current_client"]
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Формат: дата_клиент_тип_время (время для уникальности)
        if slug == "_sandbox":
            dir_name = f"{state['run_date']}_sandbox_{state['run_type']}_{timestamp}"
        else:
            dir_name = f"{state['run_date']}_{slug}_{state['run_type']}_{timestamp}"
        
        project_dir = RUNS_DIR / dir_name
        state["project_dir"] = project_dir
        
        if create:
            project_dir.mkdir(parents=True, exist_ok=True)
            assets_dir = project_dir / "assets"
            assets_dir.mkdir(exist_ok=True)
            state["file_processor"] = FileProcessor(assets_dir)
            app.add_static_files('/files', str(assets_dir))
    
    def show_new_client_dialog():
        """Диалог создания нового клиента"""
        new_client = {"name": "", "niche": "", "description": ""}
        
        with ui.dialog() as dialog, ui.card().style(
            'background: #1a1a2e; border: 1px solid rgba(255,255,255,0.1); min-width: 350px;'
        ):
            ui.label('➕ Новый клиент').style('color: white; font-weight: 900; font-size: 16px; margin-bottom: 12px;')
            
            name_input = ui.input('Название клиента / бренда').style('width: 100%').props('dark')
            niche_input = ui.input('Ниша / сфера').style('width: 100%').props('dark')
            desc_input = ui.textarea('Описание (опционально)').style('width: 100%').props('dark')
            
            with ui.row().style('margin-top: 12px'):
                def do_create():
                    name = name_input.value.strip()
                    if not name:
                        ui.notify('Введите название!', type='warning')
                        return
                    
                    slug = create_client(
                        name=name,
                        niche=niche_input.value.strip(),
                        description=desc_input.value.strip()
                    )
                    dialog.close()
                    
                    # Обновляем select
                    _refresh_client_select(slug)
                    
                    state["current_client"] = slug
                    update_client_badge()
                    update_runs_display()
                    _update_project_dir()
                    
                    ui.notify(f'✅ Клиент "{name}" создан!', type='positive')
                
                ui.button('Создать', on_click=do_create).style(
                    'background: rgba(0,255,136,0.2); color: #00ff88; border: 1px solid rgba(0,255,136,0.5)')
                ui.button('Отмена', on_click=dialog.close).style(
                    'background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2)')
        
        dialog.open()
    
    def _refresh_client_select(set_value=None):
        """Обновляет опции в селекте клиентов"""
        if client_select_ref['element']:
            options = _build_client_options()
            client_select_ref['element'].options = options
            client_select_ref['element'].update()
            if set_value:
                client_select_ref['element'].value = set_value
    
    def _build_client_options() -> dict:
        """Строит dict опций для селекта: {value: label}"""
        options = {"_sandbox": "🧪 Sandbox"}
        
        for slug in get_clients_list():
            info = load_client_info(slug)
            name = info.get("name", slug)
            niche = info.get("niche", "")
            label = f"👤 {name}"
            if niche:
                label += f" — {niche}"
            options[slug] = label
        
        options["__new__"] = "➕ Новый клиент..."
        return options
    
    # ─── Основные действия ───────────────────────────────
    
    def switch_worker(worker_id: str):
        state["active_worker"] = worker_id
        update_status()
        update_avatar_states()
        
        if worker_id in state["results"]:
            result = state["results"][worker_id]
            if isinstance(result, dict):
                text = _clean_response(result.get("text", ""))
            else:
                text = result
            
            info = get_worker_info(worker_id, state.get("active_dept", ""))
            label = info.get("label", worker_id) if info else worker_id
            update_viewer(f"# {label} ({worker_id})\n\n{text}")
        else:
            info = get_worker_info(worker_id, state.get("active_dept", ""))
            label = info.get("label", worker_id) if info else worker_id
            update_viewer(f"# {label} ({worker_id})\n\n*Отчёт пока не создан. Запустите пайплайн или напишите агенту напрямую.*")
        
        ui.notify(f'Switched to {worker_id}', type='info')

    def switch_worker_victor():
        """Клик на пузырёк Виктора — показывает его критику в viewer и аватар."""
        state["active_worker"] = "VICTOR"
        update_avatar_states()

        # Аватар Виктора в правой панели
        if status_ref['element']:
            try:
                status_ref['element'].clear()
            except Exception:
                return
            with status_ref['element']:
                ui.html(f'''
                    <div style="position: relative; width: 100%; height: 100%; min-height: 200px;">
                        <img src="/static/avatars/residents/VICTOR.png"
                            style="width: 100%; height: 100%; object-fit: cover;
                                    border-radius: 12px; opacity: 0.85;"
                            onerror="this.style.background='rgba(255,180,0,0.08)'; this.style.display='flex';">
                        <div style="position: absolute; bottom: 0; left: 0; right: 0;
                                    padding: 15px; background: linear-gradient(transparent, rgba(0,0,0,0.85));
                                    border-radius: 0 0 12px 12px;">
                            <div style="font-size: 0.65rem; color: rgba(255,180,0,0.6); letter-spacing: 0.15em;">РЕЗИДЕНТ-КРИТИК</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #ffb400;">VICTOR</div>
                            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.8);">Второй взгляд</div>
                        </div>
                    </div>
                ''')

        # Критика в viewer
        critique = state.get("victor_critique") or {}
        if isinstance(critique, dict):
            _render_victor_critique(critique)
        else:
            update_viewer(f"# ⚡ ВИКТОР\n\n{critique}")

    def _render_victor_critique(critique: dict):
        """Рендерит victor_critique как красивый markdown в viewer."""
        verdict_raw = critique.get("verdict", "")
        strong = critique.get("strong_points", [])
        blind  = critique.get("blind_spots", [])
        question = critique.get("critical_question", "")
        recommendation = critique.get("recommendation", "")

        # Цвет вердикта
        verdict_map = {
            "APPROVED": ("approved", "✅ APPROVED"),
            "APPROVED_WITH_CONCERNS": ("concerns", "⚠️ APPROVED WITH CONCERNS"),
            "NEEDS_REWORK": ("rework", "❌ NEEDS REWORK"),
        }
        verdict_cls, verdict_label = verdict_map.get(
            verdict_raw, ("concerns", verdict_raw or "—")
        )

        strong_md = "\n".join(f"- {s}" for s in strong) if strong else "—"
        blind_md  = "\n".join(f"- {b}" for b in blind)  if blind  else "—"

        md = f"""# ⚡ ВИКТОР — КРИТИКА

<div class="victor-critique-panel">
<div class="victor-critique-title">РЕЗИДЕНТ-КРИТИК · ВТОРОЙ ВЗГЛЯД</div>
<div class="victor-verdict {verdict_cls}">{verdict_label}</div>

<div class="victor-section-label">СИЛЬНЫЕ СТОРОНЫ</div>
<div class="victor-section-text">

{strong_md}

</div>

<div class="victor-section-label">СЛЕПЫЕ ПЯТНА</div>
<div class="victor-section-text">

{blind_md}

</div>

<div class="victor-question">
❓ {question or "—"}
</div>

<div class="victor-section-label">РЕКОМЕНДАЦИЯ</div>
<div class="victor-section-text">{recommendation or "—"}</div>
</div>

> Вердикт Виктора — мнение. Финальное решение за тобой.
"""
        update_viewer(md)

    def update_victor_bubble():
        """Активирует пузырёк Виктора когда state['victor_ready'] == True.
        Вызывать из pipeline после того как Виктор отработал.
        """
        el = avatars_ref['elements'].get('VICTOR')
        if not el:
            return
        if state.get("victor_ready"):
            el.classes(remove='avatar-victor')
            el.classes(add='avatar-victor victor-ready')
            ui.notify('⚡ Виктор готов — посмотри критику', type='warning', timeout=4000)
        else:
            el.classes(remove='victor-ready')


    async def send_message():
        if not input_ref['element']:
            return
        
        msg = input_ref['element'].value.strip()
        if not msg:
            return
        
        input_ref['element'].value = ''
        
        worker_id = state["active_worker"]
        state["chat_history"].append({"role": "user", "content": msg})
        # Изолированная история для ANCHOR — по worker_id
        _wid = state["active_worker"]
        state.setdefault(f"chat_history_{_wid}", []).append(
            {"role": "user", "content": msg}
        )
        update_chat_display()
        
        ui.notify(f'Отправлено к {worker_id}...', type='info')
        
        try:
            if worker_id == "SET":
                system = build_set_context(
                    dept=state["active_dept"],
                    run_type=state["run_type"],
                    settings=state["settings"],
                )
                knowledge = ""
            else:
                system = get_worker_prompt(worker_id, state.get("active_dept", ""))
                knowledge = get_worker_knowledge(worker_id, state.get("active_dept", ""))
            
            # Формируем контекст клиента — добавляем в системный промпт
            client_slug = state["current_client"]
            client_system_ctx = ""
            
            if client_slug != "_sandbox":
                info = load_client_info(client_slug)
                client_system_ctx += f"\n\n=== ТЕКУЩИЙ КЛИЕНТ ===\n"
                client_system_ctx += f"Название: {info.get('name', client_slug)}\n"
                if info.get("niche"):
                    client_system_ctx += f"Ниша: {info['niche']}\n"
                if info.get("description"):
                    client_system_ctx += f"Описание: {info['description']}\n"
            else:
                client_system_ctx += "\n\n=== РЕЖИМ: SANDBOX (без клиента) ==="
            
            # Настройки проекта
            client_system_ctx += f"\n\n=== НАСТРОЙКИ ПРОЕКТА ===\n"
            client_system_ctx += f"Формат: {state['settings']['format']}\n"
            client_system_ctx += f"Длительность: {state['settings']['duration']} сек\n"
            client_system_ctx += f"Стиль: {state['settings']['style']}\n"
            client_system_ctx += f"Тип: {state['run_type']}\n"
            
            system_with_client = system + client_system_ctx
            
            # Память клиента и конспекты — в сообщение
            memory_ctx = format_memory_for_agent(client_slug, worker_id)
            session_ctx = format_session_context(client_slug)
            
            extra_ctx = ""
            if memory_ctx:
                extra_ctx += memory_ctx + "\n\n"
            if session_ctx:
                extra_ctx += session_ctx + "\n\n"
            
            # Добавляем контекст загруженных файлов
            if state["uploaded_files"] and state["file_processor"]:
                try:
                    files_ctx = state["file_processor"].format_for_agent()
                    if files_ctx.strip():
                        extra_ctx += files_ctx + "\n\n"
                        print(f"[CHAT] Файлы переданы агенту: {len(files_ctx)} символов")
                except Exception as ex:
                    print(f"[CHAT FILES ERROR] {ex}")
            
            # Каталог ассетов клиента — чтобы ДЖем знал какие референсы доступны
            try:
                _catalog_ctx = _load_asset_catalog()
                if _catalog_ctx:
                    extra_ctx += _catalog_ctx + "\n\n"
            except Exception as _cat_ex:
                print(f"[CHAT CATALOG] {_cat_ex}")
            
            if extra_ctx:
                msg_with_ctx = f"{extra_ctx}=== СООБЩЕНИЕ ===\n{msg}"
            else:
                msg_with_ctx = msg
            
            # Собираем историю диалога (без последнего — он пойдёт как user msg)
            dialog_history = []
            for m in state["chat_history"][:-1]:  # всё кроме только что добавленного
                role = m.get("role", "user")
                content = m.get("content", "")
                if role in ("user", "assistant") and content:
                    dialog_history.append({"role": role, "content": content})
            
            # Проверяем есть ли изображения для vision
            vision_images = _collect_images_for_vision(state)
            
            if vision_images:
                print(f"[CHAT] Vision режим: {len(vision_images)} изображений")
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: chat_with_images(
                        system_with_client, msg_with_ctx, 
                        images=vision_images,
                        knowledge=knowledge, history=dialog_history
                    )
                )
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: chat(system_with_client, msg_with_ctx, knowledge, history=dialog_history)
                )
            
            state["chat_history"].append({
                "role": "assistant", 
                "content": _clean_response(response), 
                "worker": worker_id
            })
            
            update_chat_display()
                        
        except Exception as e:
            ui.notify(f"Ошибка: {e}", type='negative')
    
    async def build_brief():
        if not state["chat_history"]:
            ui.notify("Сначала обсудите проект!", type='warning')
            return
        
        ui.notify("Собираю бриф...", type='info')
        
        context = "\n".join([f"{m['role']}: {m['content']}" for m in state["chat_history"]])
        
        # Каталог ассетов — чтобы бриф знал про файлы клиента
        _brief_catalog = _load_asset_catalog()
        if _brief_catalog:
            context += f"\n\n{_brief_catalog}\n"

        
        # Добавляем info клиента в контекст брифа
        client_slug = state["current_client"]
        client_info_ctx = ""
        if client_slug != "_sandbox":
            info = load_client_info(client_slug)
            client_info_ctx = f"\n\n=== КЛИЕНТ ===\nНазвание: {info.get('name', '')}\nНиша: {info.get('niche', '')}\nОписание: {info.get('description', '')}"
        
        try:
            brief = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chat(
                    build_set_context(
                        dept=state["active_dept"],
                        run_type=state["run_type"],
                        settings=state["settings"],
                    ),
                    f"Собери MASTER BRIEF на основе диалога:{client_info_ctx}\n\n{context}",
                    ""  # без knowledge
                )
            )
            
            state["master_brief"] = brief

            # ═══ SET AUTO-MODE: контент-план или производство ═══
            # ПАТЧ run_type_lock: не меняем режим если пользователь
            # выбрал его вручную через кнопки ПЛАН/ПОСТ
            if not state.get("run_type_locked", False):
                dept = state.get("active_dept", "social_mix")
                default_type = DEPT_TO_RUNTYPE.get(dept, "social")
                new_run_type = detect_run_type_from_brief(
                    brief=brief,
                    dept=dept,
                    default_run_type=default_type,
                )
                if state["run_type"] != new_run_type:
                    state["run_type"] = new_run_type
                    mode_label = "КОНТЕНТ-ПЛАН (A01-A04)" if new_run_type == "content_plan" else new_run_type
                    print(f"[SET] Режим → {new_run_type}")
                    ui.notify(f"📝 SET: режим {mode_label}", type="info", timeout=5000)
            else:
                print(f"[SET] Режим зафиксирован пользователем: {state['run_type']}")
            # ═════════════════════════════════════════════════════

            update_viewer(f"# MASTER BRIEF\n\n{brief}")
            ui.notify("Бриф готов!", type='positive')
            
        except Exception as e:
            ui.notify(f"Ошибка: {e}", type='negative')
    

    async def run_cartridge_pipeline(from_worker=None, with_chat_context=False):
        """Запуск пайплайна через картриджную систему."""
        global _current_run_pipeline
        _current_run_pipeline = run_cartridge_pipeline

        if not state["master_brief"]:
            ui.notify("Сначала соберите бриф!", type='warning')
            return

        if state["pipeline_running"]:
            ui.notify("Пайплайн уже запущен!", type='warning')
            return

        # Подготовка project_dir
        if not state["project_dir"] or not state["project_dir"].exists():
            _update_project_dir(create=True)
        elif not state["file_processor"]:
            assets_dir = state["project_dir"] / "assets"
            assets_dir.mkdir(exist_ok=True)
            state["file_processor"] = FileProcessor(assets_dir)
            app.add_static_files('/files', str(assets_dir))

        # Загружаем картридж по текущему dept
        manifest = CartridgeManifest.load(dept)

        # Создаём callbacks для NiceGUI
        _client = ui.context.client
        callbacks = NiceGUICallbacks(
            state=state,
            avatars_ref=avatars_ref,
            ui_client=_client,
            update_viewer_fn=update_viewer,
            update_status_fn=update_status,
            update_runs_display_fn=update_runs_display,
        )

        # Запускаем через CartridgeRunner
        runner = CartridgeRunner(manifest, state, callbacks, slot_id=dept)
        await runner.run(from_worker=from_worker, with_chat_context=with_chat_context)

    async def run_cartridge_turbo():
        """TURBO через картриджную систему."""
        if not state["master_brief"]:
            ui.notify("Сначала соберите бриф!", type='warning')
            return

        if state["pipeline_running"]:
            ui.notify("Пайплайн уже запущен!", type='warning')
            return

        # Подготовка project_dir
        if not state["project_dir"] or not state["project_dir"].exists():
            _update_project_dir(create=True)
        elif not state["file_processor"]:
            assets_dir = state["project_dir"] / "assets"
            assets_dir.mkdir(exist_ok=True)
            state["file_processor"] = FileProcessor(assets_dir)
            app.add_static_files('/files', str(assets_dir))

        # Загружаем картридж
        manifest = CartridgeManifest.load(dept)

        # Callbacks
        _client = ui.context.client
        callbacks = NiceGUICallbacks(
            state=state,
            avatars_ref=avatars_ref,
            ui_client=_client,
            update_viewer_fn=update_viewer,
            update_status_fn=update_status,
            update_runs_display_fn=update_runs_display,
        )

        # Запуск TURBO
        runner = CartridgeRunner(manifest, state, callbacks, slot_id=dept)
        await runner.run_turbo()

    # ─── CARTRIDGE CONTINUE ──────────────────────────────
    async def continue_cartridge_pipeline():
        """Продолжить пайплайн после checkpoint (картриджная версия)."""
        if not state["paused_at"]:
            ui.notify("Нет паузы — нечего продолжать!", type="warning")
            return

        resume_from = state["paused_at"]

        # Очищаем checkpoint
        state["paused_at"] = None

        # Пересобираем previous_output из актуальных results
        all_agents_flat = [w for workers in _dept_workers.values() for w in workers]
        rebuilt_output = ""

        for wid in all_agents_flat:
            if wid == resume_from:
                break
            if wid not in state["results"]:
                continue
            res = state["results"][wid]
            text = res.get("text", "") if isinstance(res, dict) else str(res)
            meta = res.get("meta", {}) if isinstance(res, dict) else {}
            info = get_worker_info(wid, state.get("active_dept", ""))
            label = info.get("label", wid) if info else wid
            my_output = meta.get("my_output", {})
            chain_json = ""
            if my_output:
                try:
                    chain_json = f"\n```json\n{json.dumps(my_output, ensure_ascii=False, indent=2)}\n```"
                except Exception:
                    pass
            chunk = meta.get("next_input") or (text[:800] + chain_json)
            rebuilt_output += f"\n\n--- {label} ({wid}) ---\n{chunk}"

        state["paused_output"] = rebuilt_output
        print(f"[CONTINUE] Пересобран previous_output: {len(rebuilt_output)} символов")

        ui.notify(f"▶ Продолжаю с {resume_from}...", type="positive")
        await run_cartridge_pipeline(
            from_worker=resume_from,
            with_chat_context=False
        )
    # --- Буфер для pending-загрузок (до подтверждения категории) ---
    _pending_uploads: list = []

    def handle_upload(e):
        """Перехватывает файл → диалог категории → подпапка → каталог."""
        try:
            if not state["project_dir"] or not state["project_dir"].exists():
                _update_project_dir(create=True)

            # Сохраняем во временный assets/ (потом переместим в подпапку)
            filepath = state["file_processor"].save_file(e.content, e.name)
            print(f"[UPLOAD] Временно: {e.name} → {filepath}")

            # Создаём подпапки категорий
            from studio.workshop.assets import ensure_asset_subfolders
            ensure_asset_subfolders(state["file_processor"].assets_dir)

            show_upload_category_dialog(filepath, e.name)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            ui.notify(f"❌ Ошибка: {ex}", type='negative')

    def show_upload_category_dialog(filepath, filename):
        """Модалка: категория + имя → подпапка → каталог."""
        from pathlib import Path as _P

        ext = _P(filename).suffix.lower()
        is_image = ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        is_doc = ext in {'.pdf', '.docx', '.doc', '.txt', '.md'}
        is_video = ext in {'.mp4', '.mov', '.avi', '.mkv'}
        type_icon = "🖼️" if is_image else "📄" if is_doc else "🎬" if is_video else "📎"
        size_kb = filepath.stat().st_size / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"

        CATEGORIES = {
            "character": {"icon": "🎭", "label": "Персонаж",  "folder": "characters", "color": "#ff6ec7"},
            "location":  {"icon": "🏔️", "label": "Локация",   "folder": "locations",  "color": "#00d4ff"},
            "prop":      {"icon": "🔮", "label": "Реквизит",  "folder": "props",      "color": "#ffa500"},
            "reference": {"icon": "📌", "label": "Референс",  "folder": "references", "color": "#888888"},
        }

        selected = {"category": "reference"}
        suggested_name = _P(filename).stem.replace("_", " ").replace("-", " ").title()

        with ui.dialog() as dialog, ui.card().style(
            'background: #1a1a2e; border: 1px solid rgba(255,255,255,0.15); '
            'min-width: 380px; max-width: 440px; padding: 20px;'
        ):
            ui.label('📂 Категория ассета').style(
                'color: white; font-weight: 900; font-size: 16px; margin-bottom: 4px;'
            )
            ui.label(f'{type_icon} {filename}  •  {size_str}').style(
                'color: rgba(255,255,255,0.5); font-size: 12px; margin-bottom: 6px;'
            )
            folder_preview = ui.label(
                f'📁 assets/references/{filename}'
            ).style(
                'color: rgba(255,255,255,0.35); font-size: 11px; font-family: monospace; '
                'margin-bottom: 14px; padding: 4px 8px; '
                'background: rgba(255,255,255,0.04); border-radius: 4px;'
            )

            cat_buttons = {}
            with ui.element('div').style(
                'display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px;'
            ):
                for cat_id, cat_info in CATEGORIES.items():
                    def make_click(cid=cat_id):
                        def on_click():
                            selected["category"] = cid
                            ci = CATEGORIES[cid]
                            folder_preview.text = f'📁 assets/{ci["folder"]}/{filename}'
                            for bid, btn in cat_buttons.items():
                                c = CATEGORIES[bid]
                                if bid == cid:
                                    btn.style(
                                        f'background: {c["color"]}22; color: {c["color"]}; '
                                        f'border: 2px solid {c["color"]}; border-radius: 8px; '
                                        f'padding: 10px 8px; font-weight: 700; font-size: 13px; cursor: pointer;'
                                    )
                                else:
                                    btn.style(
                                        f'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.5); '
                                        f'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '
                                        f'padding: 10px 8px; font-size: 13px; cursor: pointer;'
                                    )
                        return on_click

                    btn = ui.button(
                        f'{cat_info["icon"]} {cat_info["label"]}',
                        on_click=make_click(cat_id)
                    ).props('flat unelevated').style(
                        'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.5); '
                        'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '
                        'padding: 10px 8px; font-size: 13px; cursor: pointer;'
                    )
                    cat_buttons[cat_id] = btn

            _dc = CATEGORIES["reference"]["color"]
            cat_buttons["reference"].style(
                f'background: {_dc}22; color: {_dc}; border: 2px solid {_dc}; '
                f'border-radius: 8px; padding: 10px 8px; font-weight: 700; font-size: 13px; cursor: pointer;'
            )

            ui.label('Уровень референса').style(
                'font-size: 11px; color: rgba(255,255,255,0.4); '
                'letter-spacing: 0.08em; margin-bottom: 6px;'
            )
            _ref_selected = {'level': 'inspiration'}
            _ref_btns = {}
            _REF_LEVELS = {
                'truth':       ('🔒', 'Truth',       '#ff6ec7', 'бренд клиента — нельзя менять'),
                'orientation': ('🧭', 'Orientation', '#00d4ff', 'рефы от заказчика'),
                'inspiration': ('✨', 'Inspiration', '#ffa500', 'внутренние эталоны студии'),
            }
            with ui.element('div').style(
                'display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 14px;'
            ):
                def _make_ref_click(rid):
                    def _on():
                        _ref_selected['level'] = rid
                        for _bid, _rb in _ref_btns.items():
                            _ic, _lb, _co, _ = _REF_LEVELS[_bid]
                            if _bid == rid:
                                _rb.style(
                                    f'background: {_co}22; color: {_co}; '
                                    f'border: 2px solid {_co}; border-radius: 8px; '
                                    f'padding: 8px 6px; font-weight: 700; font-size: 12px; cursor: pointer;'
                                )
                            else:
                                _rb.style(
                                    'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.45); '
                                    'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '
                                    'padding: 8px 6px; font-size: 12px; cursor: pointer;'
                                )
                    return _on
                for _rid, (_ic, _lb, _co, _hint) in _REF_LEVELS.items():
                    _active = (_rid == 'inspiration')
                    _style = (
                        f'background: {_co}22; color: {_co}; '
                        f'border: 2px solid {_co}; border-radius: 8px; '
                        f'padding: 8px 6px; font-weight: 700; font-size: 12px; cursor: pointer;'
                        if _active else
                        'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.45); '
                        'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '
                        'padding: 8px 6px; font-size: 12px; cursor: pointer;'
                    )
                    _rb = ui.button(f'{_ic} {_lb}', on_click=_make_ref_click(_rid)).props(
                        'flat unelevated'
                    ).style(_style).tooltip(_hint)
                    _ref_btns[_rid] = _rb

            name_input = ui.input('Имя ассета', value=suggested_name).style(
                'width: 100%; margin-bottom: 12px;'
            ).props('dark dense')

            with ui.row().style('justify-content: flex-end; gap: 8px;'):
                def do_confirm():
                    cat = selected["category"]
                    asset_name = name_input.value.strip() or suggested_name
                    cat_info = CATEGORIES[cat]

                    from studio.workshop.assets import register_uploaded_asset
                    registered = register_uploaded_asset(
                        filepath=filepath,
                        category=cat,
                        name=asset_name,
                        client_slug=state.get("current_client", "_sandbox"),
                        move_to_subfolder=True,
                        ref_level=_ref_selected["level"],
                    )

                    final_path = _P(registered['file_path']) if registered else filepath

                    state["uploaded_files"].append({
                        'name': filename,
                        'path': str(final_path),
                        'size': final_path.stat().st_size if final_path.exists() else 0,
                        'category': cat,
                        'asset_id': registered['id'] if registered else None,
                    })
                    update_files_display()
                    dialog.close()

                    if registered:
                        ui.notify(
                            f'{cat_info["icon"]} {asset_name} → {cat_info["folder"]}/',
                            type='positive'
                        )
                        print(f"[UPLOAD] ✅ Финал: {registered['file_path']}")
                    else:
                        ui.notify('⚠️ Сохранён, но не зарегистрирован', type='warning')

                def do_cancel():
                    try:
                        filepath.unlink(missing_ok=True)
                        print(f"[UPLOAD] Отменено: {filename}")
                    except Exception:
                        pass
                    dialog.close()
                    ui.notify(f'Отменено: {filename}', type='info')

                ui.button('Отмена', on_click=do_cancel).props('flat').style(
                    'background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6); '
                    'border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; font-size: 12px;'
                )
                ui.button('✅ Добавить', on_click=do_confirm).props('flat').style(
                    'background: rgba(0,255,136,0.15); color: #00ff88; '
                    'border: 1px solid rgba(0,255,136,0.4); border-radius: 6px; '
                    'font-weight: 700; font-size: 12px;'
                )

        dialog.open()


    def save_chat():
        if not state["chat_history"]:
            ui.notify("Чат пуст!", type='warning')
            return
        
        # Создаём project_dir если ещё нет
        if not state["project_dir"] or not state["project_dir"].exists():
            _update_project_dir(create=True)
        
        # Markdown версия (для чтения)
        chat_file = state["project_dir"] / "chat_history.md"
        content = "# Chat History\n\n"
        for msg in state["chat_history"]:
            role = msg.get('role', 'user').upper()
            worker = msg.get('worker', '')
            text = msg.get('content', '')
            if worker:
                content += f"**{role} ({worker}):** {text}\n\n"
            else:
                content += f"**{role}:** {text}\n\n"
        chat_file.write_text(content, encoding='utf-8')
        
        # JSON версия (для загрузки обратно)
        json_file = state["project_dir"] / "chat_history.json"
        json_file.write_text(
            json.dumps(state["chat_history"], ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        # Сохраняем бриф если есть
        if state["master_brief"]:
            brief_file = state["project_dir"] / "master_brief.md"
            brief_file.write_text(f"# MASTER BRIEF\n\n{state['master_brief']}", encoding='utf-8')
        
        update_runs_display()
        ui.notify(f"✅ Чат сохранён!", type='positive')

    def show_assets_dialog():
        """🗂 Asset Registry — вкладки АССЕТЫ и NFT. v3"""
        import json as _json
        from pathlib import Path as _P

        PAGE_SIZE = 20

        RARITY_COLORS = {
            "Mythic":    "#ff2d78",
            "Legendary": "#ffd166",
            "Epic":      "#bd00ff",
            "Rare":      "#00d4ff",
            "Common":    "#888888",
        }

        CAT_COLORS = {
            "character":       "#ff6ec7",
            "location":        "#00d4ff",
            "prop":            "#ffa500",
            "reference":       "#888888",
            "reference_image": "#888888",
        }
        CAT_LABELS = {
            "character":       "👤 Персонаж",
            "location":        "🏔️ Локация",
            "prop":            "🔮 Реквизит",
            "reference":       "📌 Референс",
            "reference_image": "📌 Референс",
        }

        # ── Загрузить assets_catalog.json ─────────────────
        catalog_path = None
        for cp in [
            _P("assets_catalog.json"),
            BASE_DIR / "assets_catalog.json",
        ]:
            if cp.exists():
                catalog_path = cp
                break

        all_assets = []
        if catalog_path:
            try:
                raw = _json.loads(catalog_path.read_text(encoding="utf-8"))
                all_assets = raw.get("assets", raw) if isinstance(raw, dict) else raw
            except Exception as ex:
                ui.notify(f"Ошибка каталога: {ex}", type="negative")

        # ── Загрузить catalog.json (NFT) ──────────────────
        nft_path = None
        for cp in [
            BASE_DIR / "catalog.json",
            _P("catalog.json"),
            _P("../catalog.json"),
            BASE_DIR.parent / "catalog.json",
        ]:
            if cp.exists():
                nft_path = cp
                break

        all_nft = []
        if nft_path:
            try:
                all_nft = _json.loads(nft_path.read_text(encoding="utf-8"))
            except Exception as ex:
                ui.notify(f"Ошибка NFT каталога: {ex}", type="negative")

        def _nft_img_url(nft_item: dict) -> str:
            raw_path = nft_item.get("_image_path", "")
            if not raw_path:
                return ""
            # Конвертим винтовые слэши
            rel = raw_path.replace("\\", "/")
            # Убираем 00_REGISTRY_NFT/ если есть — отдаём через /nft_registry/
            if rel.startswith("00_REGISTRY_NFT/"):
                rel = rel[len("00_REGISTRY_NFT/"):]
            return f"/nft_registry/{rel}"

        
        def _asset_img_url(asset: dict) -> str:
            fp = asset.get("file_path", "")
            if fp:
                p = _P(fp)
                if p.exists():
                    # Строим URL из абсолютного пути
                    try:
                        rel = p.relative_to(BASE_DIR)
                        # Конвертим \ → /
                        return "/" + str(rel).replace("\\", "/")
                    except ValueError:
                        pass

            fn = asset.get("filename") or asset.get("file_name", "")
            
            if not fn:
                return ""

            # Поиск по подпапкам assets/
            subfolders = {
                "character": "characters", "location": "locations",
                "prop": "props", "reference": "references",
                "reference_image": "references",
            }
            sub = subfolders.get(asset.get("category", ""), "")
            for folder in ([sub] if sub else []) + ["characters", "locations", "props", "references", ""]:
                check = BASE_DIR / "assets" / folder / fn if folder else BASE_DIR / "assets" / fn
                if check.exists():
                    url = f"/assets/{folder}/{fn}" if folder else f"/assets/{fn}"
                    return url

            # Поиск в runs/
            for candidate in (BASE_DIR / "runs").rglob(fn):
                try:
                    rel = candidate.relative_to(BASE_DIR)
                    return "/" + str(rel).replace("\\", "/")
                except ValueError:
                    pass

            return ""

        # ── Состояния фильтров ─────────────────────────────
        sf_assets = {"search": "", "cat": "all", "page": 0}
        sf_nft    = {"search": "", "page": 0}

        # ── Диалог ────────────────────────────────────────
        with ui.dialog() as dialog, ui.card().style(
            'background:#0d1117; border:1px solid rgba(255,255,255,0.1); '
            'min-width:900px; max-width:1100px; max-height:88vh; '
            'padding:0; overflow:hidden; display:flex; flex-direction:column;'
        ):
            # Заголовок
            with ui.element('div').style(
                'padding:14px 18px 0; background:#111827; flex-shrink:0; '
                'border-bottom:1px solid rgba(255,255,255,0.08); width:100%; box-sizing:border-box;'
            ):
                with ui.row().style('justify-content:space-between; align-items:center; width:100%; margin-bottom:10px; box-sizing:border-box;'):
                    with ui.row().style('gap:10px; align-items:center;'):
                        ui.label('🗂 Asset Registry').style(
                            'color:white; font-weight:900; font-size:15px;')
                        assets_total_lbl = ui.label(f'{len(all_assets)} ассетов').style(
                            'color:rgba(255,255,255,0.3); font-size:11px; '
                            'background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:10px;')
                        ui.label(f'{len(all_nft)} NFT').style(
                            'color:rgba(255,45,120,0.7); font-size:11px; '
                            'background:rgba(255,45,120,0.08); padding:2px 8px; border-radius:10px; '
                            'border:1px solid rgba(255,45,120,0.2);')
                    ui.button('✕', on_click=dialog.close).props('flat dense').style(
                        'color:rgba(255,255,255,0.4); min-width:28px;')

                # Вкладки
                with ui.tabs() as tabs:
                    tab_assets = ui.tab('АССЕТЫ').style(
                        'color:rgba(255,255,255,0.7); font-size:12px; font-weight:700; letter-spacing:1px;')
                    tab_nft = ui.tab('💎 NFT').style(
                        'color:rgba(255,45,120,0.8); font-size:12px; font-weight:700; letter-spacing:1px;')

            # ══════════════════════════════════════════════
            # ПАНЕЛИ ВКЛАДОК
            # ══════════════════════════════════════════════
            with ui.tab_panels(tabs, value=tab_assets).style(
                'background:transparent; flex:1; overflow:hidden; display:flex; flex-direction:column; width:100%;'
            ):

                # ─────────────────────────────────────────
                # ВКЛАДКА: АССЕТЫ
                # ─────────────────────────────────────────
                with ui.tab_panel(tab_assets).style(
                    'padding:0; display:flex; flex-direction:column; height:100%; width:100%;'
                ):
                    # Тулбар
                    with ui.element('div').style(
                        'padding:10px 18px 6px; border-bottom:1px solid rgba(255,255,255,0.05); '
                        'flex-shrink:0; display:flex; gap:8px; align-items:center; flex-wrap:wrap; width:100%;'
                    ):
                        a_search = ui.input(placeholder='🔍  Поиск...').props('dense outlined dark').style(
                            'flex:1; min-width:180px; width:100%;')
                        a_result_lbl = ui.label('').style('color:rgba(255,255,255,0.25); font-size:11px;')

                    # Кнопки категорий
                    with ui.element('div').style(
                        'padding:6px 18px 8px; border-bottom:1px solid rgba(255,255,255,0.04); '
                        'display:flex; gap:6px; flex-shrink:0; width:100%;'
                    ):
                        a_cat_btns = {}
                        CATS = [("all","Все"),("character","👤"),("location","🏔️"),("prop","🔮"),("reference","📌")]

                        def _make_acat(cat_id):
                            def on_click():
                                sf_assets["cat"] = cat_id
                                sf_assets["page"] = 0
                                for bid, cb in a_cat_btns.items():
                                    c = CAT_COLORS.get(bid, "#ffffff")
                                    if bid == cat_id:
                                        cb.style(f'background:{c}22; border:1px solid {c}88; color:{c}; '
                                                 f'border-radius:6px; padding:4px 10px; font-size:12px; font-weight:700;')
                                    else:
                                        cb.style('background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); '
                                                 'color:rgba(255,255,255,0.45); border-radius:6px; padding:4px 10px; font-size:12px;')
                                refresh_assets()
                            return on_click

                        for cid, clabel in CATS:
                            b = ui.button(clabel, on_click=_make_acat(cid)).props('flat dense').style(
                                'background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); '
                                'color:rgba(255,255,255,0.45); border-radius:6px; padding:4px 10px; font-size:12px;')
                            a_cat_btns[cid] = b

                    # Список ассетов
                    a_list = ui.element('div').style('overflow-y:auto; flex:1; padding:8px 18px 8px; display:grid; grid-template-columns:1fr 1fr; gap:6px; align-content:start;')

                    # Пагинация
                    with ui.element('div').style(
                        'padding:7px 18px; border-top:1px solid rgba(255,255,255,0.05); '
                        'display:flex; gap:8px; align-items:center; justify-content:center; flex-shrink:0;'
                    ):
                        a_prev = ui.button('← Назад', on_click=lambda: _apage(-1)).props('flat dense').style(
                            'color:rgba(255,255,255,0.35); font-size:11px;')
                        a_page_lbl = ui.label('').style(
                            'color:rgba(255,255,255,0.25); font-size:11px; min-width:80px; text-align:center;')
                        a_next = ui.button('Вперёд →', on_click=lambda: _apage(1)).props('flat dense').style(
                            'color:rgba(255,255,255,0.35); font-size:11px;')

                    def _apage(d):
                        flt = _afilt()
                        tp = max(1, (len(flt) + PAGE_SIZE - 1) // PAGE_SIZE)
                        sf_assets["page"] = max(0, min(sf_assets["page"] + d, tp - 1))
                        refresh_assets()

                    def _afilt():
                        q = sf_assets["search"].lower()
                        c = sf_assets["cat"]
                        res = []
                        for a in all_assets:
                            if c != "all":
                                ac = a.get("category", "")
                                if not (ac == c or (c == "reference" and "reference" in ac)):
                                    continue
                            if q:
                                hay = (a.get("name","") + " " + a.get("id","") + " " +
                                       " ".join(a.get("tags",[]))).lower()
                                if q not in hay:
                                    continue
                            res.append(a)
                        return res

                    def refresh_assets():
                        a_list.clear()
                        flt = _afilt()
                        tp = max(1, (len(flt) + PAGE_SIZE - 1) // PAGE_SIZE)
                        p = sf_assets["page"]
                        chunk = flt[p * PAGE_SIZE:(p + 1) * PAGE_SIZE]
                        a_result_lbl.text = f'{len(flt)} из {len(all_assets)}'
                        a_page_lbl.text = f'стр. {p+1} / {tp}'
                        a_prev.set_enabled(p > 0)
                        a_next.set_enabled(p < tp - 1)
                        with a_list:
                            if not chunk:
                                ui.label('Ничего не найдено').style(
                                    'color:rgba(255,255,255,0.2); text-align:center; padding:40px; font-size:13px;')
                                return
                            for asset in chunk:
                                _render_asset(asset)

                    def _render_asset(asset):
                        aid   = asset.get("id", "?")
                        cat   = asset.get("category", "reference")
                        color = CAT_COLORS.get(cat, "#888")
                        img_url = _asset_img_url(asset)
                        with ui.element('div').style(
                            'display:flex; align-items:center; gap:10px; padding:10px 12px; '
                            'border-radius:7px; '
                            'background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06);'
                        ):
                            if img_url:
                                ui.image(img_url).style(
                                    'width:40px; height:40px; object-fit:contain; '
                                    'border-radius:4px; flex-shrink:0; background:#000;')
                            else:
                                ui.element('div').style(
                                    f'width:40px; height:40px; border-radius:4px; flex-shrink:0; '
                                    f'background:{color}15; border:1px solid {color}33;')

                            with ui.element('div').style('flex:1; min-width:0; overflow:hidden;'):
                                with ui.row().style('gap:5px; align-items:center; margin-bottom:2px;'):
                                    ui.label(aid).style(
                                        'color:rgba(255,255,255,0.22); font-size:9px; font-family:monospace;')
                                    ui.label(CAT_LABELS.get(cat, cat)).style(
                                        f'color:{color}; font-size:9px; font-weight:700; '
                                        f'background:{color}18; padding:1px 5px; border-radius:3px;')
                                name_input = ui.input(value=asset.get("name", aid)).props(
                                    'dense borderless dark').style(
                                    'color:rgba(255,255,255,0.85); font-size:13px; font-weight:600; width:100%;')

                            def _save_asset(a=asset, ni=name_input):
                                new = ni.value.strip()
                                if not new or new == a.get("name"):
                                    return
                                try:
                                    data = _json.loads(catalog_path.read_text(encoding="utf-8"))
                                    lst = data.get("assets", data) if isinstance(data, dict) else data
                                    for item in lst:
                                        if item.get("id") == a["id"]:
                                            item["name"] = new
                                            break
                                    if isinstance(data, dict):
                                        data["assets"] = lst
                                    else:
                                        data = lst
                                    catalog_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                                    a["name"] = new
                                    invalidate_catalog_cache()
                                    ui.notify(f'✓ «{new}» сохранено', type='positive')
                                except Exception as ex:
                                    ui.notify(f'Ошибка: {ex}', type='negative')

                            ui.button('✓', on_click=_save_asset).props('flat dense').style(
                                'color:rgba(0,204,255,0.55); min-width:26px;').tooltip('Сохранить имя')

                            def _ask_del_asset(a=asset):
                                with ui.dialog() as cd, ui.card().style(
                                    'background:#1a1a2e; border:1px solid rgba(255,60,60,0.3); padding:20px; min-width:300px;'
                                ):
                                    ui.label('🗑 Удалить?').style('color:white; font-weight:900; font-size:14px; margin-bottom:6px;')
                                    ui.label(f'«{a.get("name", a["id"])}»').style('color:rgba(255,255,255,0.6); font-size:13px; margin-bottom:4px;')
                                    ui.label('Файл картинки тоже удалится с диска').style(
                                        'color:rgba(255,100,100,0.65); font-size:11px; margin-bottom:14px;')
                                    with ui.row().style('gap:8px; justify-content:flex-end;'):
                                        ui.button('Отмена', on_click=cd.close).props('flat').style('color:rgba(255,255,255,0.4);')
                                        def _do_del(a=a, dlg=cd):
                                            for key in ("file_path", "filename", "file_name"):
                                                fp = a.get(key, "")
                                                if not fp:
                                                    continue
                                                p = _P(fp)
                                                if not p.is_absolute():
                                                    p = _P("assets") / p.name
                                                if p.exists():
                                                    try:
                                                        p.unlink()
                                                    except Exception:
                                                        pass
                                                break
                                            try:
                                                data = _json.loads(catalog_path.read_text(encoding="utf-8"))
                                                if isinstance(data, dict):
                                                    data["assets"] = [x for x in data.get("assets",[]) if x.get("id") != a["id"]]
                                                    data["total_assets"] = len(data["assets"])
                                                else:
                                                    data = [x for x in data if x.get("id") != a["id"]]
                                                catalog_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                                                invalidate_catalog_cache()
                                            except Exception as ex:
                                                ui.notify(f'Ошибка: {ex}', type='negative')
                                                dlg.close()
                                                return
                                            all_assets[:] = [x for x in all_assets if x.get("id") != a["id"]]
                                            assets_total_lbl.text = f'{len(all_assets)} ассетов'
                                            dlg.close()
                                            refresh_assets()
                                            ui.notify(f'✓ «{a.get("name", a["id"])}» удалён', type='positive')
                                        ui.button('Удалить', on_click=_do_del).props('flat').style(
                                            'background:rgba(255,60,60,0.2); color:#ff4444; '
                                            'border:1px solid rgba(255,60,60,0.4); border-radius:6px; '
                                            'padding:5px 14px; font-weight:700;')
                                cd.open()

                            ui.button('✕', on_click=_ask_del_asset).props('flat dense').style(
                                'color:rgba(255,60,60,0.4); min-width:26px;').tooltip('Удалить')

                    def _on_asearch(e):
                        sf_assets["search"] = e.value if hasattr(e, 'value') else a_search.value
                        sf_assets["page"] = 0
                        refresh_assets()
                    a_search.on('keyup', _on_asearch)

                    # Активировать "Все"
                    a_cat_btns["all"].style(
                        'background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.4); '
                        'color:white; border-radius:6px; padding:4px 10px; font-size:12px; font-weight:700;')
                    refresh_assets()

                # ─────────────────────────────────────────
                # ВКЛАДКА: NFT
                # ─────────────────────────────────────────
                with ui.tab_panel(tab_nft).style(
                    'padding:0; display:flex; flex-direction:column; height:100%;'
                ):
                    # Поиск
                    with ui.element('div').style(
                        'padding:10px 18px 8px; border-bottom:1px solid rgba(255,255,255,0.05); '
                        'flex-shrink:0; display:flex; gap:8px; align-items:center;'
                    ):
                        n_search = ui.input(placeholder='🔍  Поиск по имени, ID, рангу...').props('dense outlined dark').style(
                            'flex:1;')
                        n_result_lbl = ui.label('').style('color:rgba(255,255,255,0.25); font-size:11px;')

                    # Список NFT
                    n_list = ui.element('div').style('overflow-y:auto; flex:1; padding:10px 18px 8px;')

                    # Пагинация NFT
                    with ui.element('div').style(
                        'padding:7px 18px; border-top:1px solid rgba(255,255,255,0.05); '
                        'display:flex; gap:8px; align-items:center; justify-content:center; flex-shrink:0;'
                    ):
                        n_prev = ui.button('← Назад', on_click=lambda: _npage(-1)).props('flat dense').style(
                            'color:rgba(255,255,255,0.35); font-size:11px;')
                        n_page_lbl = ui.label('').style(
                            'color:rgba(255,255,255,0.25); font-size:11px; min-width:80px; text-align:center;')
                        n_next = ui.button('Вперёд →', on_click=lambda: _npage(1)).props('flat dense').style(
                            'color:rgba(255,255,255,0.35); font-size:11px;')

                    def _npage(d):
                        flt = _nfilt()
                        tp = max(1, (len(flt) + PAGE_SIZE - 1) // PAGE_SIZE)
                        sf_nft["page"] = max(0, min(sf_nft["page"] + d, tp - 1))
                        refresh_nft()

                    def _nfilt():
                        q = sf_nft["search"].lower()
                        if not q:
                            return list(all_nft)
                        res = []
                        for n in all_nft:
                            hay = (
                                n.get("Official_Name", "") + " " +
                                n.get("ID_Object", "") + " " +
                                n.get("Social_Rank", "") + " " +
                                n.get("Profession", "") + " " +
                                n.get("Rarity", "")
                            ).lower()
                            if q in hay:
                                res.append(n)
                        return res

                    def refresh_nft():
                        n_list.clear()
                        flt = _nfilt()
                        tp = max(1, (len(flt) + PAGE_SIZE - 1) // PAGE_SIZE)
                        p = sf_nft["page"]
                        chunk = flt[p * PAGE_SIZE:(p + 1) * PAGE_SIZE]
                        n_result_lbl.text = f'{len(flt)} из {len(all_nft)}'
                        n_page_lbl.text = f'стр. {p+1} / {tp}'
                        n_prev.set_enabled(p > 0)
                        n_next.set_enabled(p < tp - 1)
                        with n_list:
                            if not chunk:
                                ui.label('Ничего не найдено').style(
                                    'color:rgba(255,255,255,0.2); text-align:center; padding:40px; font-size:13px;')
                                return
                            for nft in chunk:
                                _render_nft(nft)

                    def _render_nft(nft):
                        nid      = nft.get("ID_Object", "?")
                        name     = nft.get("Official_Name", nid)
                        rarity   = nft.get("Rarity", "Common")
                        rank     = nft.get("Social_Rank", "")
                        prof     = nft.get("Profession", "")
                        access   = nft.get("Access_Level", "")
                        r_color  = RARITY_COLORS.get(rarity, "#888")
                        img_url  = _nft_img_url(nft)

                        with ui.element('div').style(
                            'display:flex; align-items:center; gap:12px; padding:10px 12px; '
                            'border-radius:8px; margin-bottom:6px; '
                            f'background:rgba(255,255,255,0.02); '
                            f'border:1px solid {r_color}25; '
                            f'border-left:3px solid {r_color};'
                        ):
                            # Превью
                            if img_url:
                                ui.image(img_url).style(
                                    'width:52px; height:52px; object-fit:contain; '
                                    'border-radius:6px; flex-shrink:0; background:#000;')
                            else:
                                ui.element('div').style(
                                    f'width:52px; height:52px; border-radius:6px; flex-shrink:0; '
                                    f'background:{r_color}10; border:1px solid {r_color}30; '
                                    f'display:flex; align-items:center; justify-content:center; '
                                    f'font-size:22px;')

                            # Инфо
                            with ui.element('div').style('flex:1; min-width:0;'):
                                with ui.row().style('gap:6px; align-items:center; margin-bottom:4px; flex-wrap:wrap;'):
                                    ui.label(nid).style(
                                        'color:rgba(255,255,255,0.25); font-size:9px; font-family:monospace;')
                                    ui.label(rarity).style(
                                        f'color:{r_color}; font-size:9px; font-weight:700; '
                                        f'background:{r_color}18; padding:1px 6px; border-radius:3px;')
                                    if access:
                                        ui.label(f'LVL {access}').style(
                                            'color:rgba(255,255,255,0.3); font-size:9px; '
                                            'background:rgba(255,255,255,0.05); padding:1px 5px; border-radius:3px;')

                                ui.label(name).style(
                                    'color:white; font-size:14px; font-weight:700; margin-bottom:2px;')

                                with ui.row().style('gap:12px; flex-wrap:wrap;'):
                                    if rank:
                                        ui.label(f'🎖 {rank}').style(
                                            'color:rgba(255,255,255,0.45); font-size:11px;')
                                    if prof:
                                        ui.label(f'💼 {prof}').style(
                                            'color:rgba(255,255,255,0.35); font-size:11px;')

                            # NFT — только просмотр, нет удаления
                            ui.label('🔐').style(
                                'color:rgba(255,255,255,0.15); font-size:16px; '
                                'flex-shrink:0;').tooltip('NFT объект защищён от удаления')

                    def _on_nsearch(e):
                        sf_nft["search"] = e.value
                        sf_nft["page"] = 0
                        refresh_nft()
                    n_search.on('input', _on_nsearch)
                    refresh_nft()

        dialog.open()

    def show_load_dialog():
        """Модалка загрузки сохранённого чата"""
        slug = state["current_client"]
        
        # Ищем все папки run'ов с chat_history.json
        saved_chats = []
        if RUNS_DIR.exists():
            # Паттерн поиска
            if slug == "_sandbox":
                search_key = "_sandbox_"
            else:
                search_key = f"_{slug}_"
            
            for p in sorted(RUNS_DIR.iterdir(), reverse=True):
                if not p.is_dir() or p.name.startswith("_"):
                    continue
                
                json_file = p / "chat_history.json"
                md_file = p / "chat_history.md"
                
                # Ищем по клиенту ИЛИ показываем все если sandbox
                if search_key in p.name or slug == "_sandbox":
                    if json_file.exists() or md_file.exists():
                        # Считаем сообщения
                        msg_count = 0
                        has_json = json_file.exists()
                        if has_json:
                            try:
                                msgs = json.loads(json_file.read_text(encoding='utf-8'))
                                msg_count = len(msgs)
                            except:
                                pass
                        
                        # Проверяем есть ли бриф
                        has_brief = (p / "master_brief.md").exists()
                        
                        saved_chats.append({
                            "name": p.name,
                            "path": str(p),
                            "has_json": has_json,
                            "msg_count": msg_count,
                            "has_brief": has_brief,
                        })
        
        if not saved_chats:
            ui.notify("Нет сохранённых чатов для этого клиента", type='warning')
            return
        
        def _load_chat(chat_info, dialog):
            """Загружает чат из папки"""
            p = Path(chat_info["path"])
            json_file = p / "chat_history.json"
            md_file = p / "chat_history.md"
            
            loaded = False
            
            # Вариант 1: JSON (точная загрузка)
            if chat_info["has_json"] and json_file.exists():
                try:
                    msgs = json.loads(json_file.read_text(encoding='utf-8'))
                    state["chat_history"] = msgs
                    loaded = True
                except:
                    pass
            
            # Вариант 2: парсим .md (для старых чатов)
            if not loaded and md_file.exists():
                try:
                    md_text = md_file.read_text(encoding='utf-8')
                    parsed_msgs = []
                    
                    for line in md_text.split('\n'):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # Формат: **USER:** текст  или  **ASSISTANT (SET):** текст
                        if line.startswith('**USER'):
                            # Убираем **USER:** или **USER (SET):**
                            text = re.sub(r'^\*\*USER[^*]*\*\*:?\s*', '', line).strip()
                            if text:
                                parsed_msgs.append({"role": "user", "content": text})
                        elif line.startswith('**ASSISTANT'):
                            # Извлекаем worker
                            worker_match = re.search(r'\((\w+)\)', line)
                            worker = worker_match.group(1) if worker_match else "SET"
                            text = re.sub(r'^\*\*ASSISTANT[^*]*\*\*:?\s*', '', line).strip()
                            if text:
                                parsed_msgs.append({"role": "assistant", "content": text, "worker": worker})
                    
                    if parsed_msgs:
                        state["chat_history"] = parsed_msgs
                        loaded = True
                except:
                    pass
            
            if loaded:
                # Загружаем бриф если есть
                brief_file = p / "master_brief.md"
                if brief_file.exists():
                    brief_text = brief_file.read_text(encoding='utf-8')
                    brief_text = brief_text.replace("# MASTER BRIEF\n\n", "").strip()
                    state["master_brief"] = brief_text
                
                # Привязываем project_dir к этой папке
                state["project_dir"] = p
                assets_dir = p / "assets"
                if assets_dir.exists():
                    state["file_processor"] = FileProcessor(assets_dir)
                    app.add_static_files('/files', str(assets_dir))
                
                update_chat_display()
                dialog.close()
                
                msg_count = len(state["chat_history"])
                ui.notify(f"✅ Загружено в чат: {msg_count} сообщений", type='positive')
                
                # Показываем бриф в viewer если есть
                if state["master_brief"]:
                    update_viewer(f"# MASTER BRIEF\n\n{state['master_brief']}")
                else:
                    update_viewer("# 💬 Чат загружен\n\nМожете продолжить диалог или собрать BRIEF.")
            else:
                # Совсем не удалось — хотя бы покажем .md в viewer
                if md_file.exists():
                    update_viewer(md_file.read_text(encoding='utf-8'))
                dialog.close()
                ui.notify("⚠️ Не удалось загрузить чат", type='warning')
        
        # === Модалка ===
        with ui.dialog() as dialog, ui.card().style(
            'background: #0d1117; border: 1px solid rgba(255,255,255,0.1); '
            'min-width: 450px; max-width: 600px; max-height: 70vh;'
        ):
            with ui.row().style('justify-content: space-between; align-items: center; width: 100%; margin-bottom: 12px;'):
                ui.label('📂 Загрузить чат').style('color: white; font-weight: 900; font-size: 16px;')
                ui.button('✕', on_click=dialog.close).props('flat dense').style(
                    'color: rgba(255,255,255,0.4); min-width: 30px;')
            
            ui.label(f'{len(saved_chats)} сохранённых сессий').style(
                'color: rgba(255,255,255,0.35); font-size: 11px; margin-bottom: 12px;')
            
            with ui.element('div').style('overflow-y: auto; max-height: 50vh;'):
                for chat_info in saved_chats:
                    with ui.element('div').style(
                        'background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); '
                        'border-radius: 10px; padding: 12px; margin-bottom: 8px; cursor: pointer; '
                        'transition: all 0.2s;'
                    ).on('click', lambda e, ci=chat_info: _load_chat(ci, dialog)):
                        with ui.row().style('justify-content: space-between; align-items: center;'):
                            ui.label(chat_info["name"]).style(
                                'color: rgba(255,255,255,0.8); font-size: 12px; '
                                'font-family: "JetBrains Mono", monospace;')
                            with ui.row().style('gap: 6px;'):
                                if chat_info["has_json"]:
                                    ui.label(f'💬 {chat_info["msg_count"]}').style(
                                        'color: #00ccff; font-size: 10px; font-weight: 700;')
                                if chat_info["has_brief"]:
                                    ui.label('📋').style('font-size: 12px;').tooltip('Есть бриф')
                                if not chat_info["has_json"]:
                                    ui.label('📄 только .md').style(
                                        'color: rgba(255,255,255,0.3); font-size: 10px;')
        
        dialog.open()

    def clear_chat():
        state["chat_history"] = []
        update_chat_display()
        ui.notify("🗑️ Чат очищен", type='info')
            
    
    # ═══ LAYOUT ══════════════════════════════════════════
    with ui.element('div').classes('app-container'):
        
        # ─── HEADER ──────────────────────────────────────
        with ui.element('div').classes('area-header'):
            with ui.element('div').classes('glass squad-deck').style(
                'display:flex; align-items:center; width:100%; gap:8px; padding:0 8px; position:relative;'
            ):
                # ── Заглушка слева — симметрия с Виктором справа ──
                _victor_depts = ["video_long", "video_shorts"]
                _has_victor = dept in _victor_depts
                if _has_victor:
                    ui.element('div').style('width:38px; flex-shrink:0;')

                # ── Агенты — центр ──
                with ui.element('div').style(
                    'display:flex; align-items:center; gap:6px; flex-wrap:wrap; '
                    'justify-content:center; flex:1;'
                ):
                    _avatar_list = ALL_TURBO if is_turbo else _all_workers
                    for worker_id in _avatar_list:
                        avatar = ui.element('div').classes(f'avatar {"active" if worker_id == "SET" else ""}')
                        avatar.on('click', lambda e, w=worker_id: switch_worker(w))
                        with avatar:
                            ui.label(worker_id).style('font-size: 10px')
                        avatars_ref['elements'][worker_id] = avatar

                # ── Виктор — правый угол ──
                if _has_victor:
                    _victor_el = ui.element('div').classes('avatar-victor').style('flex-shrink:0;')
                    _victor_el.on('click', lambda e, v='VICTOR': switch_worker_victor())
                    with _victor_el:
                        ui.label('⚡V').style('font-size:10px;')
                    avatars_ref['elements']['VICTOR'] = _victor_el

        
        # ─── LEFT PANEL ─────────────────────────────────
        with ui.element('div').classes('area-left'):
            with ui.element('div').classes('left-col'):
                
                # --- CLIENT SELECTOR ---
                with ui.element('div').classes('glass client-panel'):
                    ui.html('<div class="panel-title">👤 CLIENT</div>')
                    with ui.element('div').classes('panel-body'):
                        client_options = _build_client_options()
                        client_select_ref['element'] = ui.select(
                            options=client_options,
                            value='_sandbox',
                            on_change=on_client_change
                        ).style('width: 100%').props('dark dense options-dense')
                        
                        with ui.row().style('margin-top: 8px; gap: 6px; align-items: center;'):
                            client_badge_ref['element'] = ui.element('div')
                            with client_badge_ref['element']:
                                ui.html('<div class="client-badge">🧪 SANDBOX</div>')
                            
                            ui.button('🧠', on_click=show_memory_dialog).props('flat dense').style(
                                'color: rgba(189,0,255,0.8); border: 1px solid rgba(189,0,255,0.3); '
                                'border-radius: 6px; min-width: 34px; height: 26px; font-size: 14px;'
                            ).tooltip('Управление памятью клиента')
                
                # --- ASSET BAY ---
                with ui.element('div').classes('glass asset-bay'):
                    with ui.row().style('width: 100%; justify-content: space-between; align-items: center; padding: 8px 16px 6px 16px; border-bottom: 1px solid rgba(255,255,255,0.08);'):
                        ui.label('ASSET BAY').style('color: rgba(255,255,255,0.92); font-weight: 900; letter-spacing: .12em; text-transform: uppercase; font-size: 11px;')
                        ui.button('CLEAR', on_click=clear_all_files).props('flat dense size=xs').style('color: rgba(255,80,80,0.5); font-size: 9px; letter-spacing: 0.05em;')
                    files_list_ref['element'] = ui.element('div').classes('file-list')
                    with files_list_ref['element']:
                        ui.label('No files').style('color: rgba(255,255,255,0.4)')
                    
                    ui.upload(
                        on_upload=handle_upload,
                        multiple=True,
                        auto_upload=True,
                    ).props('flat color=purple').style(
                        'margin: 0 8px 4px 8px;'
                    ).classes('hidden-uploader')
                
                # --- PROJECT SETTINGS ---
                with ui.element('div').classes('glass settings-panel'):
                    ui.html('<div class="panel-title">PROJECT SETTINGS</div>')
                    with ui.element('div').classes('panel-body'):
                        
                        with ui.element('div').classes('setting-row'):
                            ui.html('<div class="setting-label">📐 Format</div>')
                            ui.select(
                                options=['9:16', '16:9', '1:1'],
                                value='9:16',
                                on_change=lambda e: state['settings'].update({'format': e.value})
                            ).style('width: 100%')
                        
                        with ui.element('div').classes('setting-row'):
                            ui.html('<div class="setting-label">⏱️ Duration (sec)</div>')
                            ui.number(
                                value=15,
                                min=5,
                                max=300,
                                on_change=lambda e: state['settings'].update({'duration': int(e.value or 30)})
                            ).style('width: 100%')
                        
                        with ui.element('div').classes('setting-row'):
                            ui.html('<div class="setting-label">🎨 Style</div>')
                            ui.select(
                                options=['Stylized 3D Realism', 'Cinematic', 'Minimalist', 'Cyberpunk', 'Documentary', 'Commercial'],
                                value='Stylized 3D Realism',
                                on_change=lambda e: state['settings'].update({'style': e.value})
                            ).style('width: 100%')
                        
                        # Run Type убран из UI — используется значение по умолчанию 'project'
                        # state['run_type'] уже инициализирован как 'project' в state dict
        
        # ─── STAGE ──────────────────────────────────────
        with ui.element('div').classes('area-stage'):
            with ui.element('div').classes('glass stage-monitor').style('height:100%; overflow:hidden;'):
                
                with ui.element('div').classes('stage-toolbar').style('flex-shrink:0;'):
                    # ── ЛЕВАЯ ГРУППА: BRIEF | LOAD ────────────────────────
                    with ui.element('div').style('display:flex; gap:6px; align-items:center;'):
                        ui.button('📋 BRIEF', on_click=build_brief).props('flat').style('''
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(189,0,255,0.15), rgba(0,204,255,0.10)) !important;
                            border: 1px solid rgba(189,0,255,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        ''')
                        ui.button('📂 LOAD', on_click=show_load_dialog).props('flat').style('''
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(0,204,255,0.15), rgba(189,0,255,0.10)) !important;
                            border: 1px solid rgba(0,204,255,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        ''')
                        ui.button('🗂 ASSETS', on_click=show_assets_dialog).props('flat').style('''
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(255,210,0,0.12), rgba(255,140,0,0.08)) !important;
                            border: 1px solid rgba(255,210,0,0.30);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        ''')


                    # ── ЦЕНТРАЛЬНАЯ ГРУППА: CONTINUE | 🏭 | 🔌 | РЕЖИМЫ ──
                    with ui.element('div').style('display:flex; gap:6px; align-items:center; justify-content:center;'):
                        ui.button('▶ CONTINUE', on_click=lambda: continue_cartridge_pipeline()).props('flat no-caps').style(
                            'padding:6px 14px; border-radius:8px; font-size:0.72rem; font-weight:700; '
                            'letter-spacing:0.06em; border:1px solid rgba(255,210,0,0.35); '
                            'color:rgba(255,210,0,0.85); background:rgba(255,210,0,0.07);'
                        )
                        ui.button('🏭', on_click=lambda: ui.navigate.to('/assembly', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(255,140,0,0.3); '
                            'color:rgba(255,140,0,0.8); background:rgba(255,140,0,0.07);'
                        ).tooltip('Сборочный цех')
                        ui.button('🔌', on_click=lambda: ui.navigate.to('/cartridges', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(140,108,255,0.3); '
                            'color:rgba(140,108,255,0.8); background:rgba(140,108,255,0.07);'
                        ).tooltip('Менеджер картриджей')

                        # ── Режимы: social_mix ──
                        if dept == 'social_mix':
                            _sm_refs = {}
                            with ui.element('div').style(
                                'display:flex; align-items:center; gap:6px; '
                                'background:rgba(255,255,255,0.05); border-radius:20px; '
                                'padding:4px 8px; flex-shrink:0;'
                            ):
                                ui.html('<span style="font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                        'letter-spacing:0.12em; margin-right:4px;">РЕЖИМ</span>')

                                def _set_plan():
                                    state['run_type'] = 'content_plan'
                                    state['run_type_locked'] = True  # ПАТЧ: не перезаписывать при BRIEF
                                    _sm_refs['plan'].style('background:rgba(99,179,237,0.3); color:#63b3ed;')
                                    _sm_refs['post'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📝 Контент-план (A01–A04)', type='info', timeout=2000)

                                def _set_post():
                                    state['run_type'] = 'social'
                                    state['run_type_locked'] = True  # ПАТЧ: не перезаписывать при BRIEF
                                    _sm_refs['post'].style('background:rgba(72,187,120,0.3); color:#68d391;')
                                    _sm_refs['plan'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📱 Производство поста (все агенты)', type='info', timeout=2000)

                                _plan_active = state['run_type'] == 'content_plan'
                                _btn_s = ('border:none; border-radius:14px; padding:3px 12px; '
                                          'font-size:0.7rem; font-weight:700; letter-spacing:0.05em; '
                                          'cursor:pointer; transition:all 0.2s;')

                                _sm_refs['plan'] = ui.button('📝 ПЛАН', on_click=_set_plan).props('flat no-caps').style(
                                    _btn_s + ('background:rgba(99,179,237,0.3); color:#63b3ed;'
                                              if _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )
                                _sm_refs['post'] = ui.button('📱 ПОСТ', on_click=_set_post).props('flat no-caps').style(
                                    _btn_s + ('background:rgba(72,187,120,0.3); color:#68d391;'
                                              if not _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )

                        # ── Режимы: video_long ──
                        if dept == 'video_long':
                            _vl_refs = {}
                            with ui.element('div').style(
                                'display:flex; align-items:center; gap:6px; '
                                'background:rgba(255,255,255,0.05); border-radius:20px; '
                                'padding:4px 8px; flex-shrink:0;'
                            ):
                                ui.html('<span style="font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                        'letter-spacing:0.12em; margin-right:4px;">РЕЖИМ</span>')

                                def _set_bible():
                                    state['run_type'] = 'bible'
                                    state['run_type_locked'] = True  # ПАТЧ: не перебивать SET'ом
                                    _vl_refs['bible'].style('background:rgba(139,92,246,0.3); color:#a78bfa;')
                                    _vl_refs['episode'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📖 Библия — создание вселенной (A01–A04)', type='info', timeout=2000)

                                def _set_episode():
                                    state['run_type'] = 'episode'
                                    state['run_type_locked'] = True  # ПАТЧ: не перебивать SET'ом
                                    _vl_refs['episode'].style('background:rgba(52,211,153,0.3); color:#34d399;')
                                    _vl_refs['bible'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('🎬 Эпизод — экранизация по Библии', type='info', timeout=2000)

                                _bible_active = state['run_type'] == 'bible'
                                _vl_btn_s = ('border:none; border-radius:14px; padding:3px 12px; '
                                             'font-size:0.7rem; font-weight:700; letter-spacing:0.05em; '
                                             'cursor:pointer; transition:all 0.2s;')

                                _vl_refs['bible'] = ui.button('📖 BIBLE', on_click=_set_bible).props('flat no-caps').style(
                                    _vl_btn_s + ('background:rgba(139,92,246,0.3); color:#a78bfa;'
                                                 if _bible_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )
                                _vl_refs['episode'] = ui.button('🎬 EPISODE', on_click=_set_episode).props('flat no-caps').style(
                                    _vl_btn_s + ('background:rgba(52,211,153,0.3); color:#34d399;'
                                                 if not _bible_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )

                    # ── ПРАВАЯ ГРУППА: WORD | PDF ─────────────────────────
                    with ui.row().style('gap: 8px; justify-content: flex-end;'):
                        def _show_download_dialog(fmt):
                            """Показывает список файлов для скачивания"""
                            from pathlib import Path as _PP
                            import tempfile
                            
                            # Собираем все файлы
                            all_files = []
                            
                            # Viewer контент
                            if state.get("viewer_content", "").strip():
                                all_files.append(("viewer", "То что сейчас в просмотре", state["viewer_content"]))
                            
                            # Бриф
                            if state.get("master_brief", "").strip():
                                all_files.append(("brief", "Master Brief", state["master_brief"]))
                            
                            # Файлы из runs/
                            rd = _PP("runs")
                            if rd.exists():
                                for run_dir in sorted(rd.iterdir(), reverse=True):
                                    if not run_dir.is_dir():
                                        continue
                                    for mf in sorted(run_dir.glob("*.md")):
                                        try:
                                            txt = mf.read_text(encoding="utf-8")
                                            if len(txt) > 50:
                                                label = f"{run_dir.name} / {mf.name}"
                                                txt = _clean_for_export(txt)
                                                all_files.append((str(mf), label, txt))
                                        except:
                                            pass
                            
                            if not all_files:
                                ui.notify("Нет файлов для скачивания!", type="warning")
                                return
                            
                            def _do_download(text, name, dialog, fmt_type):
                                text = _clean_for_export(text)
                                tmp_dir = _PP(tempfile.mkdtemp())
                                safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")[:40]
                                if fmt_type == "word":
                                    tmp = tmp_dir / f"{safe_name}.docx"
                                    if _export_docx(text, tmp):
                                        ui.download(str(tmp), f"{safe_name}.docx")
                                        ui.notify("Word скачан!", type="positive")
                                    else:
                                        ui.notify("pip install python-docx", type="negative")
                                else:
                                    tmp = tmp_dir / f"{safe_name}.pdf"
                                    if _export_pdf(text, tmp):
                                        ui.download(str(tmp), f"{safe_name}.pdf")
                                        ui.notify("PDF скачан!", type="positive")
                                    else:
                                        ui.notify("pip install fpdf2", type="negative")
                                dialog.close()
                            
                            with ui.dialog() as dlg, ui.card().style(
                                "background: #0d1117; border: 1px solid rgba(255,255,255,0.1); "
                                "min-width: 500px; max-width: 650px; max-height: 75vh;"
                            ):
                                fmt_label = "Word" if fmt == "word" else "PDF"
                                with ui.row().style("justify-content: space-between; align-items: center; width: 100%; margin-bottom: 12px;"):
                                    ui.label(f"Скачать как {fmt_label}").style("color: white; font-weight: 900; font-size: 16px;")
                                    ui.button("X", on_click=dlg.close).props("flat dense").style("color: rgba(255,255,255,0.4);")
                                
                                ui.label(f"{len(all_files)} файлов доступно").style(
                                    "color: rgba(255,255,255,0.35); font-size: 11px; margin-bottom: 8px;")
                                
                                with ui.element("div").style("overflow-y: auto; max-height: 55vh;"):
                                    for fid, label, txt in all_files:
                                        size_kb = len(txt.encode("utf-8")) // 1024
                                        with ui.element("div").style(
                                            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); "
                                            "border-radius: 10px; padding: 10px 14px; margin-bottom: 6px; cursor: pointer; "
                                            "transition: all 0.2s;"
                                        ).on("click", lambda e, t=txt, n=label: _do_download(t, n, dlg, fmt)):
                                            with ui.row().style("justify-content: space-between; align-items: center;"):
                                                ui.label(label).style(
                                                    "color: rgba(255,255,255,0.8); font-size: 12px; "
                                                    "font-family: JetBrains Mono, monospace;")
                                                ui.label(f"{size_kb} KB").style(
                                                    "color: rgba(255,255,255,0.3); font-size: 10px;")
                            dlg.open()
                        
                        ui.button("WORD", on_click=lambda: _show_download_dialog("word")).props("flat").style(
                            "padding: 8px 14px; border-radius: 8px; "
                            "background: linear-gradient(135deg, rgba(0,255,136,0.12), rgba(0,204,255,0.08)) !important; "
                            "border: 1px solid rgba(0,255,136,0.30); "
                            "color: rgba(255,255,255,0.85); font-weight: 700; font-size: 12px;")
                        ui.button("PDF", on_click=lambda: _show_download_dialog("pdf")).props("flat").style(
                            "padding: 8px 14px; border-radius: 8px; "
                            "background: linear-gradient(135deg, rgba(255,149,0,0.12), rgba(255,80,80,0.08)) !important; "
                            "border: 1px solid rgba(255,149,0,0.30); "
                            "color: rgba(255,255,255,0.85); font-weight: 700; font-size: 12px;")

                
                with ui.element('div').classes('stage-content').style('flex:1; min-height:0; overflow:hidden;'):
                    with ui.element('div').classes('split-view').style('height:100%; min-height:0; overflow:hidden;'):
                        
                        chat_log_ref['element'] = ui.element('div').classes('chat-log').style('flex:1; min-height:0; overflow-y:auto; overflow-x:hidden;')
                        with chat_log_ref['element']:
                            ui.html('<div class="chat-msg-system">SYSTEM: Ready</div>')
                        
                        viewer_ref['element'] = ui.element('div').classes('viewer').style('flex:1; min-height:0; overflow-y:auto; overflow-x:hidden;')
                        with viewer_ref['element']:
                            ui.label('Waiting for input...')
                
                with ui.element('div').classes('floating-console'):
                    ui.button('💾', on_click=save_chat).props('flat dense').style('color: rgba(255,255,255,0.6); min-width: 40px')
                    ui.button('🗑️', on_click=clear_chat).props('flat dense').style('color: rgba(255,255,255,0.6); min-width: 40px')
                    input_ref['element'] = ui.input(placeholder='Type message...').props('borderless').style('flex: 1')
                    input_ref['element'].on('keydown.enter', send_message)
                    ui.button('SEND', on_click=send_message).classes('send-button')

        
        # ─── RIGHT PANEL ────────────────────────────────
        with ui.element('div').classes('area-right'):
            with ui.element('div').classes('right-col'):
                
                # --- Agent avatar ---
                status_ref['element'] = ui.element('div').classes('right-top-slot')
                with status_ref['element']:
                    ui.html(f'''
                        <div style="position: relative; width: 100%; height: 100%; min-height: 200px;">
                            <img src="/static/avatars/{dept}/SET.png" 
                                style="width: 100%; height: 100%; object-fit: cover; 
                                        border-radius: 12px; opacity: 0.85;">
                            <div style="position: absolute; bottom: 0; left: 0; right: 0; 
                                        padding: 15px; background: linear-gradient(transparent, rgba(0,0,0,0.8));
                                        border-radius: 0 0 12px 12px;">
                                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">ACTIVE AGENT</div>
                                <div style="font-size: 1.3rem; font-weight: 700; color: #00ff88;">SET</div>
                                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.8);">Координатор</div>
                            </div>
                        </div>
                    ''')
                
                # --- RUNS LIST ---
                with ui.element('div').classes('glass runs-panel'):
                    ui.html('<div class="panel-title">📁 RUNS</div>')
                    runs_list_ref['element'] = ui.element('div').classes('runs-list')
                    with runs_list_ref['element']:
                        ui.label("Нет run'ов").style('color: rgba(255,255,255,0.3); font-size: 11px;')
                
                
                # --- ACTION BUTTONS (3 старта) ---
                ui.button(
                    '⚡ TURBO' if is_turbo else '▶ FULL PIPELINE',
                    on_click=lambda: run_cartridge_turbo() if is_turbo else run_cartridge_pipeline()
                ).classes('neon-btn g').props('flat')
                ui.button('▶ FROM CURRENT', on_click=lambda: run_cartridge_pipeline(state["active_worker"])).classes('neon-btn b').props('flat')
                ui.button('⚓ ANCHOR', on_click=lambda: run_cartridge_pipeline(from_worker=state["active_worker"], with_chat_context=True)).classes('neon-btn p').props('flat')

                async def _check_auto_run():
                    global _auto_run_requested
                    # ПАТЧ: не стартуем если pipeline на паузе (Виктор, checkpoint)
                    if not _auto_run_requested:
                        return
                    if state.get("pipeline_running"):
                        return
                    if state.get("paused_at"):
                        return
                    _auto_run_requested = False
                    try:
                        with _page_client:
                            await run_cartridge_pipeline()
                    except Exception:
                        pass

                ui.timer(1.0, _check_auto_run)

# ═══════════════════════════════════════════════════════════
# API ДЛЯ РОДИТЕЛЬСКОГО КАБИНЕТА
# ═══════════════════════════════════════════════════════════
from pydantic import BaseModel
from typing import Optional

class _AutoRequest(BaseModel):
    child_name: str
    child_age: str
    task_context: str
    parent_email: Optional[str] = None

@app.post("/api/studio/generate")
async def _auto_generate(request: _AutoRequest):
    global _current_state, _current_run_pipeline

    if _current_state is None:
        return {"status": "error", "message": "Студия не открыта в браузере"}

    master_brief = {
        "project": {"name": f"История для {request.child_name}", "workshop": "living_book"},
        "story": {"real_task": request.task_context},
        "child": {"name": request.child_name, "age": request.child_age},
        "key_message": f"{request.child_name} справится!"
    }

    import json as _json
    _current_state["master_brief"] = _json.dumps(master_brief, ensure_ascii=False, indent=2)
    _current_state["active_dept"] = "living_book"

    global _auto_run_requested
    _auto_run_requested = True
    return {"status": "started", "child_name": request.child_name}