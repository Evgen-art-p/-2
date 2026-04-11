"""
Cartridge System for Studio
Динамическое переключение конфигураций цехов и пайплайнов
"""
import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

class CartridgeManager:
    """Менеджер картриджей (профилей) студии"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "cartridges.json"
        
        self.config_path = Path(config_path)
        self.cartridges: Dict[str, Any] = {}
        self.active_cartridge: Optional[str] = None
        self.available_modules: List[str] = []
        self.available_pipelines: List[str] = []
        
        self.load_cartridges()
    
    def load_cartridges(self) -> bool:
        """Загрузка конфигураций картриджей из JSON"""
        try:
            if not self.config_path.exists():
                print(f"⚠️  Файл картриджей не найден: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.cartridges = json.load(f)
            
            print(f"✅ Загружено {len(self.cartridges)} картриджей")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки картриджей: {e}")
            return False
    
    def get_cartridge_list(self) -> List[Dict[str, str]]:
        """Получить список доступных картриджей для UI"""
        result = []
        for key, data in self.cartridges.items():
            result.append({
                "id": key,
                "name": data.get("name", key),
                "description": data.get("description", "")
            })
        return result
    
    def activate_cartridge(self, cartridge_id: str) -> bool:
        """Активировать картридж по ID"""
        if cartridge_id not in self.cartridges:
            print(f"❌ Картридж '{cartridge_id}' не найден")
            return False
        
        self.active_cartridge = cartridge_id
        config = self.cartridges[cartridge_id]
        
        # Здесь должна быть логика фильтрации модулей и пайплайнов
        # Для прототипа просто сохраняем список
        modules = config.get("modules", [])
        pipelines = config.get("pipelines", [])
        
        if "all" in modules:
            # Загрузить все доступные модули
            self.available_modules = self._discover_all_modules()
        else:
            self.available_modules = modules
        
        if "all" in pipelines:
            self.available_pipelines = self._discover_all_pipelines()
        else:
            self.available_pipelines = pipelines
        
        print(f"🔌 Активирован картридж: {config.get('name', cartridge_id)}")
        print(f"   📦 Модули: {len(self.available_modules)}")
        print(f"   🔗 Пайплайны: {len(self.available_pipelines)}")
        
        return True
    
    def _discover_all_modules(self) -> List[str]:
        """Авто-обнаружение всех доступных модулей"""
        modules_dir = Path(__file__).parent.parent / "modules"
        if not modules_dir.exists():
            return []
        
        modules = []
        for item in modules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                modules.append(item.name)
        return modules
    
    def _discover_all_pipelines(self) -> List[str]:
        """Авто-обнаружение всех доступных пайплайнов"""
        # Заглушка - в реальности сканирует файлы pipeline
        return ["default", "turbo_boost", "shorts_render", "book_flow"]
    
    def is_module_available(self, module_name: str) -> bool:
        """Проверка доступности модуля в текущем картридже"""
        if not self.active_cartridge:
            return False
        return module_name in self.available_modules
    
    def is_pipeline_available(self, pipeline_name: str) -> bool:
        """Проверка доступности пайплайна в текущем картридже"""
        if not self.active_cartridge:
            return False
        return pipeline_name in self.available_pipelines
    
    def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Получить конфигурацию активного картриджа"""
        if not self.active_cartridge:
            return None
        return self.cartridges.get(self.active_cartridge)


# Глобальный экземпляр (для использования в приложении)
cartridge_manager = CartridgeManager()


def init_cartridge_system():
    """Инициализация системы картриджей"""
    return cartridge_manager


if __name__ == "__main__":
    # Тестирование прототипа
    print("🧪 Тестирование системы картриджей...\n")
    
    manager = CartridgeManager()
    
    # Показать список
    print("📋 Доступные картриджи:")
    for cart in manager.get_cartridge_list():
        print(f"  • {cart['id']}: {cart['name']}")
        print(f"    {cart['description']}\n")
    
    # Активация
    print("\n🔄 Активация 'shorts_factory'...")
    manager.activate_cartridge("shorts_factory")
    
    print("\n🔄 Активация 'living_book_studio'...")
    manager.activate_cartridge("living_book_studio")
    
    print("\n✅ Прототип готов!")
