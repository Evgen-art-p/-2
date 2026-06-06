#!/usr/bin/env python3
"""
patch_anchor_isolation.py — Фикс 1: изолированная история чата по агенту

ПРОБЛЕМА:
  state["chat_history"] — глобальная каша. ANCHOR читает оттуда и получает
  реплики адресованные другим агентам / Локе / общему чату.
  Агент сходит с ума и генерирует не то.

РЕШЕНИЕ:
  1. ui.py send_message() — параллельно пишем в state[f"chat_history_{worker_id}"]
  2. cartridge.py ANCHOR — читает из изолированной истории конкретного агента
     Обрезка 200 → 2000 симв
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"anchor_isolation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ❌ Файл не найден: {path}")
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 1: ui.py — send_message пишет в изолированный ключ агента
# ══════════════════════════════════════════════════════════════════

UI_OLD = (
    "        state[\"chat_history\"].append({\"role\": \"user\", \"content\": msg})\n"
    "        update_chat_display()"
)

UI_NEW = (
    "        state[\"chat_history\"].append({\"role\": \"user\", \"content\": msg})\n"
    "        # Изолированная история для ANCHOR — по worker_id\n"
    "        _wid = state[\"active_worker\"]\n"
    "        state.setdefault(f\"chat_history_{_wid}\", []).append(\n"
    "            {\"role\": \"user\", \"content\": msg}\n"
    "        )\n"
    "        update_chat_display()"
)

UI_OLD2 = (
    "            state[\"chat_history\"].append({\n"
    "                \"role\": \"assistant\", \n"
    "                \"content\": _clean_response(response), \n"
    "                \"worker\": worker_id\n"
    "            })"
)

UI_NEW2 = (
    "            state[\"chat_history\"].append({\n"
    "                \"role\": \"assistant\", \n"
    "                \"content\": _clean_response(response), \n"
    "                \"worker\": worker_id\n"
    "            })\n"
    "            # Изолированная история для ANCHOR — ответ агента\n"
    "            state.setdefault(f\"chat_history_{worker_id}\", []).append({\n"
    "                \"role\": \"assistant\",\n"
    "                \"content\": _clean_response(response),\n"
    "                \"worker\": worker_id\n"
    "            })"
)


# ══════════════════════════════════════════════════════════════════
# ПАТЧ 2: cartridge.py — ANCHOR читает изолированную историю агента
# ══════════════════════════════════════════════════════════════════

CARTRIDGE_OLD = (
    "                anchor_ctx = \"\"\n"
    "                if with_chat_context and worker_id == (from_worker or \"\"):\n"
    "                    chat_text = \"\\n\".join([\n"
    "                        f\"{m.get('role','')}: {m.get('content','')[:200]}\"\n"
    "                        for m in self.state.get(\"chat_history\", [])[-10:]\n"
    "                    ])\n"
    "                    if chat_text:\n"
    "                        anchor_ctx = f\"=== КОНТЕКСТ ЧАТА ===\\n{chat_text}\\n\""
)

CARTRIDGE_NEW = (
    "                anchor_ctx = \"\"\n"
    "                if with_chat_context and worker_id == (from_worker or \"\"):\n"
    "                    # Читаем ИЗОЛИРОВАННУЮ историю этого агента\n"
    "                    # а не глобальную кашу state[chat_history]\n"
    "                    _isolated = self.state.get(f\"chat_history_{worker_id}\", [])\n"
    "                    if not _isolated:\n"
    "                        # Fallback: глобальная история если изолированной нет\n"
    "                        _isolated = self.state.get(\"chat_history\", [])\n"
    "                    chat_text = \"\\n\".join([\n"
    "                        f\"{m.get('role','')}: {m.get('content','')[:2000]}\"\n"
    "                        for m in _isolated[-20:]\n"
    "                    ])\n"
    "                    if chat_text:\n"
    "                        anchor_ctx = (\n"
    "                            f\"=== ПРАВКИ ШЕФА ДЛЯ {worker_id} ===\\n\"\n"
    "                            f\"{chat_text}\\n\"\n"
    "                            f\"ВАЖНО: учти ВСЕ правки и комментарии Шефа выше.\\n\"\n"
    "                            f\"Не игнорируй ни одну деталь из этого контекста.\\n\"\n"
    "                        )"
)

# Также патчим вариант после patch_anchor_and_stress если он уже применён
CARTRIDGE_OLD2 = (
    "                anchor_ctx = \"\"\n"
    "                if with_chat_context and worker_id == (from_worker or \"\"):\n"
    "                    # ПАТЧ: 2000 симв вместо 200 — правки Шефа влезают полностью\n"
    "                    chat_text = \"\\n\".join([\n"
    "                        f\"{m.get('role','')}: {m.get('content','')[:2000]}\"\n"
    "                        for m in self.state.get(\"chat_history\", [])[-20:]\n"
    "                    ])\n"
    "                    if chat_text:\n"
    "                        anchor_ctx = (\n"
    "                            f\"=== КОНТЕКСТ ЧАТА (правки Шефа) ===\\n\"\n"
    "                            f\"{chat_text}\\n\"\n"
    "                            f\"ВАЖНО: учти все правки и комментарии Шефа выше.\\n\"\n"
    "                        )"
)

# CARTRIDGE_NEW2 — тот же что CARTRIDGE_NEW


def main():
    print("=" * 60)
    print("ПАТЧ: Изолированная история чата для ANCHOR")
    print("=" * 60)
    if DRY_RUN:
        print("DRY-RUN\n")

    ui_path = Path("studio/workshop/ui.py")
    cartridge_path = Path("studio/cartridge.py")

    print("\n[1/3] ui.py — send_message пишет в chat_history_{worker_id}")
    ok1 = apply(ui_path, UI_OLD, UI_NEW, "изолированная запись user-сообщения")

    print("\n[2/3] ui.py — send_message пишет ответ агента в изолированную историю")
    ok2 = apply(ui_path, UI_OLD2, UI_NEW2, "изолированная запись ответа агента")

    print("\n[3/3] cartridge.py — ANCHOR читает chat_history_{worker_id}")
    ok3 = apply(cartridge_path, CARTRIDGE_OLD, CARTRIDGE_NEW,
                "изолированное чтение + 2000 симв")
    if not ok3:
        ok3 = apply(cartridge_path, CARTRIDGE_OLD2, CARTRIDGE_NEW,
                    "изолированное чтение (после anchor_stress патча)")

    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    applied = sum([ok1, ok2, ok3])
    if applied > 0:
        print(f"✅ Применено {applied}/3 патчей!")
        print(f"   Бекапы: {BACKUP_DIR}")
        print()
        print("Как теперь работает ANCHOR:")
        print("  1. Ты нажимаешь аватар A03")
        print("  2. Пишешь правки в чат — они пишутся в chat_history_A03")
        print("  3. Нажимаешь ANCHOR — A03 получает ТОЛЬКО свой разговор с тобой")
        print("  4. Никакой каши из чатов с другими агентами")
        print()
        print("Перезапусти: python main.py")
    else:
        print("⚠ Ничего не применено")


if __name__ == "__main__":
    main()
