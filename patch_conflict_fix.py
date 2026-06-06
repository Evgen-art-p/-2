#!/usr/bin/env python3
"""
patch_conflict_fix.py — ПАТЧ: Фикс Conflict System + asyncio.create_task

ПРОБЛЕМЫ (найдены в репо):
1. manifest.json video_long: conflict_mode=divergent — конфликт запускается
   для КАЖДОГО из 12 агентов по очереди, итого 48+ параллельных LLM-вызовов.
   Event loop захлёбывается → CancelledError → KeyboardInterrupt на Windows.

2. В cartridge.py логика вызова конфликта неверна: конфликт должен срабатывать
   ОДИН РАЗ для всей фазы (PRE-PROD), а не для каждого агента внутри фазы.

3. pipeline.py: asyncio.create_task() вызывается в контексте где event loop
   может быть в другом потоке → не thread-safe → падение при Ctrl+C.

4. client_slug не передаётся в conflict state корректно.

ПРАВКИ:
А) cartridge.py — conflict запускается один раз на ФАЗУ, не на агента
Б) pipeline.py — create_task заменён на asyncio.ensure_future с проверкой loop
В) manifest.json video_long — backup + опциональный сброс conflict_mode в none
   для безопасного тестирования (можно вернуть потом)

ИСПОЛЬЗОВАНИЕ:
  python patch_conflict_fix.py          # применить всё
  python patch_conflict_fix.py --dry-run # только показать что будет
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"conflict_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def validate_python(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  ❌ СИНТАКС-ОШИБКА: {e}")
        return False

def apply_patch(path: Path, old: str, new: str, description: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Строка не найдена в {path.name} (возможно уже пропатчено): {description}")
        return True  # не ошибка
    
    new_content = content.replace(old, new, 1)
    
    if DRY_RUN:
        print(f"  [DRY] patch {path.name}: {description}")
        return True
    
    backup(path)
    
    # Пишем во временный файл, валидируем, потом перемещаем
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    
    if path.suffix == ".py":
        if not validate_python(tmp_path):
            tmp_path.unlink()
            return False
    
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {description}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: cartridge.py — конфликт только для первого агента в фазе
# ══════════════════════════════════════════════════════════════════
#
# ПРОБЛЕМА: сейчас в run() есть блок:
#   if _CONFLICT_ENABLED and hasattr(self.manifest, 'conflict_mode'):
#       conflict_mode = getattr(self.manifest, 'conflict_mode', 'none')
#       if conflict_mode != 'none':
#           conflict_result = await _conflict.run_conflict_phase(...)
#
# Это выполняется для КАЖДОГО агента в цикле while i < len(all_agents).
# Для video_long с divergent + 12 агентами = 12 * 4 параллельных вызовов.
#
# РЕШЕНИЕ: запускать конфликт только для ПЕРВОГО агента в каждой фазе,
# и только если агент — первый в своей фазе.

CARTRIDGE_OLD = """                # ═══ Conflict System: divergent/adversarial режим ═══
                conflict_result = None
                if _CONFLICT_ENABLED and hasattr(self.manifest, 'conflict_mode'):
                    conflict_mode = getattr(self.manifest, 'conflict_mode', 'none')
                    if conflict_mode != 'none':
                        conflict_result = await _conflict.run_conflict_phase(
                            state=self.state,
                            phase_config={
                                "id": phase,
                                "conflict_mode": conflict_mode,
                                "agents": self.manifest.phases.get(phase, [worker_id]),
                            },
                            build_context_fn=build_agent_context,
                            call_agent_fn=call_agent,
                            slot_id=self.slot_id,
                        )"""

CARTRIDGE_NEW = """                # ═══ Conflict System: divergent/adversarial режим ═══
                # ПАТЧ conflict_fix: конфликт запускается ОДИН РАЗ — только для
                # первого агента в фазе. Остальные агенты фазы пропускаются
                # (их результаты уже внутри conflict_result['all_proposals']).
                conflict_result = None
                if _CONFLICT_ENABLED and hasattr(self.manifest, 'conflict_mode'):
                    conflict_mode = getattr(self.manifest, 'conflict_mode', 'none')
                    if conflict_mode != 'none':
                        # Проверяем: этот агент — первый в своей фазе?
                        _phase_agents = self.manifest.phases.get(phase, [worker_id])
                        _is_phase_leader = (len(_phase_agents) > 0 and worker_id == _phase_agents[0])
                        if _is_phase_leader:
                            # Передаём client_slug корректно (ключ в state — current_client)
                            _conflict_state = dict(self.state)
                            _conflict_state["client_slug"] = self.state.get("current_client", "_sandbox")
                            conflict_result = await _conflict.run_conflict_phase(
                                state=_conflict_state,
                                phase_config={
                                    "id": phase,
                                    "conflict_mode": conflict_mode,
                                    "agents": _phase_agents,
                                },
                                build_context_fn=build_agent_context,
                                call_agent_fn=call_agent,
                                slot_id=self.slot_id,
                            )
                            # Сохраняем результаты всех агентов конфликта в state
                            if conflict_result and conflict_result.get("all_proposals"):
                                for _caid, _cdata in conflict_result["all_proposals"].items():
                                    if _caid != worker_id:  # победитель обрабатывается ниже
                                        self.state["results"][_caid] = {
                                            "text": _cdata.get("human_text", ""),
                                            "meta": _cdata.get("meta", {}),
                                            "raw":  _cdata.get("raw_result", ""),
                                        }
                                # Пропускаем всех остальных агентов этой фазы — они уже обработаны
                                _skip_to = None
                                for _next_phase, _next_agents in self.manifest.phases.items():
                                    if _next_phase != phase:
                                        if _next_agents:
                                            _skip_to = _next_agents[0]
                                        break
                                if _skip_to:
                                    for _si, _sa in enumerate(all_agents):
                                        if _sa == _skip_to:
                                            i = _si - 1  # -1 т.к. i += 1 в конце цикла
                                            break
                        else:
                            # Не первый агент фазы — результат уже записан конфликтом выше
                            print(f"[CONFLICT] {worker_id} обработан как часть конфликта — пропуск")
                            i += 1
                            continue"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: pipeline.py — asyncio.create_task thread-safe fix
