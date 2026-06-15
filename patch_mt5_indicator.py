"""
patch_mt5_indicator.py — фикс моста MT5 + индикатора AI_Tribunal_v7.

Что делает:
  1. Находит python-файл моста в студии (любой .py, который пишет в mt5_signals.json)
     и переписывает json.dumps(...) с форматом indent=1 + separators БЕЗ пробелов.
     После этого каждый сигнал — на отдельной строке, но JSON без лишних пробелов,
     поиск "divergence":true в индикаторе сработает.

  2. Находит AI_Tribunal_v7.mq5 в стандартных папках MT5 и патчит:
       - добавляет диагностику в Журнал (первые 500 символов файла + два варианта поиска),
       - расширяет поиск divergence/alligator_sleeping — теперь ловит и без пробела, и с пробелом.

Запуск (PowerShell, из корня студии):
    python patch_mt5_indicator.py

Безопасность:
  - перед любой правкой делается .bak копия с timestamp,
  - если шаблон не найден — скрипт ничего не ломает, просто пишет что искал,
  - если индикатор лежит в Program Files и прав нет — попросит запустить от Администратора.
"""

from pathlib import Path
import re, shutil, sys
from datetime import datetime

ROOT  = Path(__file__).resolve().parent
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ════════════════════════════════════════════════════════════════════════
#  ШАГ 1. Мост — python-файл студии, пишущий mt5_signals.json
# ════════════════════════════════════════════════════════════════════════
print("─" * 64)
print(" ШАГ 1. Ищу мост MT5 в *.py файлах студии…")
print("─" * 64)

SKIP_DIRS = {"venv", ".venv", "__pycache__", "node_modules", ".git", "site-packages"}

bridges = []
for p in ROOT.rglob("*.py"):
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if "mt5_signals" in txt and "json.dumps" in txt:
        bridges.append(p)

if not bridges:
    print("[!] Не нашёл ни одного .py, который пишет mt5_signals.json")
    print("    Возможно мост лежит вне корня студии — тогда поправь его вручную:")
    print("    json.dumps(data, ensure_ascii=False)")
    print("      →")
    print("    json.dumps(data, ensure_ascii=False, indent=1, separators=(',', ':'))")
else:
    # Паттерны от более специфичного к менее. Заменяем ПЕРВОЕ совпадение.
    PATTERNS = [
        (re.compile(
            r"json\.dumps\(\s*([A-Za-z_]\w*)\s*,\s*ensure_ascii\s*=\s*False\s*\)"),
         r"json.dumps(\1, ensure_ascii=False, indent=1, separators=(',', ':'))"),

        (re.compile(
            r"json\.dumps\(\s*([A-Za-z_]\w*)\s*,\s*ensure_ascii\s*=\s*True\s*\)"),
         r"json.dumps(\1, ensure_ascii=True, indent=1, separators=(',', ':'))"),

        (re.compile(
            r"json\.dumps\(\s*([A-Za-z_]\w*)\s*\)"),
         r"json.dumps(\1, indent=1, separators=(',', ':'))"),
    ]

    for p in bridges:
        rel = p.relative_to(ROOT)
        print(f"[+] Кандидат: {rel}")
        txt = p.read_text(encoding="utf-8")

        # уже пропатчен?
        if "separators=(',', ':')" in txt and "indent=1" in txt and "mt5_signals" in txt:
            print(f"    уже пропатчен ранее — пропускаю")
            continue

        new_txt = txt
        patched = False
        for pat, repl in PATTERNS:
            cand = pat.sub(repl, new_txt, count=1)
            if cand != new_txt:
                new_txt = cand
                patched = True
                print(f"    применил шаблон: {pat.pattern}")
                break

        if not patched:
            print(f"    json.dumps в файле есть, но в нестандартной форме — пропускаю")
            print(f"    (поправь вручную: добавь к dumps аргументы")
            print(f"     indent=1, separators=(',', ':'))")
            continue

        bak = p.with_name(p.name + f".bak_{STAMP}")
        shutil.copy2(p, bak)
        p.write_text(new_txt, encoding="utf-8")
        print(f"    бэкап:   {bak.name}")
        print(f"    ✓ обновлён")


# ════════════════════════════════════════════════════════════════════════
#  ШАГ 2. Индикатор — AI_Tribunal_v7.mq5
# ════════════════════════════════════════════════════════════════════════
print()
print("─" * 64)
print(" ШАГ 2. Ищу AI_Tribunal_v7.mq5 в стандартных папках MT5…")
print("─" * 64)

