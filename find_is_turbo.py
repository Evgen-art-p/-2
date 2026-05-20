from pathlib import Path

src = Path("studio/workshop/ui.py").read_text(encoding="utf-8")
lines = src.splitlines()

for i, line in enumerate(lines, 1):
    if "is_turbo" in line:
        print(f"{i:4d}: {line}")