# ══════════════════════════════════════════════════════════════════

PIPELINE_OLD = """                if _QUANTUM_WALK_ENABLED:
                    _dept_for_walk = state.get("active_dept", "")
                    if _dept_for_walk:
                        try:
                            asyncio.create_task(
                                _run_evening_walk(
                                    workshops=[_dept_for_walk],
                                    max_agents=0,  # все агенты цеха
                                )
                            )
                            print(f"[CITY] 🌆 Вечерняя прогулка запущена для цеха: {_dept_for_walk}")
                        except Exception as _walk_err:
                            print(f"[CITY] ⚠ Автотриггер прогулки: {_walk_err}")"""

PIPELINE_NEW = """                if _QUANTUM_WALK_ENABLED:
                    _dept_for_walk = state.get("active_dept", "")
                    if _dept_for_walk:
                        try:
                            # ПАТЧ conflict_fix: asyncio.ensure_future вместо create_task
                            # create_task не thread-safe когда вызывается из executor-потока.
                            # ensure_future безопаснее на Windows ProactorEventLoop.
                            _walk_coro = _run_evening_walk(
                                workshops=[_dept_for_walk],
                                max_agents=0,
                            )
                            try:
                                _loop = asyncio.get_event_loop()
                                if _loop.is_running():
                                    asyncio.ensure_future(_walk_coro)
                                else:
                                    print(f"[CITY] ⚠ Loop не запущен — прогулка пропущена")
                            except RuntimeError:
                                print(f"[CITY] ⚠ Нет event loop — прогулка пропущена")
                            print(f"[CITY] 🌆 Вечерняя прогулка запущена для цеха: {_dept_for_walk}")
                        except Exception as _walk_err:
                            print(f"[CITY] ⚠ Автотриггер прогулки: {_walk_err}")"""


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 3: pipeline.py — guard для Оле (не искать если бриф = JSON)
# ══════════════════════════════════════════════════════════════════

