# patch_williams_history_v2.py
# Запускать из корня проекта:
#   python patch_williams_history_v2.py
#
# ОТКАТЫВАЕТ предыдущий патч (убирает ao.history и ac.history)
# и оставляет только ao.pivots (последние 6) — этого достаточно
# чтобы Искра нашла дивергенцию без раздувания контекста.

from pathlib import Path
import shutil
from datetime import datetime

TARGET = Path("studio/modules/trading/williams_core.py")

# ── Убираем history из ao/ac, оставляем только пивоты ───────

OLD = '''\
        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
            # История последних 50 значений — нужна Искре для поиска пивотов/дивергенций
            "history":      [round(v, 8) for v in ao_series[-50:] if v is not None],
            # Пивоты AO (локальные минимумы и максимумы) — последние 10
            "pivots":       _find_ao_pivots(ao_series, bars)[-10:],
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
            # История последних 50 значений
            "history":    [round(v, 8) for v in ac_series[-50:] if v is not None],
        },'''

NEW = '''\
        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
            # Последние 6 пивотов AO — Искре нужно 2 пары для дивергенции
            "pivots":       _find_ao_pivots(ao_series, bars)[-6:],
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
        },'''


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        return

    text = TARGET.read_text(encoding="utf-8")

    if OLD not in text:
        print("⚠️  Предыдущий патч не найден — возможно уже применён v2 или файл другой.")
        print("   Патч не применён.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    patched = text.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    print(f"✅ Патч применён: {TARGET}")
    print("   - ao.history убран (раздувал контекст)")
    print("   - ac.history убран")
    print("   + ao.pivots оставлен (последние 6 — MIN/MAX с ценой и датой)")
    print()
    print("Теперь запускай:")
    print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 100")


if __name__ == "__main__":
    main()
