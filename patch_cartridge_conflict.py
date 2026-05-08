# patch_cartridge_conflict.py
# Запустить: python patch_cartridge_conflict.py
# Добавляет Conflict System в cartridge.py (Этап 6)

from pathlib import Path

CARTRIDGE_PATH = Path("studio/cartridge.py")
BACKUP_PATH = Path("studio/cartridge.py.bak_conflict")

# Читаем оригинал
original = CARTRIDGE_PATH.read_text(encoding="utf-8")

# Бэкап
CARTRIDGE_PATH.rename(BACKUP_PATH)
print(f"✅ Бэкап: {BACKUP_PATH}")

# ═══════════════════════════════════════════════════════════
# ПАТЧ 1: Импорт conflict в начало файла
# ═══════════════════════════════════════════════════════════

# Ищем место после импорта modules_registry
import_marker = "from studio.modules_registry import ("
import_block_end = ")"

# Находим конец блока импорта modules_registry
pos = original.find(import_marker)
end_pos = original.find("\n\n", pos)  # следующая пустая строка после импорта

conflict_import = """
# ══ Conflict System (Этап 6) ══
try:
    from studio import conflict as _conflict
    _CONFLICT_ENABLED = True
except ImportError:
    _CONFLICT_ENABLED = False
"""

patched = original[:end_pos] + conflict_import + original[end_pos:]

# ═══════════════════════════════════════════════════════════
# ПАТЧ 2: Вызов conflict перед call_agent в run()
# ═══════════════════════════════════════════════════════════

# Ищем строку "Вызываем агента" в методе run()
old_call = """                # Вызываем агента
                human_text, meta, raw_result = await call_agent(
                    self.state, worker_id, context
                )"""

new_call = """                # ═══ Conflict System: divergent/adversarial режим ═══
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
                        )

                # Вызываем агента (или берём победителя конфликта)
                if conflict_result:
                    human_text, meta, raw_result = conflict_result["winner_result"]
                else:
                    human_text, meta, raw_result = await call_agent(
                        self.state, worker_id, context
                    )"""

if old_call in patched:
    patched = patched.replace(old_call, new_call)
    print("✅ Патч 2: вызов conflict в run()")
else:
    print("❌ Не найдено место для патча 2 в run()")
    print("   Ищу альтернативное место...")
    
    # Fallback: ищем по ключевой строке
    alt_marker = "human_text, meta, raw_result = await call_agent("
    if alt_marker in patched:
        # Находим строку и 2 строки выше (комментарий и сам вызов)
        lines = patched.split("\n")
        for i, line in enumerate(lines):
            if alt_marker in line:
                # Заменяем блок из 3 строк (комментарий + вызов + закрытие)
                lines[i-1] = "                # ═══ Conflict System: divergent/adversarial режим ═══"
                # Вставляем новый блок
                new_block = [
                    "                conflict_result = None",
                    "                if _CONFLICT_ENABLED and hasattr(self.manifest, 'conflict_mode'):",
                    "                    conflict_mode = getattr(self.manifest, 'conflict_mode', 'none')",
                    "                    if conflict_mode != 'none':",
                    "                        conflict_result = await _conflict.run_conflict_phase(",
                    "                            state=self.state,",
                    "                            phase_config={",
                    '                                "id": phase,',
                    '                                "conflict_mode": conflict_mode,',
                    '                                "agents": self.manifest.phases.get(phase, [worker_id]),',
                    "                            },",
                    "                            build_context_fn=build_agent_context,",
                    "                            call_agent_fn=call_agent,",
                    "                            slot_id=self.slot_id,",
                    "                        )",
                    "",
                    "                # Вызываем агента (или берём победителя конфликта)",
                    "                if conflict_result:",
                    '                    human_text, meta, raw_result = conflict_result["winner_result"]',
                    "                else:",
                    "                    human_text, meta, raw_result = await call_agent(",
                    '                        self.state, worker_id, context',
                    "                    )",
                ]
                # Удаляем старые строки и вставляем новые
                lines = lines[:i-1] + new_block + lines[i+3:]
                patched = "\n".join(lines)
                print("✅ Патч 2 (fallback): вызов conflict в run()")
                break
    else:
        print("❌ Критически не найдено место для патча 2")

# Сохраняем
CARTRIDGE_PATH.write_text(patched, encoding="utf-8")
print(f"✅ Сохранено: {CARTRIDGE_PATH}")
print("Готово! Conflict System интегрирована в cartridge.py")