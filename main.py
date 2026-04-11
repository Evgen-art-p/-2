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

from studio.grondheim_memory import run_loka_filter_all
run_loka_filter_all()

from studio.slot_manager import SlotManager
SlotManager().print_summary()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()
