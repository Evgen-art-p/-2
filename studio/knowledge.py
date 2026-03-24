from pathlib import Path

def load_all_knowledge(folder: Path) -> str:
    if not folder.exists():
        return ""
    texts = []
    for f in sorted(folder.glob("*.txt")):
        texts.append(f.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(texts)

