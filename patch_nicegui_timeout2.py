#!/usr/bin/env python3
"""
patch_nicegui_timeout2.py — ПАТЧ v2: WebSocket timeout без ping_interval

NiceGUI не принимает ping_interval напрямую в ui.run().
Используем только reconnect_timeout — это стандартный параметр NiceGUI.
Для keep-alive добавляем JS на стороне клиента.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"nicegui_timeout2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

# ── Патч 1: main.py — убираем неподдерживаемые параметры ──────────

MAIN_OLD_BROKEN = """if __name__ in {"__main__", "__mp_main__"}:
    # ПАТЧ nicegui_timeout:
    # reconnect_timeout=300 — браузер ждёт переподключения 5 минут
    #   (LLM-запросы могут идти 30-90 сек, дефолт NiceGUI ~30 сек)
    # ping_interval=15, ping_timeout=60 — сервер пингует браузер каждые 15 сек
    #   чтобы WebSocket не считался мёртвым при длинных запросах
    ui.run(
        reload=False,
        reconnect_timeout=300,
        ping_interval=15,
        ping_timeout=60,
    )"""

MAIN_OLD_ORIGINAL = """if __name__ in {"__main__", "__mp_main__"}:
    ui.run(reload=False)"""

MAIN_NEW = """if __name__ in {"__main__", "__mp_main__"}:
    # reconnect_timeout=300: браузер ждёт 5 минут пока агент думает
    # (дефолт NiceGUI ~30 сек — меньше чем один LLM-запрос)
    ui.run(
        reload=False,
        reconnect_timeout=300,
    )"""

# ── Патч 2: добавляем JS keep-alive в page_workshop (ui.py) ───────
# Вставляем после ui.add_head_html(f'<style>{IDENTITY_BUREAU_CSS}</style>')
# JS посылает ping каждые 20 сек чтобы WS не умирал

WORKSHOP_OLD = """    ui.add_head_html(f'<style>{IDENTITY_BUREAU_CSS}</style>')"""

WORKSHOP_NEW = """    ui.add_head_html(f'<style>{IDENTITY_BUREAU_CSS}</style>')
    # ПАТЧ: JS keep-alive — посылает пустое сообщение каждые 20 сек
    # чтобы WebSocket не закрывался пока агент думает (LLM 30-90 сек)
    ui.add_head_html(\"\"\"<script>
    (function() {
        var _kaTimer = null;
        function _startKeepalive() {
            if (_kaTimer) return;
            _kaTimer = setInterval(function() {
                try {
                    // NiceGUI использует глобальный socket объект
                    if (window.socket && window.socket.connected) {
                        window.socket.emit('keepalive', {});
                    }
                } catch(e) {}
            }, 20000);
        }
        // Запускаем после загрузки страницы
        if (document.readyState === 'complete') {
            _startKeepalive();
        } else {
            window.addEventListener('load', _startKeepalive);
        }
    })();
    </script>\"\"\")"""

def apply(path: Path, old: str, new: str, desc: str) -> bool:
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    new_content = content.replace(old, new, 1)
    if DRY_RUN:
        print(f"  [DRY] {path.name}: {desc}")
        return True
    backup(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"  ❌ Синтакс-ошибка: {e}")
        return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {path.name}: {desc}")
    return True

def main():
    print("=" * 55)
    print("ПАТЧ v2: NiceGUI timeout (только reconnect_timeout)")
    print("=" * 55)
    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    main_path = Path("main.py")
    ui_path   = Path("studio/workshop/ui.py")

    # Патч main.py — пробуем оба варианта (сломанный и оригинальный)
    print("\n[1/2] main.py — reconnect_timeout=300")
    ok1 = apply(main_path, MAIN_OLD_BROKEN,   MAIN_NEW, "убираем ping_interval, оставляем reconnect_timeout")
    if not ok1:
        ok1 = apply(main_path, MAIN_OLD_ORIGINAL, MAIN_NEW, "добавляем reconnect_timeout=300")
    if not ok1:
        print("  ❌ main.py не пропатчен")

    # Патч ui.py — JS keep-alive
    print("\n[2/2] studio/workshop/ui.py — JS keep-alive (WS ping каждые 20 сек)")
    ok2 = apply(ui_path, WORKSHOP_OLD, WORKSHOP_NEW, "JS keep-alive в head")

    print("\n" + "=" * 55)
    if not DRY_RUN:
        if ok1 or ok2:
            print("✅ Патч применён!")
            print(f"   Бекапы: {BACKUP_DIR}")
            print()
            print("reconnect_timeout=300 — браузер ждёт 5 мин переподключения")
            print("JS keep-alive        — WebSocket не умирает при долгих LLM")
            print()
            print("Перезапусти: python main.py")
        else:
            print("⚠ Ничего не изменено")
    else:
        print("DRY-RUN завершён.")

if __name__ == "__main__":
    main()
