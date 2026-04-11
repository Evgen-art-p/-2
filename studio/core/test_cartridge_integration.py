"""
Тест интеграции картриджей с реальной структурой модулей
"""
from studio.core.cartridge import CartridgeManager

def test_real_modules():
    print("🧪 Тестирование с реальными модулями студии...\n")
    
    manager = CartridgeManager()
    
    # Показать все обнаруженные модули
    all_modules = manager._discover_all_modules()
    print(f"📂 Найдено модулей в системе: {len(all_modules)}")
    for mod in sorted(all_modules):
        print(f"   • {mod}")
    
    print("\n" + "="*60 + "\n")
    
    # Тест активации разных картриджей
    test_cases = [
        ('default', 'Полная студия'),
        ('shorts_factory', 'Фабрика шортсов'),
        ('living_book_studio', 'Живая книга'),
        ('web_studio', 'Веб-студия'),
        ('social_media_hub', 'Соцсети'),
    ]
    
    for cart_id, description in test_cases:
        print(f"\n🔄 Тест: {description} ({cart_id})")
        print("-" * 40)
        
        success = manager.activate_cartridge(cart_id)
        if success:
            config = manager.get_active_config()
            
            # Проверка соответствия модулей
            requested_modules = config.get('modules', [])
            print(f"   Запрошено: {requested_modules}")
            print(f"   Активно: {manager.available_modules}")
            
            # Валидация
            if 'all' not in requested_modules:
                for mod in requested_modules:
                    exists = mod in all_modules
                    available = manager.is_module_available(mod)
                    status = "✅" if (exists and available) else "❌"
                    print(f"   {status} {mod}: существует={exists}, доступен={available}")
    
    print("\n" + "="*60)
    print("\n✅ Тестирование завершено!")
    print("\n💡 Следующие шаги:")
    print("   1. Интегрировать cartridge_manager в workshop/ui.py")
    print("   2. Добавить селектор картриджей в главный экран")
    print("   3. Обернуть отображение цехов в check_module_visibility()")
    print("   4. Протестировать переключение в реальном интерфейсе")


if __name__ == "__main__":
    test_real_modules()
