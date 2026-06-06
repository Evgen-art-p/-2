#!/usr/bin/env python3
"""
patch_anchor_context.py — ANCHOR передаёт полный диалог включая ответы агента

ПРОБЛЕМА:
  anchor_ctx содержит весь chat_history_A03 включая ответы агента.
  НО: промпт говорит агенту "учти правки" — агент игнорирует свой
  предыдущий ответ из чата и генерирует заново с нуля.

РЕШЕНИЕ:
  Разделяем anchor_ctx на две части:
  1. Твой предыдущий ответ из чата (последний assistant-ответ)
     → "ВОТ ЧТО ТЫ УЖЕ НАПИСАЛ — ДОРАБОТАЙ ЭТО"
  2. Правки Шефа (user-сообщения)
     → "ВОТ ПРАВКИ — УЧТИ ИХ В ДОРАБОТКЕ"
  
  Агент не пишет заново — он берёт свой ответ и дорабатывает.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"anchor_ctx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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


ANCHOR_OLD = (
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

ANCHOR_NEW = (
    "                anchor_ctx = \"\"\n"
    "                if with_chat_context and worker_id == (from_worker or \"\"):\n"
    "                    # Читаем ИЗОЛИРОВАННУЮ историю этого агента\n"
    "                    _isolated = self.state.get(f\"chat_history_{worker_id}\", [])\n"
    "                    if not _isolated:\n"
    "                        _isolated = self.state.get(\"chat_history\", [])\n"
    "                    \n"
    "                    # Разделяем на: что агент уже написал vs правки Шефа\n"
    "                    _agent_replies = [\n"
    "                        m for m in _isolated\n"
    "                        if m.get(\"role\") == \"assistant\"\n"
    "                        and m.get(\"worker\") == worker_id\n"
    "                    ]\n"
    "                    _shef_edits = [\n"
    "                        m for m in _isolated\n"
    "                        if m.get(\"role\") == \"user\"\n"
    "                    ]\n"
    "                    \n"
    "                    print(f\"[ANCHOR] {worker_id}: \"\n"
    "                          f\"{len(_agent_replies)} ответов агента, \"\n"
    "                          f\"{len(_shef_edits)} правок Шефа \"\n"
    "                          f\"в chat_history_{worker_id}\")\n"
    "                    \n"
    "                    parts = []\n"
    "                    \n"
    "                    # Часть 1: последний ответ агента из чата\n"
    "                    if _agent_replies:\n"
    "                        _last_reply = _agent_replies[-1].get(\"content\", \"\")[:3000]\n"
    "                        parts.append(\n"
    "                            f\"=== ТВОЙ ПОСЛЕДНИЙ ОТВЕТ ИЗ ЧАТА ===\\n\"\n"
    "                            f\"{_last_reply}\\n\"\n"
    "                            f\"=== КОНЕЦ ТВОЕГО ОТВЕТА ===\\n\"\n"
    "                        )\n"
    "                    \n"
    "                    # Часть 2: правки Шефа\n"
    "                    if _shef_edits:\n"
    "                        _edits_text = \"\\n\".join([\n"
    "                            f\"Шеф: {m.get('content','')[:1000]}\"\n"
    "                            for m in _shef_edits[-5:]\n"
    "                        ])\n"
    "                        parts.append(\n"
    "                            f\"=== ПРАВКИ ШЕФА ===\\n\"\n"
    "                            f\"{_edits_text}\\n\"\n"
    "                            f\"=== КОНЕЦ ПРАВОК ===\\n\"\n"
    "                        )\n"
    "                    \n"
    "                    if parts:\n"
    "                        anchor_ctx = (\n"
    "                            \"\\n\".join(parts) +\n"
    "                            f\"\\nЗАДАЧА: Возьми свой ответ выше и доработай его \"\n"
    "                            f\"с учётом правок Шефа. \"\n"
    "                            f\"НЕ пиши заново — улучши то что уже есть.\\n\"\n"
    "                        )"
)


def main():
    print("=" * 60)
    print("ПАТЧ: ANCHOR передаёт полный диалог агенту")
    print("=" * 60)
    if DRY_RUN:
        print("DRY-RUN\n")

    path = Path("studio/cartridge.py")

    print("\n[1/1] cartridge.py — anchor_ctx с ответом агента + правками Шефа")
    ok = apply(path, ANCHOR_OLD, ANCHOR_NEW,
               "разделяем чат на ответы агента и правки Шефа")

    print("\n" + "=" * 60)
    if DRY_RUN:
        print("DRY-RUN завершён.")
        return

    if ok:
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("Теперь при ANCHOR:")
        print("  1. Агент видит свой ПОСЛЕДНИЙ ответ из чата")
        print("  2. Агент видит правки Шефа")
        print("  3. Задача: доработать уже написанное, не писать заново")
        print()
        print("В консоли появится:")
        print("  [ANCHOR] A03: 2 ответов агента, 1 правок Шефа в chat_history_A03")
        print()
        print("Если увидишь: 0 ответов агента — значит chat_history_A03 пустой")
        print("Это покажет где именно разрыв.")
    else:
        print("⚠ Не применено")

if __name__ == "__main__":
    main()
