# patch_pipeline.py
# Запускать из корня проекта:
#   python patch_pipeline.py
#
# Патчит studio/workshop/pipeline.py:
#   build_settings_ctx — добавляет защиту от отсутствия ключей
#   format/duration/style (которых нет в trading-цехе).

from pathlib import Path
import shutil
from datetime import datetime

TARGET = Path("studio/workshop/pipeline.py")

OLD = '''def build_settings_ctx(state: dict) -> str:
    """Формирует блок PROJECT SETTINGS для агентов"""
    return (
        f"=== PROJECT SETTINGS ===\\n"
        f"Format: {state['settings']['format']}\\n"
        f"Duration: {state['settings']['duration']} sec\\n"
        f"Style: {state['settings']['style']}\\n"
    )'''

NEW = '''def build_settings_ctx(state: dict) -> str:
    """Формирует блок PROJECT SETTINGS для агентов"""
    s = state.get("settings", {})
    # Для trading-цеха format/duration/style не нужны — возвращаем пустую строку
    if not any(k in s for k in ("format", "duration", "style")):
        return ""
    return (
        f"=== PROJECT SETTINGS ===\\n"
        f"Format: {s.get('format', '')}\\n"
        f"Duration: {s.get('duration', '')} sec\\n"
        f"Style: {s.get('style', '')}\\n"
    )'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Убедись что запускаешь из корня проекта.")
        return

    text = TARGET.read_text(encoding="utf-8")

    if OLD not in text:
        if "build_settings_ctx" in text:
            print("⚠️  build_settings_ctx уже изменена или имеет другой вид.")
            print("   Патч не применён — проверь файл вручную.")
        else:
            print("❌ build_settings_ctx не найдена в файле.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    # Патч
    patched = text.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")
    print(f"✅ Патч применён: {TARGET}")
    print()
    print("Теперь запускай:")
    print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 50")


if __name__ == "__main__":
    main()
