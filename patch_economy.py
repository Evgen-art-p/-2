#!/usr/bin/env python3
"""
ПАТЧ: studio/economy/ — экономический модуль студии
Глубокое Резюме Системы, Этапы 1, 2, 6-7

Запускать из КОРНЯ проекта:
    python patch_economy.py

Что делает:
  1. Создаёт папку studio/economy/
  2. Создаёт studio/economy/__init__.py
  3. Создаёт studio/economy/ledger.py        (Этап 1 — Billing Reality)
  4. Создаёт studio/economy/cost_intuition.py (Этап 2 — Cost Intuition)
  5. Создаёт studio/economy/ministry.py       (Этапы 6-7 — Ministry Selection)
  6. Создаёт studio/economy/data/             (папка для данных)
  7. Бэкапит studio/llm.py → llm.py.bak_economy
  8. Патчит studio/llm.py — добавляет запись в ledger

ПРИНЦИП:
  ❌ не управляй поведением напрямую
  ✅ управляй только последствиями поведения
"""

import shutil
from pathlib import Path

ROOT  = Path(__file__).resolve().parent
STUDIO = ROOT / "studio"
ECONOMY = STUDIO / "economy"
DATA_DIR = ECONOMY / "data"

# ───────────────────────────────────────────────────────────
# ФАЙЛЫ МОДУЛЯ
# ───────────────────────────────────────────────────────────

FILES = {}

FILES["__init__.py"] = '''\
# studio/economy/__init__.py
"""
ЭКОНОМИЧЕСКИЙ МОДУЛЬ СТУДИИ (Глубокое Резюме Системы)

  Этап 1 — ledger.py          : Billing Reality   — физический слой
  Этап 2 — cost_intuition.py  : Cost Intuition     — ощущение дороговизны
  Этап 6 — ministry.py        : Ministry Selection — естественный отбор

Импорт снаружи:
  from studio.economy import ledger
  from studio.economy import cost_intuition
  from studio.economy import ministry
"""

from studio.economy import ledger           # noqa: F401
from studio.economy import cost_intuition   # noqa: F401
from studio.economy import ministry         # noqa: F401

__all__ = ["ledger", "cost_intuition", "ministry"]
'''

FILES["ledger.py"] = '''\
# studio/economy/ledger.py
"""
ЭТАП 1 — БИЛЛИНГ КАК ИСТИНА (Глубокое Резюме Системы)

Физический слой экономики студии.
Никакой логики. Только запись реальности.

Каждый LLM вызов = реальный расход.
Это "гравитация системы" — единственная жёсткая правда.

Хранение: studio/economy/data/billing_ledger.jsonl
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from studio.config import BASE_DIR

# ═══════════════════════════════════════════════════════════
# СТОИМОСТЬ МОДЕЛЕЙ (per 1M tokens, USD)
# Обновляй при изменении тарифов OpenRouter
# ═══════════════════════════════════════════════════════════
MODEL_PRICES: dict[str, dict[str, float]] = {
    "google/gemini-2.5-flash":          {"input": 0.15,  "output": 0.60},
    "google/gemini-2.0-flash":          {"input": 0.10,  "output": 0.40},
    "google/gemini-1.5-flash":          {"input": 0.075, "output": 0.30},
    "anthropic/claude-sonnet-4-5":      {"input": 3.00,  "output": 15.00},
    "anthropic/claude-3-haiku":         {"input": 0.25,  "output": 1.25},
    "openai/gpt-4o-mini":               {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                    {"input": 2.50,  "output": 10.00},
    "_default":                         {"input": 0.50,  "output": 2.00},
}

DATA_DIR   = BASE_DIR / "studio" / "economy" / "data"
LEDGER_FILE = DATA_DIR / "billing_ledger.jsonl"
_lock = threading.Lock()


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = MODEL_PRICES.get(model, MODEL_PRICES["_default"])
    return round(
        prompt_tokens     / 1_000_000 * prices["input"] +
        completion_tokens / 1_000_000 * prices["output"],
        8
    )


def record(
    agent_id: str,
    slot_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    call_type: str = "chat",
) -> dict:
    """
    Записывает один LLM вызов в лог.

    Args:
        agent_id:          ID агента ("A03", "loka", ...)
        slot_id:           ID цеха ("turbo", "living_book", ...)
        model:             Модель OpenRouter
        prompt_tokens:     Входные токены из usage
        completion_tokens: Выходные токены из usage
        call_type:         chat | chat_with_tools | chat_with_images
    """
    _ensure()
    cost_usd = _calc_cost(model, prompt_tokens, completion_tokens)

    entry = {
        "ts":                datetime.now(timezone.utc).isoformat(),
        "agent_id":          agent_id,
        "slot_id":           slot_id,
        "model":             model,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "cost_usd":          cost_usd,
        "call_type":         call_type,
    }

    with _lock:
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\\n")

    return entry


def read_all(limit: int = None) -> list[dict]:
    if not LEDGER_FILE.exists():
        return []
    with _lock:
        lines = LEDGER_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries[-limit:] if limit else entries


def total_spent() -> float:
    return round(sum(e["cost_usd"] for e in read_all()), 6)


def agent_spent(agent_id: str, slot_id: str = None) -> float:
    entries = [e for e in read_all() if e["agent_id"] == agent_id]
    if slot_id:
        entries = [e for e in entries if e["slot_id"] == slot_id]
    return round(sum(e["cost_usd"] for e in entries), 6)


def slot_spent(slot_id: str) -> float:
    return round(
        sum(e["cost_usd"] for e in read_all() if e["slot_id"] == slot_id), 6
    )


def recent_by_agent(agent_id: str, slot_id: str = None, n: int = 20) -> list[dict]:
    entries = [e for e in read_all() if e["agent_id"] == agent_id]
    if slot_id:
        entries = [e for e in entries if e["slot_id"] == slot_id]
    return entries[-n:]
'''

