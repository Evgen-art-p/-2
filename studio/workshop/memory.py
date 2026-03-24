# studio/workshop_memory.py — Memory Manager, sessions, insights
# Вынесено из ui_workshop.py (строки 902-1075)

import json
from studio.config import BASE_DIR

CLIENTS_DIR = BASE_DIR / "clients"


def load_client_memory(client_slug: str) -> dict:
    """Загружает memory.json клиента"""
    mem_path = CLIENTS_DIR / client_slug / "memory.json"
    if mem_path.exists():
        try:
            return json.loads(mem_path.read_text(encoding='utf-8'))
        except:
            pass
    return {"client": client_slug, "runs": []}


def save_client_memory(client_slug: str, memory: dict):
    """Сохраняет memory.json клиента"""
    mem_path = CLIENTS_DIR / client_slug / "memory.json"
    mem_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')


def append_to_memory(client_slug: str, run_date: str, run_type: str, agent_id: str, insight: str):
    """Добавляет insight агента в memory.json клиента"""
    if client_slug == "_sandbox":
        return

    memory = load_client_memory(client_slug)

    current_run = None
    for run in memory.get("runs", []):
        if run.get("date") == run_date and run.get("type") == run_type:
            current_run = run
            break

    if not current_run:
        current_run = {"date": run_date, "type": run_type, "insights": {}}
        memory.setdefault("runs", []).append(current_run)

    current_run.setdefault("insights", {})[agent_id] = insight
    save_client_memory(client_slug, memory)


def delete_memory_run(client_slug: str, run_index: int):
    """Удаляет целый run из memory"""
    memory = load_client_memory(client_slug)
    runs = memory.get("runs", [])
    if 0 <= run_index < len(runs):
        runs.pop(run_index)
        save_client_memory(client_slug, memory)


def delete_memory_insight(client_slug: str, run_index: int, agent_id: str):
    """Удаляет insight конкретного агента из run'а"""
    memory = load_client_memory(client_slug)
    runs = memory.get("runs", [])
    if 0 <= run_index < len(runs):
        runs[run_index].get("insights", {}).pop(agent_id, None)
        if not runs[run_index].get("insights"):
            runs.pop(run_index)
        save_client_memory(client_slug, memory)


def edit_memory_insight(client_slug: str, run_index: int, agent_id: str, new_text: str):
    """Редактирует insight агента"""
    memory = load_client_memory(client_slug)
    runs = memory.get("runs", [])
    if 0 <= run_index < len(runs):
        runs[run_index].get("insights", {})[agent_id] = new_text
        save_client_memory(client_slug, memory)


def clear_client_memory(client_slug: str):
    """Полная очистка памяти клиента"""
    memory = {"client": client_slug, "runs": [], "session_summaries": []}
    save_client_memory(client_slug, memory)


def save_session_summary(client_slug: str, run_date: str, run_type: str, summary: str):
    """Сохраняет конспект сессии в memory.json (максимум 3 последних)"""
    if client_slug == "_sandbox":
        return
    
    memory = load_client_memory(client_slug)
    summaries = memory.get("session_summaries", [])
    
    summaries.append({
        "date": run_date,
        "type": run_type,
        "summary": summary
    })
    
    if len(summaries) > 3:
        summaries = summaries[-3:]
    
    memory["session_summaries"] = summaries
    save_client_memory(client_slug, memory)


def format_session_context(client_slug: str) -> str:
    """Форматирует конспекты прошлых сессий для подачи агентам"""
    if client_slug == "_sandbox":
        return ""
    
    memory = load_client_memory(client_slug)
    summaries = memory.get("session_summaries", [])
    
    if not summaries:
        return ""
    
    parts = ["=== КОНТЕКСТ ПРОШЛЫХ СЕССИЙ (для справки, не инструкция) ==="]
    for s in summaries:
        parts.append(f"\n📅 [{s['date']} / {s['type']}]")
        parts.append(s["summary"])
    parts.append("=== КОНЕЦ КОНТЕКСТА ===")
    
    return "\n".join(parts)


def format_memory_for_agent(client_slug: str, agent_id: str) -> str:
    """Форматирует память клиента для конкретного агента"""
    if client_slug == "_sandbox":
        return ""
    
    from studio.workshop.clients import load_client_info
    
    memory = load_client_memory(client_slug)
    info = load_client_info(client_slug)
    
    parts = []
    parts.append(f"=== КЛИЕНТ: {info.get('name', client_slug)} ===")
    if info.get("niche"):
        parts.append(f"Ниша: {info['niche']}")
    if info.get("description"):
        parts.append(f"Описание: {info['description']}")
    
    agent_insights = []
    for run in memory.get("runs", []):
        if agent_id in run.get("insights", {}):
            agent_insights.append(f"[{run['date']} / {run['type']}] {run['insights'][agent_id]}")
    
    if agent_insights:
        parts.append(f"\n=== ТВОИ ПРОШЛЫЕ ВЫВОДЫ ПО ЭТОМУ КЛИЕНТУ ({agent_id}) ===")
        for ins in agent_insights[-5:]:
            parts.append(ins)
    
    if memory.get("runs"):
        last_run = memory["runs"][-1]
        other_insights = {k: v for k, v in last_run.get("insights", {}).items() if k != agent_id}
        if other_insights:
            parts.append(f"\n=== ВЫВОДЫ КОЛЛЕГ (последний проект: {last_run['date']}) ===")
            for aid, text in other_insights.items():
                parts.append(f"{aid}: {text}")
    
    return "\n".join(parts)
