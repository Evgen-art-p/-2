from nicegui import ui

def agent_card(agent, mini=False):
    """
    agent: словарь с данными работника (из crew.py)
    mini: если True - компактный вид для Ресепшена, если False - полный для Цеха
    """
    # Определяем стиль карточки
    with ui.card().classes('bg-slate-800 border border-slate-700 hover:border-purple-500 transition-all cursor-pointer'):
        if mini:
            # Вариант для Ресепшена (маленький)
            with ui.row().classes('items-center gap-2 p-1'):
                ui.avatar(agent['name'][0], color='purple-500', text_color='white').props('size=sm')
                with ui.column().classes('gap-0'):
                    ui.label(agent['name']).classes('text-xs font-bold text-gray-200')
                    ui.label(agent['role']).classes('text-[10px] text-gray-400')
        else:
            # Вариант для Цеха (тут будет фото и кнопки)
            ui.label(agent['name']).classes('text-lg font-bold text-white')
            # ... тут добавим логику позже