FILES["cost_intuition.py"] = '''\
# studio/economy/cost_intuition.py
"""
ЭТАП 2 — COST INTUITION (Глубокое Резюме Системы)

Агент НЕ видит деньги напрямую.
Он видит:
  - "ощущение дороговизны"
  - "вес решения"
  - "риск потери бюджета"

Это превращает экономику в интуицию.
get_prompt_hint() → вставляй в промпт агента перед работой.
"""

from studio.economy import ledger

COST_THRESHOLDS = {
    "cheap":     0.0005,
    "medium":    0.003,
    "expensive": 0.010,
}
WINDOW = 10


def _classify(avg_cost: float) -> str:
    if avg_cost < COST_THRESHOLDS["cheap"]:
        return "cheap"
    elif avg_cost < COST_THRESHOLDS["medium"]:
        return "medium"
    elif avg_cost < COST_THRESHOLDS["expensive"]:
        return "expensive"
    return "risky"


def _feeling(level: str) -> str:
    return {
        "cheap":     "Ты чувствуешь лёгкость — твои последние действия не создавали давления на бюджет. Работай уверенно.",
        "medium":    "Ты чувствуешь умеренный вес своих решений. Каждый шаг имеет значение — выбирай стратегии осознанно.",
        "expensive": "Ты ощущаешь тяжесть — твои последние вызовы стоили дорого. Думай экономно, ищи более лёгкие пути.",
        "risky":     "Ты чувствуешь давление — бюджет под угрозой. Действуй с максимальной осторожностью.",
    }[level]


def get_intuition(agent_id: str, slot_id: str = None) -> dict:
    """Полная экономическая интуиция агента."""
    recent = ledger.recent_by_agent(agent_id, slot_id=slot_id, n=WINDOW)
    total  = ledger.agent_spent(agent_id, slot_id=slot_id)

    if not recent:
        return {
            "level": "medium", "label": "нет истории",
            "avg_cost": 0.0, "total_spent": 0.0, "calls_seen": 0,
            "prompt_hint": "",
        }

    avg_cost = sum(e["cost_usd"] for e in recent) / len(recent)
    level    = _classify(avg_cost)

    hint = f"[ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]\\n{_feeling(level)}\\nУровень: {level.upper()}"

    return {
        "level":       level,
        "avg_cost":    round(avg_cost, 8),
        "total_spent": total,
        "calls_seen":  len(recent),
        "prompt_hint": hint,
    }


def get_prompt_hint(agent_id: str, slot_id: str = None) -> str:
    """Быстрый доступ: только строка для вставки в промпт."""
    return get_intuition(agent_id, slot_id)["prompt_hint"]
'''