search_roots = [
    Path(r"C:\Program Files\MetaTrader 5\MQL5\Indicators"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators"),
]
# AppData\Roaming\MetaQuotes\Terminal\<hash>\MQL5\Indicators
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
        print(f"[+] Найден: {f}")

if not mq5_files:
    print("[!] AI_Tribunal_v7.mq5 не найден ни в одном из этих путей:")
    for sp in search_roots:
        print(f"    {sp}")
    print()
    print("    Открой в MetaEditor: File → Open Data Folder → MQL5\\Indicators —")
    print("    путь оттуда добавь сюда в search_roots и перезапусти, либо просто")
    print("    скопируй индикатор в одну из проверенных папок.")
    sys.exit(0)


def read_with_encoding(path: Path):
    """MetaEditor пишет файлы как UTF-8 или UTF-16. Угадываем по BOM."""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le"), "utf-16-le", True   # has BOM
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be"), "utf-16-be", True
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8-sig", False
    return raw.decode("utf-8", errors="ignore"), "utf-8", False


def write_with_encoding(path: Path, text: str, enc: str):
    if enc == "utf-16-le":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    elif enc == "utf-16-be":
        path.write_bytes(b"\xfe\xff" + text.encode("utf-16-be"))
    elif enc == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    else:
        path.write_bytes(text.encode("utf-8"))


# ─── точные блоки из текущего AI_Tribunal_v7.mq5 (v7.2) ─────────────────
OLD_BLOCK_1 = (
    '   int dpos = StringFind(json, "\\"divergence\\":true");\n'
    '   Print("v7.2: first divergence:true at pos=", dpos);\n'
    '   \n'
    '   if(dpos < 0) { Print("v7.2: no divergences found in json"); return; }'
)
NEW_BLOCK_1 = (
    '   int dpos    = StringFind(json, "\\"divergence\\":true");\n'
    '   int dpos_sp = StringFind(json, "\\"divergence\\": true");\n'
    '   Print("v7.2: divergence:true=", dpos, " divergence: true=", dpos_sp);\n'
    '   Print("v7.2: head=", StringSubstr(json, 0, 500));\n'
    '   \n'
    '   if(dpos < 0 && dpos_sp < 0) { Print("v7.2: no divergences found in json"); return; }'
)

OLD_BLOCK_2 = (
    '      bool diver   = StringFind(obj, "\\"divergence\\":true")        >= 0;\n'
    '      bool sleeping= StringFind(obj, "\\"alligator_sleeping\\":true") >= 0;'
)
NEW_BLOCK_2 = (
    '      bool diver    = StringFind(obj, "\\"divergence\\":true")          >= 0\n'
    '                   || StringFind(obj, "\\"divergence\\": true")         >= 0;\n'
    '      bool sleeping = StringFind(obj, "\\"alligator_sleeping\\":true")  >= 0\n'
    '                   || StringFind(obj, "\\"alligator_sleeping\\": true") >= 0;'
)


for mq5 in mq5_files:
    try:
        txt, enc, _ = read_with_encoding(mq5)
    except Exception as e:
        print(f"[!] {mq5}: не прочёлся ({e}) — пропускаю")
        continue

    # уже пропатчен?
    marker = "v7.2: head="
    if marker in txt:
        print(f"    {mq5.name}: уже пропатчен ранее — пропускаю")
        continue

    new_txt = txt
    p1 = OLD_BLOCK_1 in new_txt
    p2 = OLD_BLOCK_2 in new_txt

    if p1:
        new_txt = new_txt.replace(OLD_BLOCK_1, NEW_BLOCK_1)
        print(f"    патч 1/2 (диагностика head + поиск с пробелом): OK")
    else:
        print(f"    патч 1/2: блок не найден в точности — пропускаю")

    if p2:
        new_txt = new_txt.replace(OLD_BLOCK_2, NEW_BLOCK_2)
        print(f"    патч 2/2 (цикл diver/sleeping с пробелом): OK")
    else:
        print(f"    патч 2/2: блок не найден в точности — пропускаю")

    if new_txt == txt:
        print(f"    {mq5.name}: изменений нет")
        continue

    # бэкап
    bak = mq5.with_name(mq5.name + f".bak_{STAMP}")
    try:
        shutil.copy2(mq5, bak)
    except PermissionError:
        print(f"    [!] нет прав записи в {mq5.parent}")
        print(f"        запусти PowerShell от Администратора и повтори.")
        continue
    except Exception as e:
        print(f"    [!] не смог сделать бэкап: {e}")
        continue

    # запись
    try:
        write_with_encoding(mq5, new_txt, enc)
    except PermissionError:
        print(f"    [!] нет прав записи. Запусти от Администратора.")
        # откатим бэкап на место
        shutil.copy2(bak, mq5)
        continue
    except Exception as e:
        print(f"    [!] ошибка записи: {e}")
        shutil.copy2(bak, mq5)
        continue

    print(f"    бэкап: {bak.name}")
    print(f"    ✓ {mq5.name} обновлён  (кодировка: {enc})")


# ════════════════════════════════════════════════════════════════════════
print()
print("─" * 64)
print(" ГОТОВО")
print("─" * 64)
print()
print(" Дальше — руками в MetaTrader 5:")
print()
print(" 1. Открой MetaEditor (F4 в терминале).")
print(" 2. Открой AI_Tribunal_v7.mq5 → F7 (Compile). Должно быть 0 errors.")
print(" 3. В терминале на графике XAUUSD H4 сними индикатор (правой → Удалить)")
print("    и накинь заново из Навигатора.")
print(" 4. Перегенерируй сигналы — запусти мост ещё раз, чтобы")
print("    mt5_signals.json перезаписался уже в новом формате.")
print(" 5. Открой Журнал (Ctrl+T → вкладка \"Эксперты\" или \"Журнал\").")
print()
print(" Что увидеть в Журнале:")
print("   v7.2: lines=...  len=387700  (или близко)")
print("   v7.2: 'signals' at pos=...")
print("   v7.2: 'divergence' at pos=...")
print("   v7.2: divergence:true=...  divergence: true=...")
print("   v7.2: head={...}  ← первые 500 символов реального файла")
print("   v7.2: total_sigs=...  drawn=...")
print()
print(" Если drawn>0 — маркеры на графике. Если drawn=0 — кинь сюда")
print(" строку 'head=...' и я скажу что не сходится в формате JSON.")
print("─" * 64)
