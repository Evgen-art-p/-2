# main.py (с TURBO-цехом + Сборочный цех)
from pathlib import Path
from fastapi import Request
from nicegui import ui, app

from studio.workshop import page_workshop
from studio.turbo import page_turbo
from studio.reception import page_reception
from studio.assembly import page_assembly
from studio.cabinet.ui_cabinet import page_cabinet
from studio.ui_registry import page_registry
from studio.cartridge_manager import page_cartridge_manager
from studio.modules.living_book.ui_book_loader import page_book_loader
from studio.economy.ui_dashboard import dashboard_page


BASE_DIR = Path(__file__).resolve().parent
app.add_static_files('/images', str(BASE_DIR / 'images'))
app.add_static_files('/static', str(BASE_DIR / 'static'))
app.add_static_files('/avatars', str(BASE_DIR / 'static' / 'avatars'))
app.add_static_files('/registry_images', str(BASE_DIR / '00_REGISTRY_NFT' / 'images'))

@ui.page('/cabinet')
def cabinet():
    page_cabinet()


@ui.page('/')
def index():
    page_reception()


@ui.page('/workshop')
def workshop(request: Request):
    dept = request.query_params.get('dept', 'video_long')
    prompt = request.query_params.get('prompt', '')
    page_workshop(dept, prompt)


@ui.page('/turbo')
def turbo():
    page_turbo()


@ui.page('/assembly')
def assembly():
    page_assembly()


@ui.page('/registry')
def registry():
    page_registry()
    

@ui.page('/cartridges')
def cartridges():
    page_cartridge_manager()    

@ui.page("/living_book_loader")
def living_book_loader_page():
    page_book_loader()    

# ══ Loka-Filter: пульс города при старте · Спринт 21 ══
# Daemon-тред — не блокирует запуск студии если что-то пойдёт не так.
# Затухает сенсорная память ВСЕХ агентов: Cabinet, city_walker, резиденты.
# Без этого агенты не стареют вне пайплайна — город стоит.
import threading as _loka_thread
def _run_loka_filter():
    try:
        from studio.grondheim_memory import run_loka_filter_all
        run_loka_filter_all()
        print("[LOKA-FILTER] Пульс города завершён")
    except Exception as _err:
        print(f"[LOKA-FILTER] Ошибка: {_err}")
_loka_thread.Thread(
    target=_run_loka_filter,
    daemon=True,
    name="LokaFilterStartup",
).start()
print("[LOKA-FILTER] Пульс города запущен в фоне")
# ══ END Loka-Filter ══

from studio.slot_manager import SlotManager
SlotManager().print_summary()

if __name__ in {"__main__", "__mp_main__"}:
    # ПАТЧ nicegui_timeout:
    # reconnect_timeout=300 — браузер ждёт переподключения 5 минут
    #   (LLM-запросы могут идти 30-90 сек, дефолт NiceGUI ~30 сек)
    # ping_interval=15, ping_timeout=60 — сервер пингует браузер каждые 15 сек
    #   чтобы WebSocket не считался мёртвым при длинных запросах
    ui.run(
        reload=False,
        reconnect_timeout=300,
        ping_interval=15,
        ping_timeout=60,
    )
