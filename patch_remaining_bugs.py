"""
patch_remaining_bugs.py — оставшиеся баги

Баг #8  fal_client.py — дублирование CLIENTS_DIR (стр 37 и 43)
Баг #12 pipeline.py  — get_ole_memory_for_agent() не подключён
Задача 4 city_walker.py — highlight конфликтов/спасений в recent_events

Запуск из корня: python patch_remaining_bugs.py
"""

import sys
from pathlib import Path

FAL_PY      = Path("studio") / "fal_client.py"
PIPELINE_PY = Path("studio") / "workshop" / "pipeline.py"
WALKER_PY   = Path("studio") / "city_walker.py"
errors = []


def patch(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        errors.append(f"MISS [{label}] в {path.name}")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK {label}")
    return True


# ═══════════════════════════════════════════════════════
# БАГ #8 — fal_client.py: дублирование CLIENTS_DIR
# Строки 37-43:
#   ASSETS_DIR = Path("assets")
#   CLIENTS_DIR = Path("clients")   ← первое
#   _current_client_slug = None
#   CLIENTS_DIR = Path("clients")   ← дубль
# ═══════════════════════════════════════════════════════

P8_OLD = (
    'ASSETS_DIR = Path("assets")  # дефолт, перезаписывается при load_catalog\n'
    'CLIENTS_DIR = Path("clients")\n'
    '_current_client_slug = None\n'
    'CLIENTS_DIR = Path("clients")\n'
)
P8_NEW = (
    'ASSETS_DIR = Path("assets")  # дефолт, перезаписывается при load_catalog\n'
    'CLIENTS_DIR = Path("clients")\n'
    '_current_client_slug = None\n'
)

# ═══════════════════════════════════════════════════════
# БАГ #12 — pipeline.py: get_ole_memory_for_agent()
# Подключаем в build_agent_context() после soul_ctx
# Место: сразу после блока "Рюкзак Знаний — данные с Маяка"
# ═══════════════════════════════════════════════════════

P12_OLD = (
    "    # ══ Гавань Смыслов — RAG по внутренним знаниям ══\n"
    "    if _HARBOR_ENABLED:\n"
    "        harbor_ctx = get_harbor_knowledge(\n"
    "            worker_id,\n"
    "            state.get(\"active_dept\", \"\"),\n"
    "            task_context=state.get(\"master_brief\", \"\")[:300],\n"
    "        )\n"
    "        if harbor_ctx:\n"
    "            context += harbor_ctx + \"\\n\\n\"\n"
    "            print(f\"[РЮКЗАК] ⚓ {worker_id} получил знания из Гавани ({len(harbor_ctx)} симв.)\")\n"
    "    # ══ END ══"
)

P12_NEW = (
    "    # ══ Гавань Смыслов — RAG по внутренним знаниям ══\n"
    "    if _HARBOR_ENABLED:\n"
    "        harbor_ctx = get_harbor_knowledge(\n"
    "            worker_id,\n"
    "            state.get(\"active_dept\", \"\"),\n"
    "            task_context=state.get(\"master_brief\", \"\")[:300],\n"
    "        )\n"
    "        if harbor_ctx:\n"
    "            context += harbor_ctx + \"\\n\\n\"\n"
    "            print(f\"[РЮКЗАК] ⚓ {worker_id} получил знания из Гавани ({len(harbor_ctx)} симв.)\")\n"
    "    # ══ END ══\n"
    "\n"
    "    # ══ Память города (Оле) — культурное ядро ══\n"
    "    # get_ole_memory_for_agent() ищет в city_memory.jsonl записи\n"
    "    # релевантные текущей задаче. Агент получает живую мудрость города.\n"
    "    try:\n"
    "        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem\n"
    "        _ole_query = state.get(\"master_brief\", \"\")[:200] or worker_id\n"
    "        _ole_ctx = _ole_mem(query=_ole_query, max_chars=1200)\n"
    "        if _ole_ctx:\n"
    "            context += _ole_ctx + \"\\n\\n\"\n"
    "            print(f\"[ОЛЕ→РЮКЗАК] 🧠 {worker_id} получил память города\")\n"
    "    except Exception as _ole_err:\n"
    "        print(f\"[ОЛЕ] ⚠ {worker_id}: {_ole_err}\")\n"
    "    # ══ END Оле ══"
)

# ═══════════════════════════════════════════════════════
# ЗАДАЧА 4 — city_walker.py: highlight в recent_events
# После вечерней прогулки — собираем интересные встречи
# из сегодняшних хроник и добавляем в city_state
# Место: в конце run_city_walk_evening(), перед return results
# ═══════════════════════════════════════════════════════

P4_OLD = (
    "    # Добавляем событие в историю города\n"
    "    dept_label = workshops[0] if workshops and len(workshops) == 1 else \"цех\"\n"
    "    add_city_event(f\"Агенты {dept_label} вернулись с вечерней прогулки\")"
)

P4_NEW = (
    "    # Добавляем событие в историю города\n"
    "    dept_label = workshops[0] if workshops and len(workshops) == 1 else \"цех\"\n"
    "    add_city_event(f\"Агенты {dept_label} вернулись с вечерней прогулки\")\n"
    "\n"
    "    # ══ HIGHLIGHT: самые интересные встречи всплывают на карте · Задача 4 ══\n"
    "    # Читаем сегодняшние хроники — конфликты и спасения сразу видны Садовнику.\n"
    "    # Не надо идти в вкладку хроник вручную.\n"
    "    try:\n"
    "        import json as _hj\n"
    "        from datetime import datetime as _hdt\n"
    "        _today = _hdt.now().strftime(\"%Y-%m-%d\")\n"
    "        _chron_dir = Path(\"studio/city_chronicles\") / _today\n"
    "        if _chron_dir.exists():\n"
    "            _highlights = []\n"
    "            for _fp in sorted(_chron_dir.glob(\"*.json\"), reverse=True)[:20]:\n"
    "                try:\n"
    "                    _sc = _hj.loads(_fp.read_text(encoding=\"utf-8\"))\n"
    "                    if _sc.get(\"schema\") != \"meeting_v1\":\n"
    "                        continue\n"
    "                    _itype = _sc.get(\"interaction\", {}).get(\"type\", \"\")\n"
    "                    if _itype in (\"conflict\", \"rescue\", \"praise\"):\n"
    "                        _p = _sc.get(\"participants\", {})\n"
    "                        _a = _p.get(\"a\", {}).get(\"name\", \"?\")\n"
    "                        _b = _p.get(\"b\", {}).get(\"name\", \"?\")\n"
    "                        _loc = _sc.get(\"location\", \"\")\n"
    "                        _icons = {\"conflict\": \"⚡\", \"rescue\": \"🤝\", \"praise\": \"⭐\"}\n"
    "                        _icon = _icons.get(_itype, \"💬\")\n"
    "                        _highlights.append(\n"
    "                            f\"{_icon} {_itype}: {_a} и {_b} в {_loc}\"\n"
    "                        )\n"
    "                except Exception:\n"
    "                    continue\n"
    "            for _hl in _highlights[:3]:  # не больше 3 в events\n"
    "                add_city_event(_hl)\n"
    "                print(f\"[CITY] 📰 Highlight: {_hl}\")\n"
    "    except Exception as _hl_err:\n"
    "        print(f\"[CITY] ⚠ Highlight: {_hl_err}\")\n"
    "    # ══ END HIGHLIGHT ══"
)


print("=== patch_remaining_bugs.py ===\n")

print("studio/fal_client.py:")
patch(FAL_PY, P8_OLD, P8_NEW, "#8 убрано дублирование CLIENTS_DIR")

print("\nstudio/workshop/pipeline.py:")
patch(PIPELINE_PY, P12_OLD, P12_NEW, "#12 get_ole_memory_for_agent() подключён в pipeline")

print("\nstudio/city_walker.py:")
patch(WALKER_PY, P4_OLD, P4_NEW, "Задача 4 highlight конфликтов/спасений в recent_events")

print()
if errors:
    print("ОШИБКИ:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("Готово. 3 патча применены.")
print()
print("Что исправлено:")
print("  #8  fal_client.py: убрано дублирование CLIENTS_DIR")
print("  #12 pipeline.py: Оле даёт агентам память города при каждом ране")
print("  T4  city_walker.py: conflict/rescue/praise всплывают на карте Кабинета")
print()
print("Commit:")
print("  fix: CLIENTS_DIR duplicate (#8), ole memory in pipeline (#12), highlight events (T4)")
