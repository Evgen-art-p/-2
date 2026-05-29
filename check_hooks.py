#!/usr/bin/env python3
"""Проверяет состояние hooks.py после патчей. Запуск из корня репо."""
from pathlib import Path

HOOKS_PATH = Path("studio/modules/video_long/hooks.py")

if not HOOKS_PATH.exists():
    print(f"❌ Файл не найден: {HOOKS_PATH}")
    exit(1)

text = HOOKS_PATH.read_text(encoding="utf-8")
lines = text.splitlines()

def find_in_code(marker):
    """Ищет маркер только в строках кода (не в комментариях и не в docstring)."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if marker in line:
            return True
    return False

print("=" * 55)
print("ПРОВЕРКА hooks.py после патчей")
print("=" * 55)

all_ok = True

# 1. veo3_prompts должно отсутствовать В КОДЕ (не в комментариях)
if find_in_code('deliverables["veo3_prompts"]'):
    print('  ❌ deliverables["veo3_prompts"] в коде — патч не применён!')
    all_ok = False
else:
    print('  ✅ deliverables["veo3_prompts"] убран из кода')

# 2. video_clips должно быть В КОДЕ
if find_in_code('deliverables["video_clips"]'):
    print('  ✅ deliverables["video_clips"] есть в коде')
else:
    print('  ❌ deliverables["video_clips"] не найден — патч не применён!')
    all_ok = False

# 3. video_path в коде
if find_in_code('"video_path"'):
    print('  ✅ video_path есть в коде')
else:
    print('  ❌ video_path не найден')
    all_ok = False

# 4. _sam_generate_audio определена
if 'def _sam_generate_audio' in text:
    print('  ✅ _sam_generate_audio() определена')
else:
    print('  ❌ _sam_generate_audio() отсутствует')
    all_ok = False

# 5. A10 подключён в on_after_agent
if 'worker_id == "A10"' in text:
    print('  ✅ A10 подключён в on_after_agent')
else:
    print('  ❌ A10 не подключён')
    all_ok = False

print("=" * 55)
if all_ok:
    print("🎉 Все три патча применены корректно!")
    print("   Готово к первому рану video_long.")
else:
    print("⚠️  Есть незакрытые патчи — смотри выше.")
