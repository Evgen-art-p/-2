#!/usr/bin/env python3
"""
patch_llm_retry.py — ПАТЧ: Retry + backoff для llm.py

ПРОБЛЕМА:
  Conflict system запускает 4 параллельных LLM-запроса (asyncio.gather).
  OpenRouter или промежуточный прокси сбрасывает соединение (WinError 10054)
  на одном из параллельных потоков. requests падает с ConnectionError.
  Исключение всплывает наверх → event loop ломается → страница перезагружается.

РЕШЕНИЕ:
  Обернуть requests.post в функциях chat(), chat_with_images(), chat_with_tools()
  в retry-цикл с экспоненциальной паузой:
    попытка 1 → сразу
    попытка 2 → пауза 2 сек
    попытка 3 → пауза 5 сек
  ConnectionError и ProtocolError — ретраим. Остальное (400, 401, 429) — нет.

ПРАВКИ: только studio/llm.py — один файл.
"""

import sys
import shutil
import py_compile
import tempfile
from pathlib import Path
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
BACKUP_DIR = Path("_patch_backups") / f"llm_retry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(path: Path):
    if DRY_RUN:
        print(f"  [DRY] backup {path}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / path.name
    shutil.copy2(path, dest)
    print(f"  ✓ backup → {dest}")

def validate_python(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  ❌ СИНТАКС-ОШИБКА: {e}")
        return False

# ══════════════════════════════════════════════════════════════════
# Вставляем импорт time и вспомогательную функцию _post_with_retry
# сразу после строки import requests
# ══════════════════════════════════════════════════════════════════

IMPORT_OLD = """import json
import requests
from studio.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL, HTTP_TIMEOUT, TAVILY_KEY
from studio import billing_ledger as _ledger  # ← ДОБАВЛЕНО"""

IMPORT_NEW = """import json
import time
import requests
from studio.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL, HTTP_TIMEOUT, TAVILY_KEY
from studio import billing_ledger as _ledger  # ← ДОБАВЛЕНО


# ══ RETRY HELPER ══════════════════════════════════════════════════
# Ошибка 10054 (Connection Reset) = OpenRouter/прокси сбросил сокет.
# Это временная сетевая проблема — ретраим с паузой.
# НЕ ретраим: 400 Bad Request, 401 Unauthorized, 429 Rate Limit.

_RETRY_DELAYS = [0, 2, 5]  # секунды перед попыткой 1, 2, 3

def _post_with_retry(url: str, headers: dict, json_payload: dict,
                     proxies: dict = None, timeout: int = None) -> requests.Response:
    \"\"\"requests.post с тремя попытками при сетевых ошибках (10054, ConnectionReset).\"\"\"
    last_err = None
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        if delay > 0:
            print(f"[RETRY] Сеть упала — ждём {delay}с (попытка {attempt}/{len(_RETRY_DELAYS)})...")
            time.sleep(delay)
        try:
            r = requests.post(url, headers=headers, json=json_payload,
                              proxies=proxies, timeout=timeout)
            return r  # успех — возвращаем ответ как есть
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            last_err = e
            print(f"[RETRY] Попытка {attempt} упала: {type(e).__name__}")
            # Не ретраим если это явно не сетевая проблема
            if "ProxyError" in type(e).__name__:
                raise  # прокси не настроен — ретрай бессмысленен
        except requests.exceptions.Timeout:
            raise  # таймаут — ретраить не имеет смысла
    raise requests.exceptions.ConnectionError(
        f"OpenRouter недоступен после {len(_RETRY_DELAYS)} попыток: {last_err}"
    )
# ═════════════════════════════════════════════════════════════════"""

# ══════════════════════════════════════════════════════════════════
# Патч 1: функция chat() — заменяем requests.post на _post_with_retry
# ══════════════════════════════════════════════════════════════════

CHAT_OLD = """    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")"""

CHAT_NEW = """    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json_payload=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")"""

# ══════════════════════════════════════════════════════════════════
# Патч 2: функция chat_with_images() — заменяем requests.post
# ══════════════════════════════════════════════════════════════════

IMAGES_OLD = """    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")"""

IMAGES_NEW = """    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json_payload=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")"""

# ══════════════════════════════════════════════════════════════════
# Патч 3: chat_with_tools() — внутри цикла for round_num in range(...)
# ══════════════════════════════════════════════════════════════════

TOOLS_LOOP_OLD = """        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                proxies=proxies,
                timeout=HTTP_TIMEOUT,
            )
        except Exception as e:
            raise RuntimeError(f"OpenRouter Tool Use: {e}")"""

TOOLS_LOOP_NEW = """        try:
            r = _post_with_retry(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json_payload=payload,
                proxies=proxies,
                timeout=HTTP_TIMEOUT,
            )
        except Exception as e:
            raise RuntimeError(f"OpenRouter Tool Use: {e}")"""

# ══════════════════════════════════════════════════════════════════
# Патч 4: chat_with_tools() — финальный вызов после tool calls
# ══════════════════════════════════════════════════════════════════

TOOLS_FINAL_OLD = """    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload_final,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
        data = r.json()"""

TOOLS_FINAL_NEW = """    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json_payload=payload_final,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
        data = r.json()"""


def apply_patch(content: str, old: str, new: str, description: str) -> tuple[str, bool]:
    if old not in content:
        print(f"  ⚠ Не найдено: {description} (возможно уже пропатчено)")
        return content, False
    result = content.replace(old, new, 1)
    print(f"  ✓ {description}")
    return result, True


def main():
    print("=" * 60)
    print("ПАТЧ: llm.py — retry при ConnectionError (WinError 10054)")
    print("=" * 60)

    if DRY_RUN:
        print("РЕЖИМ: DRY-RUN\n")

    llm_path = Path("studio/llm.py")
    if not llm_path.exists():
        print(f"❌ Файл не найден: {llm_path}")
        sys.exit(1)

    content = llm_path.read_text(encoding="utf-8")
    original = content
    
    patches = [
        (IMPORT_OLD,       IMPORT_NEW,       "добавляем import time + _post_with_retry"),
        (CHAT_OLD,         CHAT_NEW,         "chat(): requests.post → _post_with_retry"),
        (IMAGES_OLD,       IMAGES_NEW,       "chat_with_images(): requests.post → _post_with_retry"),
        (TOOLS_LOOP_OLD,   TOOLS_LOOP_NEW,   "chat_with_tools() loop: requests.post → _post_with_retry"),
        (TOOLS_FINAL_OLD,  TOOLS_FINAL_NEW,  "chat_with_tools() final: requests.post → _post_with_retry"),
    ]

    applied = 0
    for old, new, desc in patches:
        content, ok = apply_patch(content, old, new, desc)
        if ok:
            applied += 1

    if content == original:
        print("\n⚠ Ничего не изменено — файл уже пропатчен или структура изменилась.")
        sys.exit(0)

    if DRY_RUN:
        print(f"\n[DRY] Было бы применено {applied} патчей.")
        sys.exit(0)

    # Валидация через временный файл
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        py_compile.compile(str(tmp_path), doraise=True)
        print(f"\n  ✓ Синтаксис OK")
    except py_compile.PyCompileError as e:
        tmp_path.unlink()
        print(f"\n❌ СИНТАКС-ОШИБКА — патч НЕ применён: {e}")
        sys.exit(1)

    # Бекап и запись
    backup(llm_path)
    import shutil as _sh
    _sh.move(str(tmp_path), str(llm_path))

    print(f"\n{'=' * 60}")
    print(f"✅ Патч применён! ({applied}/5 правок)")
    print(f"   Бекап: {BACKUP_DIR}")
    print(f"\nЧто изменилось:")
    print(f"  • При ConnectionError (10054) — 3 попытки с паузой 0/2/5 сек")
    print(f"  • Параллельные конфликтные запросы больше не роняют event loop")
    print(f"  • Страница перестанет перезагружаться сама")
    print(f"\nПерезапусти студию: python main.py")


if __name__ == "__main__":
    main()
