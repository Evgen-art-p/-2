#!/usr/bin/env python3
"""
patch_monteur_fstring.py
========================
Исправляет SyntaxError: unterminated f-string literal в monteur.py.
Причина: f-строка содержит реальный перенос строки (запрещено в Python).

Запуск из корня репо: python patch_monteur_fstring.py
"""
import re
from pathlib import Path

MONTEUR_PATH = Path("studio/assembly/monteur.py")

def apply():
    if not MONTEUR_PATH.exists():
        print(f"❌ Не найден: {MONTEUR_PATH}")
        return False

    text = MONTEUR_PATH.read_text(encoding="utf-8")

    # Проверяем синтаксис
    try:
        compile(text, str(MONTEUR_PATH), 'exec')
        print("ℹ️  Файл синтаксически корректен — ничего не делаю.")
        return True
    except SyntaxError as e:
        print(f"⚠️  SyntaxError на строке {e.lineno}: {e.msg}")

    original = text
    lines = text.splitlines()

    # Ищем строки с f"..." где внутри реальный перенос
    # Заменяем реальные \n внутри строковых литералов на \\n
    fixed_lines = []
    i = 0
    changes = 0
    while i < len(lines):
        line = lines[i]
        # Ищем открывающую f-строку без закрывающей на той же строке
        if re.search(r'f"[^"]*$', line) or re.search(r"f'[^']*$", line):
            # Многострочная f-строка — собираем до закрытия
            collected = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                collected.append(next_line)
                # Проверяем закрылась ли строка
                if '"' in next_line or "'" in next_line:
                    break
                j += 1
            # Склеиваем в одну строку с \n
            joined = "\n".join(collected)
            # Заменяем реальные переносы внутри f-строки на \n
            # Простая эвристика: между открывающей и закрывающей кавычкой
            fixed = re.sub(
                r'(f")(.*?)(")',
                lambda m: m.group(1) + m.group(2).replace('\n', '\\n') + m.group(3),
                joined,
                flags=re.DOTALL
            )
            if fixed != joined:
                fixed_lines.append(fixed)
                changes += 1
                i = j + 1
                continue
        fixed_lines.append(line)
        i += 1

    if changes == 0:
        # Fallback: ищем конкретный паттерн из arthur_look
        # f"{...}\n\n" разбитое на строки
        text = re.sub(
            r'f"(\{[^}]+\})\n\n"',
            r'f"\1\\n"',
            text,
        )
        # "строка\n" разбитое на строки
        text = re.sub(
            r'"([^"]+)\n"',
            lambda m: '"' + m.group(1).replace('\n', '\\n') + '"',
            text,
        )

    if changes > 0:
        text = "\n".join(fixed_lines)

    # Проверяем снова
    try:
        compile(text, str(MONTEUR_PATH), 'exec')
        backup = MONTEUR_PATH.with_suffix(".py.bak_fstring")
        backup.write_text(original, encoding="utf-8")
        print(f"💾 Бэкап: {backup}")
        MONTEUR_PATH.write_text(text, encoding="utf-8")
        print(f"✅ Исправлено: {MONTEUR_PATH}")
        return True
    except SyntaxError as e:
        print(f"❌ Автофикс не помог. Строка {e.lineno}: {e.msg}")
        print(f"\nОткрой файл в редакторе на строке {e.lineno}")
        print("Найди f-строку которая содержит реальный перенос строки")
        print("Замени реальный перенос на \\n")
        print("\nПример:")
        print('  БЫЛО:  f"текст')
        print('         продолжение"')
        print('  СТАЛО: f"текст\\nпродолжение"')

        # Показываем проблемные строки
        lines_list = original.splitlines()
        start = max(0, e.lineno - 5)
        end = min(len(lines_list), e.lineno + 3)
        print(f"\nОкрестности строки {e.lineno}:")
        for idx in range(start, end):
            marker = ">>>" if idx + 1 == e.lineno else "   "
            print(f"{marker} {idx+1:4d}: {lines_list[idx]}")
        return False


if __name__ == "__main__":
    apply()
