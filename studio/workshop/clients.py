# studio/workshop_clients.py — CRUD клиентов, slug, info, список
# Вынесено из ui_workshop.py (строки 873-1135)

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from studio.config import BASE_DIR

CLIENTS_DIR = BASE_DIR / "clients"
RUNS_DIR = BASE_DIR / "runs"

# Создаём базовые папки
CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)
(CLIENTS_DIR / "_sandbox").mkdir(exist_ok=True)
_sandbox_mem = CLIENTS_DIR / "_sandbox" / "memory.json"
if not _sandbox_mem.exists():
    _sandbox_mem.write_text('{"client":"_sandbox","runs":[]}', encoding='utf-8')


def get_clients_list() -> list[str]:
    """Возвращает список папок клиентов (без _sandbox)"""
    clients = []
    if CLIENTS_DIR.exists():
        for p in sorted(CLIENTS_DIR.iterdir()):
            if p.is_dir() and p.name != "_sandbox":
                clients.append(p.name)
    return clients


def load_client_info(client_slug: str) -> dict:
    """Загружает info.json клиента"""
    info_path = CLIENTS_DIR / client_slug / "info.json"
    if info_path.exists():
        try:
            return json.loads(info_path.read_text(encoding='utf-8'))
        except:
            pass
    return {"name": client_slug, "niche": "", "description": ""}


def save_client_info(client_slug: str, info: dict):
    """Сохраняет info.json клиента"""
    client_dir = CLIENTS_DIR / client_slug
    client_dir.mkdir(parents=True, exist_ok=True)
    info_path = client_dir / "info.json"
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')


def create_client(name: str, niche: str = "", description: str = "") -> str:
    """Создаёт нового клиента, возвращает slug"""
    slug = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ_-]', '_', name.lower().strip())
    slug = re.sub(r'_+', '_', slug).strip('_')
    if not slug:
        slug = f"client_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    client_dir = CLIENTS_DIR / slug
    client_dir.mkdir(parents=True, exist_ok=True)
    
    info = {"name": name, "niche": niche, "description": description, "created": datetime.now().isoformat()}
    save_client_info(slug, info)
    
    from studio.workshop.memory import save_client_memory
    memory = {"client": slug, "runs": []}
    save_client_memory(slug, memory)
    
    return slug


def get_client_runs(client_slug: str) -> list[dict]:
    """Возвращает список run'ов клиента из папки runs/"""
    runs = []
    if not RUNS_DIR.exists():
        return runs
    
    if client_slug == "_sandbox":
        search_key = "_sandbox_"
    else:
        search_key = f"_{client_slug}_"
    
    for p in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not p.is_dir():
            continue
        if p.name.startswith("_"):
            continue
        
        if search_key in p.name:
            files = [f.name for f in p.iterdir() if f.is_file()]
            if files:
                runs.append({
                    "name": p.name,
                    "path": str(p),
                    "files": files,
                    "date": p.stat().st_mtime,
                })
    return runs


def delete_run(run_path: str):
    """Удаляет папку run'а"""
    p = Path(run_path)
    if p.exists() and p.is_dir() and str(RUNS_DIR) in str(p):
        shutil.rmtree(p)