FILES["ministry.py"] = '''\
# studio/economy/ministry.py
"""
ЭТАПЫ 6-7 — MINISTRY AS SELECTION (Глубокое Резюме Системы)

Министерство НЕ принимает решения во время рана.
Только post-fact:
  - фиксирует исходы
  - усиливает успешные паттерны
  - ослабляет неуспешные
  - формирует режим для следующего рана

Никакого "управления сверху" — только естественный отбор.

Хранение: studio/economy/data/ministry.json
"""

import json
import threading
from pathlib import Path

from studio.config import BASE_DIR

DATA_DIR      = BASE_DIR / "studio" / "economy" / "data"
MINISTRY_FILE = DATA_DIR / "ministry.json"
_lock = threading.Lock()


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    if not MINISTRY_FILE.exists():
        return {}
    try:
        return json.loads(MINISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _ensure()
    MINISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _key(agent_id: str, slot_id: str) -> str:
    return f"{agent_id}::{slot_id}"


def record_outcome(
    agent_id: str,
    slot_id: str,
    score: float,
    cost_usd: float,
) -> None:
    """
    Фиксирует исход рана. Вызывается post-fact после QA оценки.

    Args:
        agent_id: ID агента
        slot_id:  ID цеха
        score:    Оценка QA (0-10)
        cost_usd: Стоимость рана
    """
    with _lock:
        data = _load()
        k = _key(agent_id, slot_id)

        if k not in data:
            data[k] = {
                "agent_id":       agent_id,
                "slot_id":        slot_id,
                "runs_total":     0,
                "runs_success":   0,
                "runs_fail":      0,
                "cost_success":   0.0,
                "cost_fail":      0.0,
                "score_sum":      0.0,
                "economy_rating": 1.0,
                "mode":           "normal",
            }

        r = data[k]
        r["runs_total"] += 1
        r["score_sum"]  += score

        if score >= 7:
            r["runs_success"] += 1
            r["cost_success"] += cost_usd
        elif score < 5:
            r["runs_fail"]    += 1
            r["cost_fail"]    += cost_usd

        r["economy_rating"] = _calc_rating(r)
        r["mode"]           = _calc_mode(r)
        _save(data)


def get_agent_stats(agent_id: str, slot_id: str) -> dict:
    """Статистика агента в цехе."""
    return _load().get(_key(agent_id, slot_id), {
        "agent_id": agent_id, "slot_id": slot_id,
        "runs_total": 0, "economy_rating": 1.0, "mode": "normal",
    })


def get_mode(agent_id: str, slot_id: str) -> str:
    """Режим для следующего рана: frugal | normal | generous."""
    return get_agent_stats(agent_id, slot_id).get("mode", "normal")


def get_prompt_hint(agent_id: str, slot_id: str) -> str:
    """Текстовый блок от Министерства для промпта агента."""
    stats = get_agent_stats(agent_id, slot_id)
    if stats.get("runs_total", 0) < 3:
        return ""  # мало данных — молчим

    mode = stats.get("mode", "normal")
    return {
        "frugal":   "[МИНИСТЕРСТВО] Твои прошлые раны были дорогими и слабыми. Ищи более экономные пути. Меньше токенов — точнее результат.",
        "normal":   "",
        "generous": "[МИНИСТЕРСТВО] Ты показываешь стабильный результат. Можешь позволить себе глубже проработать задачу.",
    }.get(mode, "")


def leaderboard(slot_id: str = None) -> list[dict]:
    """Рейтинг агентов по экономической эффективности."""
    records = list(_load().values())
    if slot_id:
        records = [r for r in records if r["slot_id"] == slot_id]
    return sorted(records, key=lambda r: r.get("economy_rating", 1.0), reverse=True)


def _calc_rating(r: dict) -> float:
    total = r["runs_total"]
    if total == 0:
        return 1.0
    success_rate = r["runs_success"] / total
    avg_sc = r["cost_success"] / r["runs_success"] if r["runs_success"] else 0.0
    avg_fc = r["cost_fail"]    / r["runs_fail"]    if r["runs_fail"]    else 0.0
    penalty = min(0.3, avg_fc / avg_sc * 0.15) if avg_sc > 0 and avg_fc > 0 else 0.0
    return round(max(0.1, min(2.0, 0.5 + success_rate * 1.5 - penalty)), 3)


def _calc_mode(r: dict) -> str:
    if r["runs_total"] < 3:
        return "normal"
    rating = r["economy_rating"]
    if rating >= 1.4:
        return "generous"
    if rating <= 0.6:
        return "frugal"
    return "normal"
'''

