# studio/client_manager.py
import json
import shutil
from pathlib import Path
from datetime import datetime
from . import config

class ClientManager:
    """Управление клиентами"""
    
    @staticmethod
    def create_client(client_id: str, client_name: str) -> Path:
        """Создаёт нового клиента из шаблона"""
        
        client_path = config.get_client_path(client_id)
        
        if client_path.exists():
            raise ValueError(f"Клиент '{client_id}' уже существует!")
        
        # Создаём папки
        client_path.mkdir(parents=True)
        (client_path / config.JOBS_FOLDER).mkdir()
        
        # Копируем и заполняем шаблоны
        today = datetime.now().strftime("%Y-%m-%d")
        
        for template_file in config.TEMPLATES_DIR.glob("*.json"):
            content = json.loads(template_file.read_text(encoding="utf-8"))
            
            # Заполняем базовые поля
            ClientManager._fill_template(content, {
                "client_id": client_id,
                "id": client_id,
                "client_name": client_name,
                "name": client_name,
                "created": today,
                "last_updated": today
            })
            
            # Сохраняем
            output_path = client_path / template_file.name
            output_path.write_text(
                json.dumps(content, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        
        return client_path
    
    @staticmethod
    def load_client(client_id: str) -> dict:
        """Загружает все данные клиента"""
        
        client_path = config.get_client_path(client_id)
        
        if not client_path.exists():
            raise ValueError(f"Клиент '{client_id}' не найден!")
        
        return {
            "client_id": client_id,
            "client_info": ClientManager._load_json(client_path / config.CLIENT_INFO_FILE),
            "project_memory": ClientManager._load_json(config.get_client_memory(client_id)),
            "history_dna": ClientManager._load_json(config.get_client_history(client_id))
        }
    
    @staticmethod
    def update_memory(client_id: str, updates: dict):
        """Обновляет память клиента"""
        
        memory_path = config.get_client_memory(client_id)
        memory = ClientManager._load_json(memory_path)
        
        # Мержим
        ClientManager._deep_merge(memory, updates)
        
        # Обновляем дату
        memory["client"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        # Сохраняем
        memory_path.write_text(
            json.dumps(memory, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    @staticmethod
    def add_to_history(client_id: str, job_data: dict):
        """Добавляет работу в историю"""
        
        history_path = config.get_client_history(client_id)
        history = ClientManager._load_json(history_path)
        
        history["jobs"].append(job_data)
        
        history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    @staticmethod
    def create_job(client_id: str, workshop_id: str, job_name: str) -> Path:
        """Создаёт новую работу для клиента"""
        
        jobs_path = config.get_client_jobs(client_id)
        jobs_path.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя папки
        date = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{date}_{job_name}"
        job_path = jobs_path / folder_name
        job_path.mkdir()
        
        # Создаём master_brief
        brief = {
            "job_id": folder_name,
            "client_id": client_id,
            "workshop": workshop_id,
            "created": datetime.now().isoformat(),
            "status": "draft"
        }
        
        (job_path / "master_brief.json").write_text(
            json.dumps(brief, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # Создаём папку для ассетов
        (job_path / "assets").mkdir()
        (job_path / "outputs").mkdir()
        
        return job_path
    
    @staticmethod
    def list_jobs(client_id: str) -> list[dict]:
        """Список всех работ клиента"""
        
        jobs_path = config.get_client_jobs(client_id)
        jobs = []
        
        if jobs_path.exists():
            for folder in sorted(jobs_path.iterdir(), reverse=True):
                if folder.is_dir():
                    brief_path = folder / "master_brief.json"
                    if brief_path.exists():
                        brief = ClientManager._load_json(brief_path)
                        brief["path"] = str(folder)
                        jobs.append(brief)
        
        return jobs
    
    # === Хелперы ===
    
    @staticmethod
    def _load_json(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}
    
    @staticmethod
    def _fill_template(obj, values: dict):
        """Рекурсивно заполняет пустые поля"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if value == "" and key in values:
                    obj[key] = values[key]
                elif isinstance(value, (dict, list)):
                    ClientManager._fill_template(value, values)
        elif isinstance(obj, list):
            for item in obj:
                ClientManager._fill_template(item, values)
    
    @staticmethod
    def _deep_merge(base: dict, updates: dict):
        """Глубокий мерж словарей"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ClientManager._deep_merge(base[key], value)
            else:
                base[key] = value
