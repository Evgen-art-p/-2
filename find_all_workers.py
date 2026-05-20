from pathlib import Path

src = Path("studio/workshop/ui.py").read_text(encoding="utf-8")
lines = src.splitlines()

for i, line in enumerate(lines, 1):
    if "ALL_WORKERS" in line or "ALL_TURBO" in line:
        print(f"{i:4d}: {line}")
