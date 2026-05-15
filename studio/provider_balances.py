# studio/provider_balances.py
"""
Реальные балансы аккаунтов провайдеров через их API.
Используется верхним рядом Economy Dashboard (5-минутный таймер).

Каждая функция возвращает:
    {"balance": float | None, "unit": "$" | "chars" | "¥", "error": str | None}

balance=None → ключ не задан, нет API или запрос упал
unit         → единица: "$" (доллары), "¥" (юани SiliconFlow), "chars" (ElevenLabs)
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from studio.config import (
    OPENROUTER_API_KEY,
    ELEVENLABS_API_KEY,
    SILICONFLOW_API_KEY,
    TAVILY_KEY,
    FAL_KEY,
)

log = logging.getLogger(__name__)
_TIMEOUT = 8   # секунды на один запрос


# ─── helpers ────────────────────────────────────────────────────────────────

def _get(url: str, headers: dict) -> dict | None:
    """GET с тихой обработкой ошибок. Возвращает JSON или None."""
    try:
        r = requests.get(url, headers=headers, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.debug("provider_balances GET %s → %s", url, e)
        return None


# ─── OpenRouter ─────────────────────────────────────────────────────────────

def get_openrouter_balance() -> dict:
    """
    GET https://openrouter.ai/api/v1/auth/key
    Ответ: {"data": {"usage": float, "limit": float|null, ...}}
    balance = limit - usage  (null limit = pay-as-you-go, показываем ···)
    """
    if not OPENROUTER_API_KEY:
        return {"balance": None, "unit": "$", "error": "no key"}
    data = _get(
        "https://openrouter.ai/api/v1/auth/key",
        {"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
    )
    if not data:
        return {"balance": None, "unit": "$", "error": "request failed"}
    try:
        d     = data["data"]
        usage = float(d.get("usage", 0))
        limit = d.get("limit")       # None = pay-as-you-go / unlimit
        if limit is not None:
            return {"balance": round(float(limit) - usage, 4), "unit": "$", "error": None}
        else:
            # Безлимитный ключ: баланса нет, покажем ···
            return {"balance": None, "unit": "$", "error": "unlimited key"}
    except Exception as e:
        return {"balance": None, "unit": "$", "error": str(e)}


# ─── ElevenLabs ─────────────────────────────────────────────────────────────

def get_elevenlabs_balance() -> dict:
    """
    GET https://api.elevenlabs.io/v1/user
    Ответ: {"subscription": {"character_limit": int, "character_count": int, ...}}
    Возвращаем остаток символов (unit="chars"), не доллары.
    """
    if not ELEVENLABS_API_KEY:
        return {"balance": None, "unit": "chars", "error": "no key"}
    data = _get(
        "https://api.elevenlabs.io/v1/user",
        {"xi-api-key": ELEVENLABS_API_KEY},
    )
    if not data:
        return {"balance": None, "unit": "chars", "error": "request failed"}
    try:
        sub   = data.get("subscription", {})
        limit = int(sub.get("character_limit", 0))
        used  = int(sub.get("character_count",  0))
        return {"balance": float(limit - used), "unit": "chars", "error": None}
    except Exception as e:
        return {"balance": None, "unit": "chars", "error": str(e)}


# ─── SiliconFlow ────────────────────────────────────────────────────────────

def get_siliconflow_balance() -> dict:
    """
    GET https://api.siliconflow.cn/v1/user/info
    Ответ: {"code": 20000, "data": {"balance": "10.0000", ...}}
    Валюта — CNY (юани), показываем с символом ¥.
    """
    if not SILICONFLOW_API_KEY:
        return {"balance": None, "unit": "¥", "error": "no key"}
    data = _get(
        "https://api.siliconflow.cn/v1/user/info",
        {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"},
    )
    if not data:
        return {"balance": None, "unit": "¥", "error": "request failed"}
    try:
        raw = data.get("data", {}).get("balance")
        if raw is None:
            return {"balance": None, "unit": "¥", "error": "no balance field"}
        return {"balance": round(float(raw), 4), "unit": "¥", "error": None}
    except Exception as e:
        return {"balance": None, "unit": "¥", "error": str(e)}


# ─── Tavily ─────────────────────────────────────────────────────────────────

def get_tavily_balance() -> dict:
    """
    Tavily не предоставляет публичный balance endpoint.
    TODO: обновить когда появится.
    """
    if not TAVILY_KEY:
        return {"balance": None, "unit": "$", "error": "no key"}
    # Пробуем неофициальный endpoint — тихо провалимся если 404
    data = _get(
        "https://api.tavily.com/v1/usage",
        {"Authorization": f"tvly-{TAVILY_KEY}" if not TAVILY_KEY.startswith("tvly-") else TAVILY_KEY},
    )
    if data and "credits_remaining" in data:
        try:
            return {"balance": float(data["credits_remaining"]), "unit": "$", "error": None}
        except Exception:
            pass
    return {"balance": None, "unit": "$", "error": "no public API"}


# ─── Fal.ai ─────────────────────────────────────────────────────────────────

def get_fal_balance() -> dict:
    """
    GET https://rest.alpha.fal.ai/billing/v1/balance
    Ответ: {"balance": float} (USD)
    Если формат изменился — смотри https://fal.ai/docs/billing
    """
    if not FAL_KEY:
        return {"balance": None, "unit": "$", "error": "no key"}
    data = _get(
        "https://rest.alpha.fal.ai/billing/v1/balance",
        {"Authorization": f"Key {FAL_KEY}"},
    )
    if not data:
        return {"balance": None, "unit": "$", "error": "request failed"}
    try:
        bal = data.get("balance") or data.get("available_balance") or data.get("amount")
        if bal is None:
            return {"balance": None, "unit": "$", "error": "no balance field"}
        return {"balance": round(float(bal), 4), "unit": "$", "error": None}
    except Exception as e:
        return {"balance": None, "unit": "$", "error": str(e)}


# ─── Главная функция ─────────────────────────────────────────────────────────

def get_all_balances() -> dict:
    """
    Параллельно запрашивает балансы всех провайдеров (5 потоков).

    Возвращает:
        {
            "openrouter":  {"balance": 5.12,  "unit": "$",     "error": None},
            "elevenlabs":  {"balance": 42000, "unit": "chars", "error": None},
            "siliconflow": {"balance": 8.50,  "unit": "¥",     "error": None},
            "tavily":      {"balance": None,  "unit": "$",     "error": "no public API"},
            "fal":         {"balance": 2.30,  "unit": "$",     "error": None},
        }
    """
    fetchers = {
        "openrouter":  get_openrouter_balance,
        "elevenlabs":  get_elevenlabs_balance,
        "siliconflow": get_siliconflow_balance,
        "tavily":      get_tavily_balance,
        "fal":         get_fal_balance,
    }

    results: dict = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fn): key for key, fn in fetchers.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"balance": None, "unit": "$", "error": str(e)}

    return results