# ───────────────────────────────────────────────────────────
# НОВЫЙ llm.py С ИНТЕГРАЦИЕЙ economy.ledger
# ───────────────────────────────────────────────────────────

LLM_NEW = '''\
# studio/llm.py
import json
import requests
from studio.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL, HTTP_TIMEOUT, TAVILY_KEY
from studio.economy import ledger as _ledger


def stress_to_temperature(stress: float = 0.0, light: float = 0.8) -> float:
    """Вычисляет temperature LLM из ДНК-состояния агента."""
    base = 0.5 + stress * 0.6
    light_mod = (0.5 - light) * 0.15
    temp = base + light_mod
    return round(max(0.3, min(1.2, temp)), 2)


PIPELINE_WEB_SEARCH_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Поиск актуальной информации в интернете через Маяк Пробуждения. "
                "Используй для поиска трендов, новостей, актуальных форматов, "
                "вирусных роликов, статистики платформ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос — конкретный, на языке платформы"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def _exec_tavily_search(query: str) -> str:
    if not TAVILY_KEY:
        return "[Маяк недоступен: TAVILY_KEY не настроен]"
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_KEY, "query": query,
                  "max_results": 5, "include_answer": True, "search_depth": "basic"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        out = ""
        if data.get("answer"):
            out += f"Краткий ответ: {data[\'answer\']}\\n\\n"
        for i, res in enumerate(data.get("results", []), 1):
            out += f"[{i}] {res.get(\'title\',\'\')}\\n{res.get(\'url\',\'\')}\\n{res.get(\'content\',\'\')[:500]}\\n\\n"
        return out or "Ничего не найдено."
    except requests.exceptions.Timeout:
        return "[Маяк: таймаут поиска — Tavily не ответил за 30 сек]"
    except Exception as e:
        return f"[Маяк: ошибка поиска — {e}]"


def _record(data: dict, model: str, agent_id: str, slot_id: str, call_type: str) -> None:
    """Безопасная запись в ledger — никогда не роняет основной вызов."""
    try:
        usage = data.get("usage", {})
        if usage:
            _ledger.record(
                agent_id=agent_id,
                slot_id=slot_id,
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                call_type=call_type,
            )
    except Exception:
        pass


def chat_with_tools(
    system: str,
    user: str,
    knowledge: str = "",
    tools_schema: list = None,
    max_tool_rounds: int = 3,
    temperature: float = None,
    on_tool_call: callable = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
) -> str:
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}

    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    messages.append({"role": "user", "content": user})

    tool_executors = {"web_search": lambda args: _exec_tavily_search(args.get("query", ""))}
    tool_calls_made = 0

    for round_num in range(max_tool_rounds + 1):
        payload = {"model": OPENROUTER_MODEL, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if tools_schema and tool_calls_made < max_tool_rounds:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                              headers=headers, json=payload, proxies=proxies, timeout=HTTP_TIMEOUT)
        except Exception as e:
            raise RuntimeError(f"OpenRouter Tool Use: {e}")

        if r.status_code != 200:
            try:
                err = r.json().get("error", {}).get("message", r.text[:300])
            except Exception:
                err = r.text[:300]
            raise RuntimeError(f"OpenRouter [{r.status_code}]: {err}")

        data = r.json()
        _record(data, payload["model"], agent_id, slot_id, "chat_with_tools")

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        if not msg.get("tool_calls"):
            content = msg.get("content", "")
            if not content or not content.strip():
                raise RuntimeError("Модель вернула пустой ответ (tool use loop)")
            return content

        tool_calls = msg["tool_calls"]
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}
            executor = tool_executors.get(fn_name)
            if executor:
                result = executor(fn_args)
                tool_calls_made += 1
                print(f"[МАЯК] 🔍 {fn_name}({fn_args.get(\'query\',\'\')[:80]}) → {len(result)} симв. (раунд {tool_calls_made}/{max_tool_rounds})")
            else:
                result = f"Неизвестный инструмент: {fn_name}"
            if on_tool_call:
                try:
                    on_tool_call(fn_name, fn_args, result)
                except Exception:
                    pass
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    payload_final = {"model": OPENROUTER_MODEL, "messages": messages}
    if temperature is not None:
        payload_final["temperature"] = temperature
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload_final, proxies=proxies, timeout=HTTP_TIMEOUT)
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content or "[Модель не дала финальный ответ после tool calls]"
    except Exception as e:
        raise RuntimeError(f"Финальный вызов после tools: {e}")


def chat(
    system: str,
    user: str,
    knowledge: str = "",
    history: list = None,
    temperature: float = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
) -> str:
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user})

    payload = {"model": OPENROUTER_MODEL, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json=payload, proxies=proxies, timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    if r.status_code != 200:
        try:
            err_msg = r.json().get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ (пустое тело)")
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Ответ не JSON. Первые 200 символов:\\n{raw_text[:200]}")

    if "choices" not in data or not data["choices"]:
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data[\'error\'].get(\'message\', data[\'error\'])}")
        raise RuntimeError(f"Нет \'choices\' в ответе. Ключи: {list(data.keys())}")

    _record(data, payload["model"], agent_id, slot_id, "chat")

    content = data["choices"][0].get("message", {}).get("content")
    if content is None:
        finish = data["choices"][0].get("finish_reason", "unknown")
        raise RuntimeError(f"Модель не вернула content (finish_reason={finish})")
    if not content.strip():
        raise RuntimeError("Модель вернула пустую строку")
    return content


def chat_with_images(
    system: str,
    user_text: str,
    images: list = None,
    knowledge: str = "",
    history: list = None,
    temperature: float = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
) -> str:
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    user_content = []
    if images:
        for img in images:
            b64, mime, name = img.get("base64",""), img.get("mime_type","image/png"), img.get("name","image")
            if not b64:
                continue
            user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
            user_content.append({"type": "text", "text": f"[Изображение: {name}]"})
    user_content.append({"type": "text", "text": user_text})
    messages.append({"role": "user", "content": user_content})

    payload = {"model": OPENROUTER_MODEL, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json=payload, proxies=proxies, timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    if r.status_code != 200:
        try:
            err_msg = r.json().get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ")
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Ответ не JSON: {raw_text[:200]}")
    if "choices" not in data or not data["choices"]:
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data[\'error\']}")
        raise RuntimeError("Нет choices в ответе")

    _record(data, payload["model"], agent_id, slot_id, "chat_with_images")

    content = data["choices"][0].get("message", {}).get("content")
    if not content or not content.strip():
        raise RuntimeError("Модель вернула пустой ответ")
    return content
'''

