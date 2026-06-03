"""
patch_deliverables_json.py
==========================
Два изменения:

1. studio/modules/video_long/hooks.py
   Добавляет функцию _save_deliverables() и её вызов в _bob_finalize().
   После сборки deliverables Боб сохраняет runs/{project_id}/deliverables.json.

2. studio/assembly/__init__.py
   _find_projects() переключается с парсинга .md файлов на чтение deliverables.json.
   _parse_bob_file() остаётся в файле, но больше не вызывается (на пенсии).
"""

from pathlib import Path
import sys

HOOKS_PATH  = Path("studio/modules/video_long/hooks.py")
INIT_PATH   = Path("studio/assembly/__init__.py")

ok_count  = 0
err_count = 0


def patch(path: Path, old: str, new: str, label: str):
    global ok_count, err_count
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"  MISS [{label}] — якорная строка не найдена в {path.name}")
        err_count += 1
        return
    if new.strip() in text:
        print(f"  SKIP [{label}] — патч уже применён")
        ok_count += 1
        return
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK   [{label}]")
    ok_count += 1


# ════════════════════════════════════════════════════════════════════
# ПАТЧ 1 — hooks.py: добавляем _save_deliverables() и вызов в _bob_finalize
# ════════════════════════════════════════════════════════════════════

print(f"\n=== Патч 1: {HOOKS_PATH} ===")

# 1a. Добавляем вызов _save_deliverables() в _bob_finalize()
# Вставляем сразу после строки с print("✅ deliverables собраны")

OLD_FINALIZE = '''\
    _bob_collect_media(chain, deliverables)
    data["deliverables"] = deliverables
    _update_state(state, data)
    print("[EPISODE A12] ✅ deliverables собраны")

    cultural_trace = _bob_cultural_trace(state)'''

NEW_FINALIZE = '''\
    _bob_collect_media(chain, deliverables)
    data["deliverables"] = deliverables
    _update_state(state, data)
    print("[EPISODE A12] ✅ deliverables собраны")

    # Сохраняем deliverables на диск — Мастерская читает отсюда
    _save_deliverables(state, deliverables)

    cultural_trace = _bob_cultural_trace(state)'''

patch(HOOKS_PATH, OLD_FINALIZE, NEW_FINALIZE, "_bob_finalize: вызов _save_deliverables")

# 1b. Добавляем саму функцию _save_deliverables() перед разделом УТИЛИТЫ
# Вставляем перед строкой "# ═══ УТИЛИТЫ"

OLD_UTILS_HEADER = '''\
# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════


def _generate_with_vision_check('''

NEW_UTILS_HEADER = '''\
# ═══════════════════════════════════════════════════════════════════
# СОХРАНЕНИЕ DELIVERABLES НА ДИСК
# ═══════════════════════════════════════════════════════════════════

def _save_deliverables(state: dict, deliverables: dict) -> None:
    """
    Сохраняет deliverables в runs/{project_id}/deliverables.json.

    Это единственный источник правды для Мастерской (assembly/__init__.py).
    Записываем сюда всё что нужно UI:
      - project_id, platform, slot_id
      - video_clips (с video_path)
      - key_frames (с path)
      - thumbnail (variant_a/variant_b с path)
      - audio (music.audio_path, sfx_list, vo_lines)
      - saved_at — метка времени

    Файл пишется атомарно: сначала во временный, потом переименовываем.
    """
    project_id = (
        deliverables.get("project_id")
        or state.get("project_id", "")
    )
    if not project_id:
        print("[EPISODE A12] ⚠️  project_id пуст — deliverables.json не сохраняю")
        return

    runs_dir = Path("runs") / project_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Добавляем служебные поля для UI
    payload = dict(deliverables)
    payload["slot_id"]   = state.get("_slot_id", "video_long")
    payload["saved_at"]  = datetime.datetime.utcnow().isoformat()

    dest = runs_dir / "deliverables.json"
    tmp  = runs_dir / "deliverables.json.tmp"

    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(dest)
        clips_ok = sum(1 for c in payload.get("video_clips", []) if c.get("video_path"))
        clips_total = len(payload.get("video_clips", []))
        print(f"[EPISODE A12] 💾 deliverables.json → {dest}  "
              f"клипов: {clips_ok}/{clips_total}")
    except Exception as e:
        print(f"[EPISODE A12] ❌ deliverables.json не записан: {e}")
        if tmp.exists():
            tmp.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════


def _generate_with_vision_check('''

