# studio/workshop/cabinet_api.py — API вызовы и веб-инструменты
# Вынесено из ui_cabinet.py для модульности

import json
import httpx
from studio.config import OPENROUTER_API_KEY, TAVILY_KEY

# ── OpenRouter config ─────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = OPENROUTER_API_KEY
DEFAULT_MODEL = "deepseek/deepseek-chat"

MODELS_CATALOG = [
    {"id": "google/gemini-2.5-flash",                "name": "Gemini 2.5 Flash",         "price": "$0.15/$0.60", "speed": "fast"},
    {"id": "anthropic/claude-haiku-4-5",              "name": "Claude Haiku 4.5",         "price": "$1/$5",       "speed": "fast"},
    {"id": "deepseek/deepseek-chat",                  "name": "DeepSeek V3",              "price": "$0.14/$0.28", "speed": "mid"},
    {"id": "openai/gpt-4.1-mini",                     "name": "GPT-4.1 mini",             "price": "$0.40/$1.60", "speed": "fast"},
    {"id": "meta-llama/llama-3.3-70b-instruct",       "name": "Llama 3.3 70B Instruct",   "price": "$0.10/$0.32", "speed": "mid"},
    {"id": "anthropic/claude-sonnet-4-5",              "name": "Claude Sonnet 4.5",        "price": "$3/$15",      "speed": "mid"},
]


async def call_openrouter(messages: list, model: str, tools_schema: list | None = None) -> str:
    """Вызов OpenRouter API с поддержкой tool calls.

    Args:
        messages: Список сообщений для API
        model: ID модели OpenRouter
        tools_schema: Схема инструментов (None = без инструментов)

    Returns:
        Текст ответа модели (после обработки tool calls если были)
    """
    from studio.cabinet.tools import execute_tool  # lazy import для избежания циклов

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.8,
    }
    if tools_schema:
        body["tools"] = tools_schema
        body["tool_choice"] = "auto"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "http://localhost:8080/cabinet",
        "X-Title": "sixfingers-cabinet",
    }

    # ── Диагностика ──
    tool_names = [t["function"]["name"] for t in body.get("tools", [])]
    print(f"[CABINET API] 📤 model={model}, tools={tool_names}, messages={len(messages)}")

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(OPENROUTER_URL, json=body, headers=headers)
        res.raise_for_status()
        data = res.json()

    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    finish = choice.get("finish_reason", "?")

    has_tools = bool(msg.get("tool_calls"))
    print(f"[CABINET API] 📥 finish_reason={finish}, has_tool_calls={has_tools}, content_len={len(msg.get('content') or '')}")
    if has_tools:
        for tc in msg["tool_calls"]:
            print(f"[CABINET API] 🔧 tool_call: {tc['function']['name']}({tc['function'].get('arguments', '{}')})")
    else:
        print(f"[CABINET API] 💬 Текст (первые 200): {(msg.get('content') or '')[:200]}")

    # Handle tool calls
    if msg.get("tool_calls"):
        tool_calls = msg["tool_calls"]
        assistant_msg = {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
        tool_results = []

        for tc in tool_calls:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"].get("arguments", "{}"))
            try:
                result = await execute_tool(fn, args)
            except Exception as e:
                result = f"Ошибка: {e}"

            print(f"[CABINET API] 🔧 {fn} → {result[:200]}")
            tool_results.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

        # Second call with tool results
        messages2 = messages + [assistant_msg] + tool_results
        body2 = {"model": model, "messages": messages2, "max_tokens": 2000, "temperature": 0.8}
        print(f"[CABINET API] 📤 Second call: {len(messages2)} messages")

        async with httpx.AsyncClient(timeout=60) as client:
            res2 = await client.post(OPENROUTER_URL, json=body2, headers=headers)
            res2.raise_for_status()
            data2 = res2.json()

        final = (data2.get("choices", [{}])[0].get("message", {}).get("content") or "...").strip()
        print(f"[CABINET API] 📥 Final: {final[:200]}")
        return final

    return (msg.get("content") or "...").strip()


# ── Web Tools ────────────────────────────────────

async def exec_web_search(query: str) -> str:
    """Tavily web search."""
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post("https://api.tavily.com/search", json={
            "api_key": TAVILY_KEY, "query": query,
            "max_results": 5, "include_answer": True, "search_depth": "basic",
        })
        res.raise_for_status()
        data = res.json()

    out = ""
    if data.get("answer"):
        out += f"Краткий ответ: {data['answer']}\n\n"
    for i, r in enumerate(data.get("results", []), 1):
        out += f"[{i}] {r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')[:500]}\n\n"
    return out or "Ничего не найдено."


async def exec_fetch_url(url: str) -> str:
    """Fetch URL via Tavily extract or direct."""
    if TAVILY_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post("https://api.tavily.com/extract", json={
                    "api_key": TAVILY_KEY, "urls": [url],
                })
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("results", [{}])[0].get("raw_content", "")
                    if content:
                        return content[:8000]
        except Exception:
            pass
    # Fallback direct
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(url)
            import re
            text = res.text
            text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:8000]
    except Exception as e:
        return f"Ошибка: {e}"
