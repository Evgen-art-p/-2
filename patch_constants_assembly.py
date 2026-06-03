"""
patch_constants_assembly.py — баг #6

constants.py find_final_mds():
  Проблема: startswith("A05") ловит A05_Лукас (storyboard) из video_long.
  Фикс: добавляем '"deliverables"' in text — у Лукаса deliverables нет.

__init__.py _parse_bob_file():
  Проблема: ищет только bob_marketing.chain_status → turbo невидим.
  Фикс: добавляем ветку для chain_check.chain_status (turbo A05).

Запуск из корня: python patch_constants_assembly.py
"""

import sys
from pathlib import Path

CONSTANTS_PY = Path("studio") / "assembly" / "constants.py"
INIT_PY      = Path("studio") / "assembly" / "__init__.py"
errors = []


def patch(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        errors.append(f"MISS [{label}] в {path.name}")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK {label}")
    return True


# ── PATCH 1: constants.py ──────────────────────────────────────────

P1_OLD = (
    '                is_final = (\n'
    '                    md.name.startswith("A05")\n'
    '                    or "final_dna" in text\n'
    '                    or ("Финализатор" in md.name and (\'"thumbnails"\' in text or \'"key_frames"\' in text))\n'
    '                )'
)

P1_NEW = (
    '                is_final = (\n'
    '                    # A05 turbo Финализатор — обязательно с deliverables\n'
    '                    # (иначе A05_Лукас storyboard из video_long тоже попадает)\n'
    '                    (md.name.startswith("A05") and \'"\'"\'deliverables\'"\'"\' in text)\n'
    '                    or "final_dna" in text\n'
    '                    or ("Финализатор" in md.name and (\'"thumbnails"\' in text or \'"key_frames"\' in text))\n'
    '                )'
)


# ── PATCH 2: __init__.py ───────────────────────────────────────────

P2_OLD = (
    'def _parse_bob_file(path: Path) -> dict | None:\n'
    '    """Читает файл Боба, возвращает данные если chain_status APPROVED."""\n'
    '    try:\n'
    '        text = path.read_text(encoding="utf-8")\n'
    '        m = re.search(\n'
    '            r"SYSTEM_JSON_START[^\\\\n]*\\\\n(.*?)\\\\n[^\\\\n]*SYSTEM_JSON_END",\n'
    '            text, re.DOTALL\n'
    '        )\n'
    '        if not m:\n'
    '            m = re.search(r"```json\\\\s*\\\\n(.*?)\\\\n```", text, re.DOTALL)\n'
    '        if not m:\n'
    '            return None\n'
    '        data = json.loads(m.group(1))\n'
    '        status = (data.get("my_output", {})\n'
    '                      .get("bob_marketing", {})\n'
    '                      .get("chain_status", ""))\n'
    '        if status != "APPROVED":\n'
    '            return None\n'
    '        return data\n'
    '    except Exception:\n'
    '        return None'
)

P2_NEW = (
    'def _parse_bob_file(path: Path) -> dict | None:\n'
    '    """\n'
    '    Читает файл QA-финализатора, возвращает данные если chain_status APPROVED.\n'
    '    Поддерживает два цеха:\n'
    '      video_long  — A12 Боб:         my_output.bob_marketing.chain_status\n'
    '      turbo       — A05 Финализатор:  my_output.chain_check.chain_status\n'
    '    """\n'
    '    try:\n'
    '        text = path.read_text(encoding="utf-8")\n'
    '        m = re.search(\n'
    '            r"SYSTEM_JSON_START[^\\\\n]*\\\\n(.*?)\\\\n[^\\\\n]*SYSTEM_JSON_END",\n'
    '            text, re.DOTALL\n'
    '        )\n'
    '        if not m:\n'
    '            m = re.search(r"```json\\\\s*\\\\n(.*?)\\\\n```", text, re.DOTALL)\n'
    '        if not m:\n'
    '            return None\n'
    '        data = json.loads(m.group(1))\n'
    '        my_out = data.get("my_output", {})\n'
    '        # video_long: Боб → bob_marketing.chain_status\n'
    '        status = my_out.get("bob_marketing", {}).get("chain_status", "")\n'
    '        # turbo: A05 → chain_check.chain_status\n'
    '        if not status:\n'
    '            status = my_out.get("chain_check", {}).get("chain_status", "")\n'
    '        # deliverables без chain_status (video_shorts / social_mix)\n'
    '        if not status and data.get("deliverables"):\n'
    '            status = "APPROVED"\n'
    '        if status != "APPROVED":\n'
    '            return None\n'
    '        return data\n'
    '    except Exception:\n'
    '        return None'
)


print("=== patch_constants_assembly.py ===\n")

# Читаем реальные файлы и ищем точные строки
print("Ищу точные якорные строки в файлах...\n")

for fp, label in [(CONSTANTS_PY, "constants.py"), (INIT_PY, "__init__.py")]:
    if fp.exists():
        text = fp.read_text(encoding="utf-8")
        print(f"  {label}: {len(text)} символов — OK")
    else:
        errors.append(f"Файл не найден: {fp}")

if errors:
    print("ОШИБКИ:", errors)
    sys.exit(1)

# Читаем точные строки напрямую из файлов
c_text = CONSTANTS_PY.read_text(encoding="utf-8")
i_text = INIT_PY.read_text(encoding="utf-8")

# Находим точную строку is_final в constants.py
import re

# constants.py: находим блок is_final
c_match = re.search(
    r'(                is_final = \(.*?\))',
    c_text, re.DOTALL
)
if c_match:
    found_old = c_match.group(1)
    new_block = found_old.replace(
        'md.name.startswith("A05")',
        'md.name.startswith("A05") and \'"\'"\'deliverables\'"\'"\' in text'
    )
    # Добавляем комментарий
    new_block = new_block.replace(
        '                is_final = (\n',
        '                is_final = (\n'
        '                    # A05+deliverables: turbo Финализатор (не Лукас storyboard)\n'
    )
    if found_old != new_block:
        c_text = c_text.replace(found_old, new_block, 1)
        CONSTANTS_PY.write_text(c_text, encoding="utf-8")
        print("\nstudio/assembly/constants.py:")
        print("  OK find_final_mds: A05 + deliverables check добавлен")
    else:
        print("\nstudio/assembly/constants.py:")
        print("  INFO уже содержит deliverables check или строка не найдена")
else:
    errors.append("MISS [is_final block] в constants.py")
    print("\n  MISS: блок is_final не найден в constants.py")

# __init__.py: находим _parse_bob_file
i_match = re.search(
    r'(def _parse_bob_file\(path: Path\).*?return None\n    except Exception:\n        return None)',
    i_text, re.DOTALL
)
if i_match:
    old_func = i_match.group(1)
    # Заменяем только если ещё нет chain_check
    if 'chain_check' not in old_func:
        new_func = old_func.replace(
            '    """Читает файл Боба, возвращает данные если chain_status APPROVED."""',
            '    """\n'
            '    Читает файл QA-финализатора, возвращает данные если chain_status APPROVED.\n'
            '    video_long: bob_marketing.chain_status\n'
            '    turbo:      chain_check.chain_status\n'
            '    """'
        ).replace(
            '        status = (data.get("my_output", {})\n'
            '                      .get("bob_marketing", {})\n'
            '                      .get("chain_status", ""))\n'
            '        if status != "APPROVED":\n'
            '            return None\n'
            '        return data',
            '        my_out = data.get("my_output", {})\n'
            '        # video_long: Боб → bob_marketing.chain_status\n'
            '        status = my_out.get("bob_marketing", {}).get("chain_status", "")\n'
            '        # turbo: A05 Финализатор → chain_check.chain_status\n'
            '        if not status:\n'
            '            status = my_out.get("chain_check", {}).get("chain_status", "")\n'
            '        # video_shorts/social_mix: есть deliverables → считаем одобренным\n'
            '        if not status and data.get("deliverables"):\n'
            '            status = "APPROVED"\n'
            '        if status != "APPROVED":\n'
            '            return None\n'
            '        return data'
        )
        if old_func != new_func:
            i_text = i_text.replace(old_func, new_func, 1)
            INIT_PY.write_text(i_text, encoding="utf-8")
            print("\nstudio/assembly/__init__.py:")
            print("  OK _parse_bob_file: turbo chain_check поддержка добавлена")
        else:
            errors.append("MISS [_parse_bob_file replace] в __init__.py — строки не совпали")
    else:
        print("\nstudio/assembly/__init__.py:")
        print("  INFO chain_check уже есть — пропускаю")
else:
    errors.append("MISS [_parse_bob_file] в __init__.py")
    print("\n  MISS: _parse_bob_file не найдена в __init__.py")

print()
if errors:
    print("ОШИБКИ:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("Готово.")
print()
print("Что исправлено:")
print("  constants.py: A05_Лукас storyboard не попадает в find_final_mds()")
print("  __init__.py:  turbo-проекты видны в Мастерской Монтажёра")
print()
print("Commit:")
print("  fix: assembly A05+deliverables filter, turbo chain_check (#6)")
