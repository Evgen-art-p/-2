"""
UI Components for Cartridge System
Компоненты интерфейса для выбора и переключения картриджей
"""
from nicegui import ui
from studio.core.cartridge import cartridge_manager

def create_cartridge_selector(on_change_callback=None):
    """
    Создает селектор картриджей для UI
    
    Args:
        on_change_callback: Функция обратного вызова при смене картриджа
                           Получает cartridge_id как аргумент
    """
    cartridges = cartridge_manager.get_cartridge_list()
    
    # Создаем options для select
    options = {c['id']: c['name'] for c in cartridges}
    descriptions = {c['id']: c['description'] for c in cartridges}
    
    with ui.card().classes('w-full'):
        ui.label('📦 Профиль студии (Картридж)').classes('text-lg font-bold')
        
        selected = ui.select(
            options=options,
            value=cartridge_manager.active_cartridge or 'default',
            label='Выберите режим работы',
            on_change=lambda e: _on_cartridge_change(e.value, on_change_callback)
        ).classes('w-full')
        
        description_label = ui.label(
            descriptions.get(cartridge_manager.active_cartridge or 'default', '')
        ).classes('text-gray-600 italic')
        
        # Обновляем описание при изменении
        def update_description():
            description_label.set_text(descriptions.get(selected.value, ''))
        
        original_on_change = selected.on_change
        def wrapped_change(e):
            update_description()
            if original_on_change:
                original_on_change(e)
        
        # Инфо-блок с активными модулями
        info_container = ui.element('div').classes('mt-2 p-3 bg-gray-100 rounded')
        with info_container:
            modules_label = ui.label('Модули: -')
            pipelines_label = ui.label('Пайплайны: -')
    
    def update_info():
        config = cartridge_manager.get_active_config()
        if config:
            modules = config.get('modules', [])
            pipelines = config.get('pipelines', [])
            modules_label.set_text(f"📦 Модули: {', '.join(modules) if modules else 'Все'}")
            pipelines_label.set_text(f"🔗 Пайплайны: {', '.join(pipelines) if pipelines else 'Все'}")
    
    # Хук для обновления информации
    def _on_cartridge_change(cartridge_id, callback):
        cartridge_manager.activate_cartridge(cartridge_id)
        update_info()
        if callback:
            callback(cartridge_id)
    
    return selected


def render_cartridge_status():
    """
    Отображает текущий статус картриджа в виде информера
    """
    if not cartridge_manager.active_cartridge:
        return ui.label('⚠️ Картридж не активирован').classes('text-yellow-600')
    
    config = cartridge_manager.get_active_config()
    name = config.get('name', 'Неизвестный')
    
    with ui.row().classes('items-center gap-2'):
        ui.icon('memory', size='md').classes('text-blue-600')
        ui.label(name).classes('font-bold')
        ui.badge(len(cartridge_manager.available_modules)).props('color=blue').tooltip('Активных модулей')
        ui.badge(len(cartridge_manager.available_pipelines)).props('color=green').tooltip('Доступных пайплайнов')


def check_module_visibility(module_name: str) -> bool:
    """
    Проверка видимости модуля в текущем картридже
    Используется в UI для скрытия/показа элементов
    """
    return cartridge_manager.is_module_available(module_name)


def check_pipeline_visibility(pipeline_name: str) -> bool:
    """
    Проверка доступности пайплайна в текущем картридже
    """
    return cartridge_manager.is_pipeline_available(pipeline_name)


# Пример использования в приложении
if __name__ in {"__main__", "__mp_main__"}:
    @ui.page('/test-cartridges')
    def test_page():
        ui.label('Тест системы картриджей').classes('text-2xl font-bold')
        
        def on_cartridge_changed(cart_id):
            ui.notify(f'Активирован картридж: {cart_id}')
            content_refresh()
        
        create_cartridge_selector(on_change_callback=on_cartridge_changed)
        
        ui.separator()
        
        status_container = ui.element('div')
        
        def content_refresh():
            with status_container:
                status_container.clear()
                render_cartridge_status()
        
        content_refresh()
        
        # Демонстрация проверки видимости
        ui.separator()
        ui.label('Проверка видимости модулей:').classes('font-bold')
        
        test_modules = ['turbo', 'living_book', 'web_story', 'social']
        for mod in test_modules:
            visible = check_module_visibility(mod)
            icon = '✅' if visible else '❌'
            ui.label(f'{icon} {mod}')
    
    ui.run(title='Cartridge Test', port=8080)