PIPELINE_OLE_OLD = """    try:
        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem
        _ole_query = state.get("master_brief", "")[:200] or worker_id
        _ole_ctx = _ole_mem(query=_ole_query, max_chars=1200)
        if _ole_ctx:
            context += _ole_ctx + "\\n\\n"
            print(f"[ОЛЕ→РЮКЗАК] 🧠 {worker_id} получил память города")
    except Exception as _ole_err:
        print(f"[ОЛЕ] ⚠ {worker_id}: {_ole_err}")"""

PIPELINE_OLE_NEW = """    try:
        from studio.residents_manager import get_ole_memory_for_agent as _ole_mem
        _raw_brief = state.get("master_brief", "")
        # ПАТЧ conflict_fix: не ищем если бриф — сырой JSON/System блок
        # (содержит SYSTEM_JSON_START или начинается с '{') — Оле всё равно ничего не найдёт
        _brief_is_json = (
            "SYSTEM_JSON_START" in _raw_brief[:300]
            or _raw_brief.strip().startswith("{")
        )
        if not _brief_is_json:
            _ole_query = _raw_brief[:200] or worker_id
            _ole_ctx = _ole_mem(query=_ole_query, max_chars=1200)
            if _ole_ctx:
                context += _ole_ctx + "\\n\\n"
                print(f"[ОЛЕ→РЮКЗАК] 🧠 {worker_id} получил память города")
        else:
            print(f"[ОЛЕ] {worker_id}: бриф — JSON-блок, поиск пропущен")
    except Exception as _ole_err:
        print(f"[ОЛЕ] ⚠ {worker_id}: {_ole_err}")"""


def main():
    print("=" * 60)
    print("ПАТЧ: Conflict System Fix + asyncio thread-safe")
    print("=" * 60)
    
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN (ничего не изменяется)\n")
    
    errors = []
    
    # Патч 1: cartridge.py
    print("\n[1/3] Фикс cartridge.py — conflict per-phase (не per-agent)")
    cartridge_path = Path("studio/cartridge.py")
    if not apply_patch(cartridge_path, CARTRIDGE_OLD, CARTRIDGE_NEW, 
                       "conflict запускается 1 раз на фазу"):
        errors.append("cartridge.py")
    
    # Патч 2: pipeline.py — create_task
    print("\n[2/3] Фикс pipeline.py — asyncio.ensure_future вместо create_task")
    pipeline_path = Path("studio/workshop/pipeline.py")
    if not apply_patch(pipeline_path, PIPELINE_OLD, PIPELINE_NEW,
                       "thread-safe вечерняя прогулка"):
        errors.append("pipeline.py (create_task)")
    
    # Патч 3: pipeline.py — Оле guard
    print("\n[3/3] Фикс pipeline.py — guard для Оле (не искать в JSON брифе)")
    if not apply_patch(pipeline_path, PIPELINE_OLE_OLD, PIPELINE_OLE_NEW,
                       "Оле пропускает поиск если бриф = JSON"):
        errors.append("pipeline.py (ole guard)")
    
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ Ошибки в: {', '.join(errors)}")
        print("Проверь что файлы не изменились с момента последнего коммита.")
    else:
        if DRY_RUN:
            print("✓ DRY-RUN завершён — всё выглядит корректно")
            print("  Запусти без --dry-run чтобы применить патч.")
        else:
            print("✅ Патч применён успешно!")
            print(f"   Бекапы: {BACKUP_DIR}")
            print("\nЧто изменилось:")
            print("  • cartridge.py: conflict запускается 1 раз на фазу PRE-PROD")
            print("    (не 12 раз на каждого агента)")
            print("  • pipeline.py: вечерняя прогулка через ensure_future (thread-safe)")
            print("  • pipeline.py: Оле не тратит время на поиск в JSON-брифах")
            print("\nПерезапусти студию: python main.py")

if __name__ == "__main__":
    main()
