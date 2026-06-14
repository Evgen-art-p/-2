# patch_cartridge.py
# Запускать из корня проекта:
#   python patch_cartridge.py
#
# Патчит studio/cartridge.py:
#   Добавляет вызов _call_hook("on_before_run", state) в run() и run_turbo()
#   сразу после on_pipeline_start.
#
# Безопасно для всех цехов: если hooks.py не содержит on_before_run —
# _call_hook тихо вернёт None и продолжит работу.

from pathlib import Path
import shutil
from datetime import datetime

TARGET = Path("studio/cartridge.py")

# ── Патч 1: run() ────────────────────────────────────────────
OLD_RUN = (
    "        self.state[\"_slot_id\"] = self.slot_id\n"
    "        await self.callbacks.on_pipeline_start(self.slot_id, run_type)\n"
    "\n"
    "        # ── ЧЕСТНЫЙ РАБОЧИЙ СТАТУС: смена началась · ПАТЧ city_red №3 ──"
)
NEW_RUN = (
    "        self.state[\"_slot_id\"] = self.slot_id\n"
    "        await self.callbacks.on_pipeline_start(self.slot_id, run_type)\n"
    "\n"
    "        # ── HOOK: on_before_run — подготовка данных перед цепочкой ──\n"
    "        self._call_hook(\"on_before_run\", self.state)\n"
    "\n"
    "        # ── ЧЕСТНЫЙ РАБОЧИЙ СТАТУС: смена началась · ПАТЧ city_red №3 ──"
)

# ── Патч 2: run_turbo() ──────────────────────────────────────
OLD_TURBO = (
    "        await self.callbacks.on_pipeline_start(self.slot_id, run_type)\n"
    "\n"
    "        # ── ЧЕСТНЫЙ РАБОЧИЙ СТАТУС: турбо-смена началась · ПАТЧ city_red №3 ──"
)
NEW_TURBO = (
    "        await self.callbacks.on_pipeline_start(self.slot_id, run_type)\n"
    "\n"
    "        # ── HOOK: on_before_run — подготовка данных перед цепочкой ──\n"
    "        self._call_hook(\"on_before_run\", self.state)\n"
    "\n"
    "        # ── ЧЕСТНЫЙ РАБОЧИЙ СТАТУС: турбо-смена началась · ПАТЧ city_red №3 ──"
)


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Убедись что запускаешь из корня проекта.")
        return

    text = TARGET.read_text(encoding="utf-8")

    missing = []
    if OLD_RUN not in text:
        missing.append("run()")
    if OLD_TURBO not in text:
        missing.append("run_turbo()")

    if missing:
        print(f"⚠️  Не найдены якоря для патча в: {', '.join(missing)}")
        print("   Возможно cartridge.py уже изменён или имеет другой вид.")
        print("   Патч не применён.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    # Применяем оба патча
    patched = text.replace(OLD_RUN, NEW_RUN, 1)
    patched = patched.replace(OLD_TURBO, NEW_TURBO, 1)
    TARGET.write_text(patched, encoding="utf-8")

    print(f"✅ Патч применён: {TARGET}")
    print(f"   + on_before_run в run()")
    print(f"   + on_before_run в run_turbo()")
    print()
    print("Теперь запускай:")
    print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 50")


if __name__ == "__main__":
    main()
