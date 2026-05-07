#!/usr/bin/env python3
# patch_slot_id.py — Привязка slot_id к памяти агентов
# Студия «Шесть Пальцев» · 2026
#
# Запуск: python patch_slot_id.py
# Делает бэкапы перед изменением каждого файла.
#
# Затрагивает 4 файла:
#   1. studio/cartridge.py          — прокидывает slot_id в state
#   2. studio/agent_feedback.py     — сохраняет slot_id в global_feedback
#   3. studio/reflection.py         — читает рефлексию с учётом slot_id
#   4. studio/workshop/pipeline.py  — передаёт slot_id при вызове save_feedback

import shutil
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════
# КОНФИГ
# ══════════════════════════════════════════════

SUFFIX = ".bak_slot_id"
DRY_RUN = False  # True = только показать что изменится, не писать

# ══════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════

def backup(path: Path):
    bak = path.with_suffix(path.suffix + SUFFIX)
    shutil.copy2(path, bak)
    print(f"  📦 Бэкап: {bak.name}")

def patch_file(path: Path, old: str, new: str, description: str) -> bool:
    """Заменяет old → new в файле. Возвращает True если замена сделана."""
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    
    content = path.read_text(encoding="utf-8")
    
    if old not in content:
        print(f"  ⚠️  Паттерн не найден ({description}) — возможно уже запатчено")
        return False
    
    if DRY_RUN:
        print(f"  🔍 [DRY RUN] Нашёл паттерн: {description}")
        return True
    
    backup(path)
    new_content = content.replace(old, new, 1)
    path.write_text(new_content, encoding="utf-8")
    print(f"  ✅ {description}")
    return True


# ══════════════════════════════════════════════
# ПАТЧ 1: studio/cartridge.py
# Добавляем self.state["_slot_id"] = self.slot_id
# в метод run() — сразу после _qa_agent
# ══════════════════════════════════════════════

def patch_cartridge():
    path = Path("studio/cartridge.py")
    print(f"\n[1/4] Патчим {path}")

    patch_file(
        path,
        old='        self.state["_qa_agent"] = getattr(self.manifest, "qa_agent", "A12")',
        new=(
            '        self.state["_qa_agent"] = getattr(self.manifest, "qa_agent", "A12")\n'
            '        self.state["_slot_id"] = self.slot_id  # ← slot_id для feedback/reflection'
        ),
        description='Добавлен self.state["_slot_id"] в run()',
    )


# ══════════════════════════════════════════════
# ПАТЧ 2: studio/agent_feedback.py
# 2a. save_feedback получает параметр slot_id
# 2b. _update_global получает параметр slot_id
# 2c. _update_global записывает данные в gf["slots"][slot_id]
# ══════════════════════════════════════════════

def patch_agent_feedback():
    path = Path("studio/agent_feedback.py")
    print(f"\n[2/4] Патчим {path}")

    # 2a. Сигнатура save_feedback
    patch_file(
        path,
        old='def save_feedback(client_slug: str, arthur_result: str | dict):',
        new='def save_feedback(client_slug: str, arthur_result: str | dict, slot_id: str = ""):',
        description='Параметр slot_id добавлен в save_feedback()',
    )

    # 2b. Вызов _update_global внутри save_feedback — передаём slot_id
    patch_file(
        path,
        old='    # Обновляем глобальный (студийный) feedback\n    _update_global(feedback)',
        new='    # Обновляем глобальный (студийный) feedback\n    _update_global(feedback, slot_id=slot_id)',
        description='Передан slot_id в _update_global()',
    )

    # 2c. Сигнатура _update_global
    patch_file(
        path,
        old='def _update_global(run_feedback: dict):',
        new='def _update_global(run_feedback: dict, slot_id: str = ""):',
        description='Параметр slot_id добавлен в _update_global()',
    )

    # 2d. Тело _update_global — добавляем запись по слоту
    # Вставляем ПЕРЕД финальным _save_global(gf)
    patch_file(
        path,
        old='    _save_global(gf)\n    print(f"[FEEDBACK] Глобальный обновлён: {gf[\'total_runs\']} ранов")',
        new=(
            '    # ══ slot_id binding: помним что происходило в каком цехе ══\n'
            '    if slot_id:\n'
            '        if "slots" not in gf:\n'
            '            gf["slots"] = {}\n'
            '        if slot_id not in gf["slots"]:\n'
            '            gf["slots"][slot_id] = {"runs": 0, "agents": {}}\n'
            '        gf["slots"][slot_id]["runs"] = gf["slots"][slot_id].get("runs", 0) + 1\n'
            '        for _aid, _rdata in run_feedback.get("agents", {}).items():\n'
            '            _sl_agents = gf["slots"][slot_id]["agents"]\n'
            '            if _aid not in _sl_agents:\n'
            '                _sl_agents[_aid] = {"runs": 0, "avg_score": 0.0, "total_score": 0.0, "last_problems": []}\n'
            '            _sla = _sl_agents[_aid]\n'
            '            _sla["runs"] += 1\n'
            '            _sla["total_score"] = _sla.get("total_score", 0.0) + _rdata.get("score", 5.0)\n'
            '            _sla["avg_score"] = round(_sla["total_score"] / _sla["runs"], 1)\n'
            '            _sla["last_problems"] = _rdata.get("problems", [])[:3]\n'
            '    # ══ end slot binding ══\n'
            '\n'
            '    _save_global(gf)\n'
            '    print(f"[FEEDBACK] Глобальный обновлён: {gf[\'total_runs\']} ранов")'
        ),
        description='Добавлена запись по slot_id в global_feedback["slots"]',
    )