# ───────────────────────────────────────────────────────────
# ПРИМЕНЯЕМ
# ───────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ПАТЧ: studio/economy/ — экономический модуль")
    print("=" * 60)
    print()

    # 1. Создаём папки
    ECONOMY.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    print(f"[OK]   Создана папка {ECONOMY.relative_to(ROOT)}")
    print(f"[OK]   Создана папка {DATA_DIR.relative_to(ROOT)}")

    # 2. Пишем файлы модуля
    for filename, code in FILES.items():
        path = ECONOMY / filename
        if path.exists():
            bak = path.with_suffix(path.suffix + ".bak_economy")
            shutil.copy2(path, bak)
            print(f"[BAK]  {path.relative_to(ROOT)} → {bak.name}")
        path.write_text(code, encoding="utf-8")
        print(f"[OK]   Записан {path.relative_to(ROOT)}")

    print()

    # 3. Патчим llm.py
    llm_path = STUDIO / "llm.py"
    if not llm_path.exists():
        print(f"[ERR]  {llm_path} не найден — прерываем")
        return

    bak = STUDIO / "llm.py.bak_economy"
    shutil.copy2(llm_path, bak)
    print(f"[BAK]  llm.py → {bak.name}")

    llm_path.write_text(LLM_NEW, encoding="utf-8")
    print(f"[OK]   Патч llm.py применён")

    print()
    print("─" * 60)
    print("Готово! Структура:")
    print("  studio/economy/")
    print("    __init__.py        ← публичный API")
    print("    ledger.py          ← Этап 1: Billing Reality")
    print("    cost_intuition.py  ← Этап 2: Cost Intuition")
    print("    ministry.py        ← Этапы 6-7: Ministry Selection")
    print("    data/              ← billing_ledger.jsonl, ministry.json")
    print()
    print("  studio/llm.py — все вызовы теперь пишут в ledger")
    print()
    print("Следующий шаг:")
    print("  Интегрировать get_prompt_hint() в build_agent_context()")
    print("  чтобы агент получал экономическое ощущение перед работой")


if __name__ == "__main__":
    main()