patch(HOOKS_PATH, OLD_UTILS_HEADER, NEW_UTILS_HEADER, "_save_deliverables: новая функция")


# ════════════════════════════════════════════════════════════════════
# ПАТЧ 2 — __init__.py: _find_projects читает deliverables.json
# ════════════════════════════════════════════════════════════════════

print(f"\n=== Патч 2: {INIT_PATH} ===")

OLD_FIND_PROJECTS = '''\
def _find_projects() -> list[dict]:
    """Все проекты из runs/ с APPROVED от Боба."""
    projects = []
    if not RUNS_DIR.exists():
        return projects

    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        bob_files = (
            list(run_dir.glob("*A12*.md")) +
            list(run_dir.glob("*[Bb]ob*.md"))
        )
        for bob_file in bob_files:
            data = _parse_bob_file(bob_file)
            if not data:
                continue
            deliverables = data.get("deliverables", {})
            if not deliverables:
                continue
            final_dna  = data.get("my_output", {}).get("final_dna", {})
            project_id = deliverables.get("project_id", run_dir.name)
            assembly   = get_assembly_status(project_id)
            projects.append({
                "project_id":      project_id,
                "platform":        deliverables.get("platform", "—"),
                "slot":            final_dna.get("mode", "—").lower(),
                "clips_count":     len(deliverables.get("video_clips", [])),
                "frames_count":    len(deliverables.get("key_frames", [])),
                "has_audio":       bool(deliverables.get("audio")),
                "assembly_status": assembly.get("status", "NOT_ASSEMBLED"),
                "deliverables":    deliverables,
                "final_dna":       final_dna,
            })
            break  # один проект из папки

    return projects'''

NEW_FIND_PROJECTS = '''\
def _find_projects() -> list[dict]:
    """Все проекты из runs/ у которых есть deliverables.json от Боба."""
    projects = []
    if not RUNS_DIR.exists():
        return projects

    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue

        # Читаем deliverables.json — единственный источник правды
        d_path = run_dir / "deliverables.json"
        if not d_path.exists():
            continue

        try:
            deliverables = json.loads(d_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[МАСТЕРСКАЯ] ⚠️  {d_path}: не читается — {e}")
            continue

        if not deliverables:
            continue

        project_id = deliverables.get("project_id", run_dir.name)
        assembly   = get_assembly_status(project_id)

        projects.append({
            "project_id":      project_id,
            "platform":        deliverables.get("platform", "—"),
            "slot":            deliverables.get("slot_id", "—"),
            "clips_count":     len(deliverables.get("video_clips", [])),
            "frames_count":    len(deliverables.get("key_frames", [])),
            "has_audio":       bool(deliverables.get("audio")),
            "assembly_status": assembly.get("status", "NOT_ASSEMBLED"),
            "deliverables":    deliverables,
            # final_dna оставляем пустым — он не нужен UI Мастерской
            "final_dna":       {},
        })

    return projects'''

patch(INIT_PATH, OLD_FIND_PROJECTS, NEW_FIND_PROJECTS, "_find_projects: читает deliverables.json")


# ════════════════════════════════════════════════════════════════════
# ИТОГ
# ════════════════════════════════════════════════════════════════════

print(f"\n{'='*50}")
print(f"Готово. {ok_count} патчей применено, {err_count} ошибок.")

if err_count == 0:
    print("""
Что изменилось:
  • hooks.py: _bob_finalize() теперь вызывает _save_deliverables()
  • hooks.py: новая функция _save_deliverables() — пишет runs/{id}/deliverables.json
  • __init__.py: _find_projects() читает deliverables.json напрямую
  • __init__.py: _parse_bob_file() осталась, но больше не вызывается

Commit:
  fix: deliverables.json как источник правды для Мастерской (#6)
""")
else:
    print(f"\n⚠️  Есть ошибки — проверь вывод выше.")
    sys.exit(1)
