#!/usr/bin/env python3
"""
patch_llm_diagnostics.py — добавляем диагностический print в llm.py

Одна строка перед _post_with_retry в функции chat():
  [LLM] → A04 Катя Кат | контекст: 12453 симв | модель: deepseek/...

Это покажет:
  - Ушёл ли запрос вообще (или завис до отправки)
  - Реальный размер контекста для каждого агента
  - Сколько токенов примерно получает A04

Убрать после диагностики: python patch_llm_diagnostics.py --remove
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

REMOVE = "--remove" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"llm_diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path):
    if DRY_RUN: return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / path.name)
    print(f"  ✓ backup → {BACKUP_DIR / path.name}")

def apply(path, old, new, desc):
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠ Не найдено: {desc}")
        return False
    if DRY_RUN:
        print(f"  [DRY] {desc}")
        return True
    backup(path)
    nc = content.replace(old, new, 1)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".py", delete=False) as tmp:
        tmp.write(nc); tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    except py_compile.PyCompileError as e:
        tmp_path.unlink(); print(f"  ❌ {e}"); return False
    shutil.move(str(tmp_path), str(path))
    print(f"  ✓ {desc}")
    return True


# Строка ПЕРЕД _post_with_retry в функции chat()
DIAG_OLD = (
    "    try:\n"
    "        r = _post_with_retry(\n"
    "            \"https://openrouter.ai/api/v1/chat/completions\",\n"
    "            headers={\n"
    "                \"Authorization\": f\"Bearer {OPENROUTER_API_KEY}\",\n"
    "                \"Content-Type\": \"application/json\",\n"
    "            },\n"
    "            json_payload=payload,\n"
    "            proxies=proxies,\n"
    "            timeout=HTTP_TIMEOUT,\n"
    "        )\n"
    "    except requests.exceptions.ProxyError as e:\n"
    "        raise RuntimeError(f\"Прокси недоступен ({PROXY_URL}): {e}\")"
)

DIAG_NEW = (
    "    # ДИАГНОСТИКА: показываем что запрос уходит и размер контекста\n"
    "    _ctx_size = sum(len(str(m.get('content', ''))) for m in messages)\n"
    "    print(f\"[LLM] → {agent_id} | контекст: {_ctx_size} симв | модель: {OPENROUTER_MODEL[:30]}\")\n"
    "    try:\n"
    "        r = _post_with_retry(\n"
    "            \"https://openrouter.ai/api/v1/chat/completions\",\n"
    "            headers={\n"
    "                \"Authorization\": f\"Bearer {OPENROUTER_API_KEY}\",\n"
    "                \"Content-Type\": \"application/json\",\n"
    "            },\n"
    "            json_payload=payload,\n"
    "            proxies=proxies,\n"
    "            timeout=HTTP_TIMEOUT,\n"
    "        )\n"
    "    except requests.exceptions.ProxyError as e:\n"
    "        raise RuntimeError(f\"Прокси недоступен ({PROXY_URL}): {e}\")"
)

# Для --remove
DIAG_NEW_REMOVE = DIAG_OLD  # меняем обратно


def main():
    path = Path("studio/llm.py")

    if REMOVE:
        print("Убираем диагностику...")
        ok = apply(path, DIAG_NEW, DIAG_NEW_REMOVE, "удаляем print")
        if ok:
            print("✅ Диагностика убрана")
        return

    print("=" * 55)
    print("ПАТЧ: Диагностика llm.py — лог перед отправкой")
    print("=" * 55)

    ok = apply(path, DIAG_OLD, DIAG_NEW, "print перед _post_with_retry в chat()")

    if ok:
        print()
        print("✅ Готово! Перезапусти: python main.py")
        print()
        print("В консоли появится:")
        print("  [LLM] → A04 | контекст: XXXXX симв | модель: deepseek/...")
        print()
        print("Если строка НЕ появится для A04 — зависание ДО отправки (баг в коде)")
        print("Если появится — зависание на ожидании ответа OpenRouter (сеть/таймаут)")
        print()
        print("Убрать после: python patch_llm_diagnostics.py --remove")

if __name__ == "__main__":
    main()