# ══════════════════════════════════════════════
# ПАТЧ 3: studio/reflection.py
# get_reflection() принимает slot_id
# и при наличии — берёт данные из global_feedback["slots"]
# ══════════════════════════════════════════════

def patch_reflection():
    path = Path("studio/reflection.py")
    print(f"\n[3/4] Патчим {path}")

    # 3a. Сигнатура get_reflection
    patch_file(
        path,
        old='def get_reflection(agent_id: str) -> str:',
        new='def get_reflection(agent_id: str, slot_id: str = "") -> str:',
        description='Параметр slot_id добавлен в get_reflection()',
    )

    # 3b. В начале get_reflection — если есть slot_id, грузим из global_feedback["slots"]
    patch_file(
        path,
        old=(
            '    cache = _load_cache()\n'
            '    agent_data = cache.get("agents", {}).get(agent_id)\n'
            '\n'
            '    if not agent_data:\n'
            '        return ""'
        ),
        new=(
            '    cache = _load_cache()\n'
            '\n'
            '    # Если передан slot_id — приоритет слотовым данным\n'
            '    agent_data = None\n'
            '    if slot_id:\n'
            '        try:\n'
            '            import json as _json\n'
            '            _gf_path = GLOBAL_FEEDBACK_PATH\n'
            '            if _gf_path.exists():\n'
            '                _gf = _json.loads(_gf_path.read_text(encoding="utf-8"))\n'
            '                _slot_agents = _gf.get("slots", {}).get(slot_id, {}).get("agents", {})\n'
            '                _raw = _slot_agents.get(agent_id)\n'
            '                if _raw and _raw.get("runs", 0) >= MIN_RUNS_FOR_REFLECTION:\n'
            '                    agent_data = _extract_patterns(_raw)\n'
            '        except Exception:\n'
            '            pass\n'
            '\n'
            '    # Fallback — общие данные из кеша\n'
            '    if agent_data is None:\n'
            '        agent_data = cache.get("agents", {}).get(agent_id)\n'
            '\n'
            '    if not agent_data:\n'
            '        return ""'
        ),
        description='get_reflection() читает slot-специфичные данные при наличии slot_id',
    )


# ══════════════════════════════════════════════
# ПАТЧ 4: studio/workshop/pipeline.py
# При вызове save_feedback — передаём slot_id из state
# При вызове get_reflection — передаём slot_id из state
# ══════════════════════════════════════════════

def patch_pipeline():
    path = Path("studio/workshop/pipeline.py")
    print(f"\n[4/4] Патчим {path}")

    # 4a. save_feedback — добавляем slot_id
    patch_file(
        path,
        old=(
            '    if worker_id == qa_agent and client_slug != "_sandbox":\n'
            '        try:\n'
            '            save_feedback(client_slug, raw_result)\n'
            '            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug}")'
        ),
        new=(
            '    if worker_id == qa_agent and client_slug != "_sandbox":\n'
            '        try:\n'
            '            _slot_id_for_fb = state.get("_slot_id", "")\n'
            '            save_feedback(client_slug, raw_result, slot_id=_slot_id_for_fb)\n'
            '            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug} (slot: {_slot_id_for_fb or \'—\'})")'
        ),
        description='save_feedback() вызван с slot_id из state',
    )

    # 4b. get_reflection — добавляем slot_id
    patch_file(
        path,
        old='        reflection = get_reflection(worker_id)',
        new=(
            '        _slot_id_for_ref = state.get("_slot_id", "")\n'
            '        reflection = get_reflection(worker_id, slot_id=_slot_id_for_ref)'
        ),
        description='get_reflection() вызван с slot_id из state',
    )


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  ПАТЧ: slot_id привязка к памяти агентов")
    print(f"  Режим: {'DRY RUN (файлы не меняются)' if DRY_RUN else 'БОЕВОЙ'}")
    print(f"  Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # Проверяем что мы в корне проекта
    if not Path("studio").exists():
        print("\n❌ Папка 'studio' не найдена.")
        print("   Запускай скрипт из корневой папки проекта!")
        print("   Например: cd /path/to/project && python patch_slot_id.py")
        return

    patch_cartridge()
    patch_agent_feedback()
    patch_reflection()
    patch_pipeline()

    print("\n" + "=" * 55)
    if DRY_RUN:
        print("  ✅ DRY RUN завершён — файлы НЕ изменены")
    else:
        print("  ✅ ПАТЧ ПРИМЕНЁН")
        print()
        print("  Бэкапы сохранены с суффиксом:", SUFFIX)
        print("  Чтобы откатить — замени файлы из бэкапов:")
        print("    studio/cartridge.py.bak_slot_id        → cartridge.py")
        print("    studio/agent_feedback.py.bak_slot_id   → agent_feedback.py")
        print("    studio/reflection.py.bak_slot_id       → reflection.py")
        print("    studio/workshop/pipeline.py.bak_slot_id → pipeline.py")
        print()
        print("  Что изменилось:")
        print("  • cartridge.py    — state['_slot_id'] = slot_id при старте рана")
        print("  • agent_feedback  — global_feedback.json['slots'][slot_id] копит статистику")
        print("  • reflection.py   — рефлексия учитывает историю конкретного слота")
        print("  • pipeline.py     — save_feedback и get_reflection знают про слот")
    print("=" * 55)


if __name__ == "__main__":
    main()
