# studio/config.py
from dataclasses import dataclass
import os
from pathlib import Path

# === Paths ===
BASE_DIR = Path(__file__).resolve().parent.parent


# Подгружаем переменные из .env автоматически (если файл есть).
# Это нужно, потому что некоторые скрипты читают os.getenv напрямую и
# не используют python-dotenv.
def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue

        # Не перезаписываем переменные окружения.
        if not os.getenv(key):
            os.environ[key] = value


_load_env_file()

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MODULES_DIR = BASE_DIR / "studio" / "modules"
RUNS_DIR = BASE_DIR / "runs"
TEMPLATES_DIR = RUNS_DIR / "_templates"
SANDBOX_DIR = RUNS_DIR / "_sandbox"

# === Memory Files (имена файлов) ===
CLIENT_INFO_FILE = "client_info.json"
MEMORY_FILE = "project_memory.json"
HISTORY_FILE = "history_dna.json"
JOBS_FOLDER = "jobs"

# === API ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
PROXY_URL = os.getenv("PROXY_URL", "")

FAL_KEY = os.getenv("FAL_KEY", "")
TAVILY_KEY = os.getenv("TAVILY_KEY", "")

HTTP_TIMEOUT = 120


# === UI Cards ===
@dataclass(frozen=True)
class WorkshopCard:
    code: str
    title: str
    color: str
    hover: str

BASE_CARD = (
    "bg-gray-900/70 backdrop-blur-lg "
    "border border-white/10"
)

WORKSHOPS: list[WorkshopCard] = [
    WorkshopCard("web_story",   "🌐 Web Story",    BASE_CARD, "hover:shadow-lg hover:shadow-cyan-500/30"),
    WorkshopCard("video_long",  "🎥 Видео Long",   BASE_CARD, "hover:shadow-lg hover:shadow-purple-500/30"),
    WorkshopCard("video_short", "⚡ Видео Shorts", BASE_CARD, "hover:shadow-lg hover:shadow-amber-500/30"),
    WorkshopCard("social_mix",  "🗓️ Соцсети",      BASE_CARD, "hover:shadow-lg hover:shadow-sky-500/30"),
    WorkshopCard("market_hit",  "🛒 Маркетплейсы", BASE_CARD, "hover:shadow-lg hover:shadow-lime-500/30"),
    WorkshopCard("logo_design", "🧩 Логотипы",     BASE_CARD, "hover:shadow-lg hover:shadow-fuchsia-500/30"),
    WorkshopCard("emo_card",    "💌 Открытки",     BASE_CARD, "hover:shadow-lg hover:shadow-rose-500/30"),
    WorkshopCard("print_promo", "🖨️ Принты",       BASE_CARD, "hover:shadow-lg hover:shadow-slate-500/30"),
]


# === Helper Functions ===
def get_client_path(client_id: str) -> Path:
    """Путь к папке клиента"""
    return RUNS_DIR / client_id

def get_client_memory(client_id: str) -> Path:
    """Путь к файлу памяти клиента"""
    return get_client_path(client_id) / MEMORY_FILE

def get_client_history(client_id: str) -> Path:
    """Путь к файлу истории клиента"""
    return get_client_path(client_id) / HISTORY_FILE

def get_client_jobs(client_id: str) -> Path:
    """Путь к папке работ клиента"""
    return get_client_path(client_id) / JOBS_FOLDER

def get_workshop_path(workshop_id: str) -> Path:
    """Путь к папке цеха"""
    return MODULES_DIR / workshop_id

def get_agent_path(workshop_id: str, agent_num: int) -> Path:
    """Путь к папке агента"""
    return get_workshop_path(workshop_id) / f"A{agent_num:02d}"

def list_clients() -> list[str]:
    """Список всех клиентов"""
    clients = []
    for folder in RUNS_DIR.iterdir():
        if folder.is_dir() and not folder.name.startswith("_"):
            if (folder / CLIENT_INFO_FILE).exists():
                clients.append(folder.name)
    return clients

def list_workshops() -> list[str]:
    """Список всех цехов"""
    workshops = []
    for folder in MODULES_DIR.iterdir():
        if folder.is_dir() and (folder / "info.json").exists():
            workshops.append(folder.name)
    return workshops
