#!/usr/bin/env python3
"""
patch_monteur_line781.py
Прямой патч строки 781 в monteur.py.
Запуск из корня репо: python patch_monteur_line781.py
"""
from pathlib import Path

MONTEUR_PATH = Path("studio/assembly/monteur.py")

def apply():
    if not MONTEUR_PATH.exists():
        print(f"❌ Не найден: {MONTEUR_PATH}")
        return False

    lines = MONTEUR_PATH.read_text(encoding="utf-8").splitlines()

    # Показываем строки 778-790 чтобы точно видеть контекст
    print("Строки 778-790:")
    for i in range(777, min(790, len(lines))):
        print(f"  {i+1:4d}: {repr(lines[i])}")

    # Ищем паттерн: строка с f"{ и без закрывающей кавычки
    # Обычно это user = ( \n f"{var}\n\n" \n "текст\n" \n "текст" \n )
    original = "\n".join(lines)

    # Заменяем конкретный паттерн arthur_look user строки
    import re

    # Паттерн 1: f"{переменная}\n\n" где \n реальный перенос
    fixed = re.sub(
        r'f"(\{[^}]+\})\n(\s*)\n(\s*)"',
        r'f"\1\\n\\n"',
        original,
    )

    # Паттерн 2: строки вида "текст\n" где \n реальный перенос
    fixed = re.sub(
        r'"([^"{}]+)\n(\s*)"',
        lambda m: '"' + m.group(1) + '\\n"',
        fixed,
    )

    if fixed == original:
        print("\n⚠️  Автозамена не сработала.")
        print("Открой studio/assembly/monteur.py строка 781")
        print("Найди блок похожий на:")
        print('    user = (')
        print('        f"{timeline_ctx}')
        print('  "')
        print('        "Три кадра...')
        print('  "')
        print("Замени на:")
        print('    user = (')
        print('        f"{timeline_ctx}\\n"')
        print('        "Три кадра...\\n"')
        print('        "Что осталось?"')
        print('    )')
        return False

    # Проверяем синтаксис
    try:
        compile(fixed, str(MONTEUR_PATH), 'exec')
        backup = MONTEUR_PATH.with_suffix(".py.bak_line781")
        backup.write_text(original, encoding="utf-8")
        print(f"\n💾 Бэкап: {backup}")
        MONTEUR_PATH.write_text(fixed, encoding="utf-8")
        print(f"✅ Исправлено!")
        return True
    except SyntaxError as e:
        print(f"\n❌ Синтаксис всё ещё сломан на строке {e.lineno}")
        print("Нужна ручная правка.")
        return False

if __name__ == "__main__":
    apply()
