"""
patch_mt5_indicator_v2.py — добивает фикс AI_Tribunal_v7.mq5.

Что узнали по логу:
  v7.2: signals array not found
  v7.2: divergence:true=-1 divergence: true=16415

→ в JSON везде пробелы после ":" ("signals": [, "date": "...", ...).
  Первый патч закрыл только divergence/alligator_sleeping, но остались
  поиски "signals":[ и "date":" — они без пробела и теперь падают.

Решение этого патча: добавить два StringReplace сразу после чтения файла,
которые ОДИН РАЗ нормализуют JSON, убирая все пробелы после ":".
После этого все существующие поиски работают и для формата с пробелами,
и для формата без пробелов — единообразно.

Запуск:
    python patch_mt5_indicator_v2.py
"""

from pathlib import Path
import shutil, sys
from datetime import datetime

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ───────────────────────────────────────────────────────────────────────
# поиск файла индикатора
# ───────────────────────────────────────────────────────────────────────
search_roots = [
    Path(r"C:\Program Files\MetaTrader 5\MQL5\Indicators"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators"),
]
roaming = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
if roaming.exists():
    for term in roaming.iterdir():
        ind = term / "MQL5" / "Indicators"
        if ind.exists():
            search_roots.append(ind)

mq5_files = []
for base in search_roots:
    if not base.exists():
        continue
    for f in base.rglob("AI_Tribunal_v7.mq5"):
        mq5_files.append(f)

if not mq5_files:
    print("[!] AI_Tribunal_v7.mq5 не найден в:")
    for sp in search_roots:
        print(f"    {sp}")
    sys.exit(1)

for f in mq5_files:
    print(f"[+] Найден: {f}")


# ───────────────────────────────────────────────────────────────────────
# I/O с автоопределением кодировки (UTF-8 / UTF-16 с BOM)
# ───────────────────────────────────────────────────────────────────────
def read_with_encoding(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le"), "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be"), "utf-16-be"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8-sig"
    return raw.decode("utf-8", errors="ignore"), "utf-8"


def write_with_encoding(path: Path, text: str, enc: str):
    if enc == "utf-16-le":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    elif enc == "utf-16-be":
        path.write_bytes(b"\xfe\xff" + text.encode("utf-16-be"))
    elif enc == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    else:
        path.write_bytes(text.encode("utf-8"))


# ───────────────────────────────────────────────────────────────────────
# вставляем блок нормализации сразу после Print("v7.2: lines=...")
# ───────────────────────────────────────────────────────────────────────
ANCHOR = '   Print("v7.2: lines=", lines, " len=", StringLen(json));'

NORMALIZE = (
    '\n'
    '   // === нормализация JSON: схлопываем пробелы после ":" ===\n'
    '   // мост может писать как "key":"v" так и "key": "v" — приводим к одному виду\n'
    '   StringReplace(json, "\\": \\"", "\\":\\"");\n'
    '   StringReplace(json, "\\": ",   "\\":");\n'
    '   Print("v7.2: normalized len=", StringLen(json));'
)

MARKER_DONE = "v7.2: normalized len="

for mq5 in mq5_files:
    try:
        txt, enc = read_with_encoding(mq5)
    except Exception as e:
        print(f"[!] {mq5}: не прочёлся ({e}) — пропускаю")
        continue

    if MARKER_DONE in txt:
        print(f"    {mq5.name}: уже пропатчен v2 — пропускаю")
        continue

    if ANCHOR not in txt:
        print(f"    {mq5.name}: якорная строка не найдена.")
        print(f"        Ищу: {ANCHOR!r}")
        print(f"        Возможно, индикатор сильно изменился — пришли актуальную версию.")
        continue

    new_txt = txt.replace(ANCHOR, ANCHOR + NORMALIZE, 1)

    # бэкап
    bak = mq5.with_name(mq5.name + f".bak_{STAMP}")
    try:
        shutil.copy2(mq5, bak)
    except PermissionError:
        print(f"    [!] нет прав записи в {mq5.parent}")
        print(f"        запусти PowerShell от Администратора и повтори.")
        continue

    try:
        write_with_encoding(mq5, new_txt, enc)
    except PermissionError:
        print(f"    [!] нет прав записи. Запусти от Администратора.")
        shutil.copy2(bak, mq5)
        continue
    except Exception as e:
        print(f"    [!] ошибка записи: {e}")
        shutil.copy2(bak, mq5)
        continue

    print(f"    бэкап: {bak.name}")
    print(f"    ✓ {mq5.name} обновлён (кодировка: {enc})")


print()
print("─" * 64)
print(" ГОТОВО.")
print("─" * 64)
print()
print(" Дальше:")
print("   1. MetaEditor (F4) → AI_Tribunal_v7.mq5 → F7 (Compile).")
print("   2. На графике — снять индикатор → накинуть заново.")
print("   3. В Журнале должно появиться:")
print("        v7.2: normalized len=<меньше 387700>")
print("        v7.2: 'signals' at pos=...")
print("        v7.2: divergence:true=...  (теперь без пробела, после нормализации)")
print("        v7.2: total_sigs=<число>  drawn=<число>")
print()
print(" Если drawn > 0 — маркеры на графике.")
print(" Если drawn = 0 при total_sigs > 0 — проблема в датах (формат StringToTime),")
print("                                      кинь сюда несколько строк лога.")
print("─" * 64)
