"""
patch_bridge_path.py — мост копирует JSON прямо в песочницу индикатора.

Индикатор читает из C:\\Program Files\\MetaTrader 5\\MQL5\\Files\\ — там
окаменелость 4:59. Мост туда не писал (только Common\\Files, но у
портативного MT5 это другая папка). Добавляем прямой путь TERMINAL_PATH.

Блоки замены берутся из _blocks.json (точные строки из файла).
Запуск: положи _blocks.json рядом и запусти из корня студии.
ПРОЩЕ: этот скрипт самодостаточен — блоки вшиты ниже.
"""
from pathlib import Path
import shutil, ast
from datetime import datetime

STAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
TARGET = Path(__file__).resolve().parent / "main.py"
if not TARGET.exists():
    print("[!] main.py не найден рядом со скриптом"); raise SystemExit(1)

txt = TARGET.read_text(encoding="utf-8")

OLD_PATHS = (
    '        SIGNALS_PATH = Path(r"C:\\mt5signals\\mt5_signals.json")\n'
    '        COMMON_PATH  = Path(r"C:\\Users\\Public\\Documents\\MetaQuotes\\Terminal\\Common\\Files\\mt5_signals.json")'
)
NEW_PATHS = (
    '        SIGNALS_PATH = Path(r"C:\\mt5signals\\mt5_signals.json")\n'
    '        COMMON_PATH  = Path(r"C:\\Users\\Public\\Documents\\MetaQuotes\\Terminal\\Common\\Files\\mt5_signals.json")\n'
    '        TERMINAL_PATH = Path(r"C:\\Program Files\\MetaTrader 5\\MQL5\\Files\\mt5_signals.json")'
)

OLD_COPY = (
    '                    # Копируем в Common\\Files для MT5\n'
    '                    try:\n'
    '                        COMMON_PATH.parent.mkdir(parents=True, exist_ok=True)\n'
    '                        shutil.copy2(SIGNALS_PATH, COMMON_PATH)\n'
    '                    except Exception as _ce:\n'
    '                        print(f"[MT5-BRIDGE] Копирование не удалось: {_ce}")'
)
NEW_COPY = (
    '                    # Копируем в Common\\Files для MT5\n'
    '                    try:\n'
    '                        COMMON_PATH.parent.mkdir(parents=True, exist_ok=True)\n'
    '                        shutil.copy2(SIGNALS_PATH, COMMON_PATH)\n'
    '                    except Exception as _ce:\n'
    '                        print(f"[MT5-BRIDGE] Копирование в Common не удалось: {_ce}")\n'
    '                    # Копируем прямо в песочницу индикатора (главное!)\n'
    '                    try:\n'
    '                        TERMINAL_PATH.parent.mkdir(parents=True, exist_ok=True)\n'
    '                        shutil.copy2(SIGNALS_PATH, TERMINAL_PATH)\n'
    '                    except Exception as _te:\n'
    '                        print(f"[MT5-BRIDGE] Копирование в Terminal не удалось: {_te}")'
)

if OLD_PATHS not in txt:
    print("[!] Блок путей не найден"); raise SystemExit(1)
if OLD_COPY not in txt:
    print("[!] Блок копирования не найден"); raise SystemExit(1)

txt = txt.replace(OLD_PATHS, NEW_PATHS, 1)
txt = txt.replace(OLD_COPY, NEW_COPY, 1)
print("    TERMINAL_PATH добавлен + копирование")

try:
    ast.parse(txt)
    print("    синтаксис: OK")
except SyntaxError as e:
    print(f"[!] СЛОМАН: {e}"); raise SystemExit(1)

bak = TARGET.with_name(TARGET.name + f".bak_{STAMP}")
shutil.copy2(TARGET, bak)
TARGET.write_text(txt, encoding="utf-8")
print(f"    бэкап: {bak.name}")
print(f"    ✓ main.py — мост теперь пишет в песочницу индикатора")
print()
print(" Перезапусти студию. Подожди ~10 сек (мост пишет раз в минуту,")
print(" но первый прогон сразу). Проверь дату файла:")
print('   Get-Item "C:\\Program Files\\MetaTrader 5\\MQL5\\Files\\mt5_signals.json" | Select LastWriteTime')
print(" Должна стать свежей. Потом перегрузи индикатор в MT5 (F7 или")
print(" сними-поставь). Жди total=185 в Эксперты.")
