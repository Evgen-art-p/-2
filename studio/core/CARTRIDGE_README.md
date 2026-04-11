# Cartridge System Documentation

## 📦 Что такое система картриджей?

Система картриджей позволяет динамически переключать конфигурацию студии, активируя только нужные цеха (модули) и пайплайны для конкретной задачи.

## 🎯 Доступные картриджи

### 1. 🏭 Полная Студия (Default)
- **ID:** `default`
- **Описание:** Все цеха и департаменты доступны. Полный цикл производства.
- **Использование:** Основная рабочая конфигурация

### 2. 🎬 Фабрика Шортсов
- **ID:** `shorts_factory`
- **Описание:** Специализированный режим для создания вертикальных видео
- **Модули:** turbo, video_shorts, assets
- **Пайплайны:** shorts_render, turbo_boost
- **Использование:** Быстрое производство шортсов без лишних модулей

### 3. 📚 Живая Книга
- **ID:** `living_book_studio`
- **Описание:** Глубокая проработка сюжетов, персонажей и мира
- **Модули:** living_book, memory, characters, world_building
- **Пайплайны:** book_phase_1 через book_phase_5
- **Использование:** Многоступенчатое создание книг

### 4. 🌐 Веб-Студия
- **ID:** `web_studio`
- **Описание:** Создание лендингов, статей и веб-историй
- **Модули:** web_story, content_plan, seo, assets
- **Пайплайны:** web_publish, article_flow

### 5. 📱 Соцсети Хаб
- **ID:** `social_media_hub`
- **Описание:** Планирование постов, генерация контента для соцсетей
- **Модули:** social, content_plan, assets
- **Пайплайны:** social_schedule, post_generator

## 🔧 Как использовать

### В коде (Python)

```python
from studio.core.cartridge import cartridge_manager

# Получить список картриджей
cartridges = cartridge_manager.get_cartridge_list()

# Активировать картридж
cartridge_manager.activate_cartridge('shorts_factory')

# Проверить доступность модуля
if cartridge_manager.is_module_available('turbo'):
    # Запустить turbo-пайплайн
    pass

# Проверить доступность пайплайна
if cartridge_manager.is_pipeline_available('shorts_render'):
    # Использовать пайплайн рендеринга
    pass
```

### В интерфейсе (NiceGUI)

```python
from studio.core.cartridge_ui import create_cartridge_selector, render_cartridge_status

# Создать селектор картриджей
def on_cartridge_changed(cart_id):
    print(f'Переключено на: {cart_id}')
    # Перерисовать интерфейс с учётом нового картриджа

create_cartridge_selector(on_change_callback=on_cartridge_changed)

# Отобразить статус
render_cartridge_status()

# Проверить видимость модуля в UI
if check_module_visibility('living_book'):
    # Показать кнопку/панель Living Book
    pass
```

## 📁 Структура файлов

```
studio/
├── config/
│   └── cartridges.json       # Конфигурация картриджей
├── core/
│   ├── cartridge.py          # Ядро системы (CartridgeManager)
│   └── cartridge_ui.py       # UI компоненты
└── modules/                  # Цеха (автоматически сканируются)
    ├── turbo/
    ├── living_book/
    ├── web_story/
    └── ...
```

## ➕ Как добавить новый картридж

1. Откройте `/workspace/studio/config/cartridges.json`
2. Добавьте новую запись:

```json
"my_custom_studio": {
  "name": "🚀 Моя Студия",
  "description": "Кастомная конфигурация",
  "modules": ["turbo", "social", "assets"],
  "pipelines": ["turbo_boost", "social_schedule"]
}
```

3. Перезагрузите приложение

## 🔍 Принцип работы

1. При старте загружаются все конфигурации из `cartridges.json`
2. При активации картриджа:
   - Если указано `["all"]` — сканируется папка `modules/`
   - Если указан конкретный список — используются только эти модули
3. UI проверяет доступность через `check_module_visibility()` и скрывает недоступные элементы

## 🎨 Примеры использования

### Только шортсы:
```bash
python -c "from studio.core.cartridge import cartridge_manager; cartridge_manager.activate_cartridge('shorts_factory')"
```

### Живая книга + Веб-студия (кастомный микс):
Создайте свой картридж в JSON с нужными модулями из обоих режимов.

## ⚠️ Важные заметки

- Картриджи не удаляют модули физически, только скрывают их из UI
- Переключение картриджа не прерывает текущие процессы
- Для применения изменений может потребоваться перезагрузка страницы/приложения
