"""
🔧 Патч для studio/city_walker.py — фикс RuntimeWarning: coroutine was never awaited

Проблема: функция log() внутри run_city_walk() вызывает on_progress(msg),
но on_progress может быть async callback. Без await корутина создаётся
но никогда не выполняется, что приводит к утечке и 100% CPU при 135 агентах.

Фикс: делаем log() async и добавляем await ко всем её вызовам.

Запуск:
  python patch_city_walker.py          — применить патч
  python patch_city_walker.py --check  — только проверить
"""

import sys
from pathlib import Path

WALKER_FILE = Path("studio/city_walker.py")


def patch():
    check_only = "--check" in sys.argv

    if not WALKER_FILE.exists():
        print(f"❌ Файл не найден: {WALKER_FILE}")
        return False

    text = WALKER_FILE.read_text(encoding="utf-8")

    # Проверяем: уже патчено?
    if "async def log(msg: str):" in text and "asyncio.iscoroutine" in text:
        print("✅ city_walker.py уже патчен.")
        return True

    if check_only:
        if "def log(msg: str):" in text:
            print("⚠ city_walker.py НЕ патчен — найдена синхронная log().")
            print("  Запусти без --check чтобы применить патч.")
        return False

    changes = 0

    # 1. Заменяем синхронную log() на async
    old_log = '''    def log(msg: str):
        print(f"[CITY] {msg}")
        if on_progress:
            on_progress(msg)'''

    new_log = '''    async def log(msg: str):
        print(f"[CITY] {msg}")
        if on_progress:
            result = on_progress(msg)
            if asyncio.iscoroutine(result):
                await result'''

    if old_log in text:
        text = text.replace(old_log, new_log, 1)
        changes += 1
        print("  ✓ log() → async def log()")
    else:
        print("  ⚠ Не нашёл точный паттерн синхронной log(). Проверь вручную.")

    # 2. Заменяем все вызовы log(...) на await log(...)
    # Но только внутри run_city_walk (где log определена) — не глобально
    # Ищем строки типа: "        log(" и заменяем на "        await log("
    import re
    # Паттерн: начало строки + пробелы + log( — но НЕ "await log(" и НЕ "def log("
    pattern = re.compile(r'^(\s+)(?<!await )(?<!def )(?<!async def )log\(', re.MULTILINE)

    def replacer(match):
        indent = match.group(1)
        return f"{indent}await log("

    new_text = pattern.sub(replacer, text)
    log_calls_fixed = len(pattern.findall(text))
    if new_text != text:
        text = new_text
        changes += log_calls_fixed
        print(f"  ✓ {log_calls_fixed} вызовов log() → await log()")

    if changes == 0:
        print("⚠ Изменений не найдено. Возможно файл уже отличается от ожидаемого.")
        return False

    # Сохраняем бэкап
    backup = WALKER_FILE.with_suffix(".py.bak_coroutine")
    WALKER_FILE.rename(backup)
    WALKER_FILE.write_text(text, encoding="utf-8")

    print(f"\n✅ city_walker.py патчен!")
    print(f"   Бэкап: {backup}")
    print(f"   Изменений: {changes}")
    print(f"")
    print(f"   Теперь прогулки не будут вешать процессор.")
    return True


if __name__ == "__main__":
    patch()
