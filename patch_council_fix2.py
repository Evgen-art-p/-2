"""
patch_council_fix2.py
=====================
1. Аватары — маппинг resident_id → имя файла (LOKA.png, JEM.png)
2. Обводка выбранной плитки — тише, не ядовитая
3. Карточка не исчезает при update_all()

Запуск: python patch_council_fix2.py
"""

import shutil
import subprocess
from pathlib import Path

DASHBOARD = Path("studio/economy/ui_dashboard.py")


def patch():
    if not DASHBOARD.exists():
        print("  ❌ ui_dashboard.py не найден")
        return False

    src = DASHBOARD.read_text(encoding="utf-8")
    changed = False

    # ── 1. Аватары — маппинг id → файл ───────────────────────────────
    OLD_AVATAR = '''    def _get_council_avatar(resident_id: str) -> str:
        from studio.cabinet.agents import get_avatar_url
        return get_avatar_url(resident_id, "residents")'''

    NEW_AVATAR = '''    def _get_council_avatar(resident_id: str) -> str:
        """Аватар резидента. Маппинг ID → имя файла в static/avatars/residents/."""
        _ID_TO_FILE = {
            "001_GENESIS_LOKA":    "LOKA",
            "002_GENESIS_CREATOR": "JEM",
            "007_KEI":             "007_KEI",
            "008_JUST":            "008_JUST",
        }
        from pathlib import Path as _P
        name = _ID_TO_FILE.get(resident_id, resident_id)
        avatars_dir = _P("static/avatars/residents")
        for ext in (".png", ".jpg", ".webp"):
            if (avatars_dir / (name + ext)).exists():
                return "/avatars/residents/" + name + ext
        # Fallback: через get_avatar_url
        try:
            from studio.cabinet.agents import get_avatar_url
            return get_avatar_url(resident_id, "residents")
        except Exception:
            return ""'''

    # Проверяем оба варианта (с fallback или без)
    if OLD_AVATAR in src:
        src = src.replace(OLD_AVATAR, NEW_AVATAR)
        print("  ✅ _get_council_avatar() — маппинг добавлен")
        changed = True
    elif '"""Путь к аватару резидента.' in src:
        # Уже патчена v1 — заменяем полностью
        start = src.find("    def _get_council_avatar(resident_id: str) -> str:")
        end   = src.find("\n    def ", start + 10)
        if start != -1 and end != -1:
            src = src[:start] + NEW_AVATAR + "\n" + src[end:]
            print("  ✅ _get_council_avatar() — маппинг добавлен (замена v1)")
            changed = True
    else:
        print("  ⚠  _get_council_avatar() — маркер не найден")

    # ── 2. Обводка — убираем ядовитый цвет ───────────────────────────
    # Меняем логику: выбранная плитка — тонкая обводка цветом резидента
    # невыбранная — почти без обводки
    OLD_BORDER = (
        '                    _border = "2px solid " + _color if _sel '
        'else "1px solid rgba(99,130,255,0.12)"\n'
        '                    _bg     = "rgba(99,130,255,0.10)" if _sel '
        'else "rgba(99,130,255,0.04)"'
    )
    NEW_BORDER = (
        '                    _border = "1px solid " + _color + "88" if _sel '
        'else "1px solid rgba(99,130,255,0.10)"\n'
        '                    _bg     = "rgba(99,130,255,0.07)" if _sel '
        'else "rgba(99,130,255,0.03)"'
    )
    if OLD_BORDER in src:
        src = src.replace(OLD_BORDER, NEW_BORDER)
        print("  ✅ Обводка плитки — тише")
        changed = True
    else:
        print("  ⚠  Обводка — маркер не найден")

    # ── 3. render_detail() не трогает Совет ──────────────────────────
    OLD_DETAIL = '''    def render_detail():
        el = refs["detail_panel"]
        if not el:
            return
        el.clear()

        aid = state["selected_agent"]'''

    NEW_DETAIL = '''    def render_detail():
        el = refs["detail_panel"]
        if not el:
            return
        if state.get("center_view") == "council":
            return
        el.clear()

        aid = state["selected_agent"]'''

    if "center_view" not in src.split("def render_detail")[1].split("def ")[0]:
        if OLD_DETAIL in src:
            src = src.replace(OLD_DETAIL, NEW_DETAIL)
            print("  ✅ render_detail() защищена в режиме Совета")
            changed = True
    else:
        print("  ✅ render_detail() уже защищена")

    if changed:
        DASHBOARD.write_text(src, encoding="utf-8")
    return True


def main():
    print("\n🔧 ПАТЧ: Аватары + обводка + карточка")
    print("=" * 42)

    bak = DASHBOARD.with_suffix(".py.bak4")
    shutil.copy2(DASHBOARD, bak)
    print(f"📦 Бэкап: {bak}")

    patch()

    result = subprocess.run(
        ["python", "-m", "py_compile", str(DASHBOARD)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Синтаксис OK")
        print()
        print("Перезапусти студию.")
        print("Аватары Локи и Джема должны появиться.")
        print("Обводка выбранной плитки — тихая, не ядовитая.")
        print("Карточка не исчезает.")
    else:
        print(f"❌ Ошибка:\n{result.stderr}")
        shutil.copy2(bak, DASHBOARD)
        print("↩ Бэкап восстановлен")


if __name__ == "__main__":
    main()
