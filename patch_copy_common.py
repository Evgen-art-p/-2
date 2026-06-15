from pathlib import Path
import shutil
from datetime import datetime

MAIN = Path(r"C:\Users\Евгений\Desktop\студия 2\main.py")
TS   = datetime.now().strftime("%Y%m%d_%H%M%S")

OLD = '''                    SIGNALS_PATH.write_text(
                        json.dumps(data, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    print(f"[MT5-BRIDGE] {SYMBOL} {TIMEFRAME}: "'''

NEW = '''                    SIGNALS_PATH.write_text(
                        json.dumps(data, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    import shutil as _sh, glob as _gl, os as _os
                    for _cp in [
                        Path(r"C:/Users/Public/Documents/MetaQuotes/Terminal/Common/Files/mt5_signals.json"),
                        Path(_os.environ.get("APPDATA","")) / "MetaQuotes/Terminal/Common/Files/mt5_signals.json",
                    ]:
                        try:
                            _cp.parent.mkdir(parents=True, exist_ok=True)
                            _sh.copy2(SIGNALS_PATH, _cp)
                            break
                        except Exception:
                            pass
                    print(f"[MT5-BRIDGE] {SYMBOL} {TIMEFRAME}: "'''

if not MAIN.exists():
    print("ERR: main.py not found")
    exit(1)

content = MAIN.read_text(encoding="utf-8")

if "copy2(SIGNALS_PATH" in content:
    print("SKIP: already patched")
    exit(0)

if OLD not in content:
    print("ERR: marker not found")
    exit(1)

shutil.copy2(MAIN, str(MAIN) + f".bak_{TS}")
content = content.replace(OLD, NEW, 1)
MAIN.write_text(content, encoding="utf-8")
print("OK: main.py patched - copy to Common/Files added")
