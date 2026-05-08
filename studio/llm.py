# studio/llm.py
import json
import requests
from studio.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL, HTTP_TIMEOUT, TAVILY_KEY
from studio import billing_ledger as _ledger  # ← ДОБАВЛЕНО


def stress_to_temperature(stress: float = 0.0, light: float = 0.8) -> float:
    """Вычисляет temperature LLM из ДНК-состояния агента.

    stress=0.0, light=0.8 → 0.46 (спокойный, точный)
    stress=0.5, light=0.5 → 0.80 (нормальный)
    stress=0.8, light=0.3 → 1.01 (нервничает, хаотичный)
    """
    base = 0.5 + stress * 0.6
    light_mod = (0.5 - light) * 0.15
    temp = base + light_mod
    return round(max(0.3, min(1.2, temp)), 2)


# ═══════════════════════════════════════════════════════════
# PIPELINE TOOL USE — web_search для агентов (Маяк Пробуждения)
# ═══════════════════════════════════════════════════════════

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
    """Синхронный поиск через Tavily API."""
    if not TAVILY_KEY:
        return "[Маяк недоступен: TAVILY_KEY не настроен]"

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_KEY,
                "query": query,
                "max_results": 5,
                "include_answer": True,
                "search_depth": "basic",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        out = ""
        if data.get("answer"):
            out += f"Краткий ответ: {data['answer']}\n\n"
        for i, result in enumerate(data.get("results", []), 1):
            out += (
                f"[{i}] {result.get('title', '')}\n"
                f"{result.get('url', '')}\n"
                f"{result.get('content', '')[:500]}\n\n"
            )
        return out or "Ничего не найдено."

    except requests.exceptions.Timeout:
        return "[Маяк: таймаут поиска — Tavily не ответил за 30 сек]"
    except Exception as e:
        return f"[Маяк: ошибка поиска — {e}]"


def chat_with_tools(
    system: str,
    user: str,
    knowledge: str = "",
    tools_schema: list = None,
    max_tool_rounds: int = 3,
    temperature: float = None,
    on_tool_call: callable = None,
) -> str:
    """Вызов LLM с поддержкой Tool Use (синхронный).

    Цикл:
      1. Отправляем сообщение с tools schema
      2. Если модель вызвала tool — исполняем, отправляем результат
      3. Повторяем до max_tool_rounds или пока модель не ответит текстом

    Args:
        system: системный промпт
        user: контекст + задача
        knowledge: база знаний
        tools_schema: список инструментов (OpenRouter format)
        max_tool_rounds: макс раундов tool_calls (береговая линия)
        temperature: temperature LLM (из ДНК)
        on_tool_call: callback(tool_name, args, result) для логирования

    Returns:
        Финальный текстовый ответ модели
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Собираем messages
    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    messages.append({"role": "user", "content": user})

    tool_executors = {
        "web_search": lambda args: _exec_tavily_search(args.get("query", "")),
    }

    tool_calls_made = 0

    for round_num in range(max_tool_rounds + 1):
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        # Даём tools только если ещё не исчерпали лимит
        if tools_schema and tool_calls_made < max_tool_rounds:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                proxies=proxies,
                timeout=HTTP_TIMEOUT,
            )
        except Exception as e:
            raise RuntimeError(f"OpenRouter Tool Use: {e}")

        if r.status_code != 200:
            try:
                err = r.json().get("error", {}).get("message", r.text[:300])
            except Exception:
                err = r.text[:300]
            raise RuntimeError(f"OpenRouter [{r.status_code}]: {err}")

        data = r.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        # Если модель НЕ вызвала tools — возвращаем текст
        if not msg.get("tool_calls"):
            content = msg.get("content", "")
            if not content or not content.strip():
                raise RuntimeError("Модель вернула пустой ответ (tool use loop)")
            
            # ── BillingLedger: запись реальности (Этап 1) ── ДОБАВЛЕНО
            usage = data.get("usage", {})
            _agent_id = "unknown"
            _slot_id  = "unknown"
            _ledger.record(
                agent_id=_agent_id,
                slot_id=_slot_id,
                model=payload["model"],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                call_type="chat_with_tools",
            )
            # ───────────────────────────────────────────────
            
            return content

        # Модель вызвала tools — исполняем
        tool_calls = msg["tool_calls"]
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        })

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
                print(
                    f"[МАЯК] 🔍 {fn_name}({fn_args.get('query', '')[:80]}) "
                    f"→ {len(result)} симв. (раунд {tool_calls_made}/{max_tool_rounds})"
                )
            else:
                result = f"Неизвестный инструмент: {fn_name}"

            if on_tool_call:
                try:
                    on_tool_call(fn_name, fn_args, result)
                except Exception:
                    pass

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # Исчерпали лимит раундов — финальный вызов без tools
    payload_final = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }
    if temperature is not None:
        payload_final["temperature"] = temperature

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload_final,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # ── BillingLedger: запись реальности (Этап 1) ── ДОБАВЛЕНО
        usage = data.get("usage", {})
        _agent_id = "unknown"
        _slot_id  = "unknown"
        _ledger.record(
            agent_id=_agent_id,
            slot_id=_slot_id,
            model=payload_final["model"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            call_type="chat_with_tools",
        )
        # ───────────────────────────────────────────────
        
        return content or "[Модель не дала финальный ответ после tool calls]"
    except Exception as e:
        raise RuntimeError(f"Финальный вызов после tools: {e}")


def chat(system: str, user: str, knowledge: str = "", history: list = None, temperature: float = None) -> str:
    """
    Отправляет запрос к LLM.
    
    Args:
        system: системный промпт
        user: текущее сообщение пользователя
        knowledge: база знаний (опционально)
        history: история диалога [{"role": "user"/"assistant", "content": "..."}]
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    
    # Добавляем историю диалога (если есть)
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    
    # Текущее сообщение
    messages.append({"role": "user", "content": user})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    try:
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
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    # --- Проверка HTTP-статуса ---
    if r.status_code != 200:
        try:
            err_data = r.json()
            err_msg = err_data.get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    # --- Проверка что тело не пустое ---
    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ (пустое тело)")

    # --- Безопасный парсинг JSON ---
    try:
        data = r.json()
    except Exception as e:
        preview = raw_text[:200]
        raise RuntimeError(f"Ответ не JSON. Первые 200 символов:\n{preview}")

    # --- Проверка структуры ответа ---
    if "choices" not in data or not data["choices"]:
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err))
            raise RuntimeError(f"OpenRouter error: {msg}")
        raise RuntimeError(f"Нет 'choices' в ответе. Ключи: {list(data.keys())}")

    content = data["choices"][0].get("message", {}).get("content")

    # ── BillingLedger: запись реальности (Этап 1) ── ДОБАВЛЕНО
    usage = data.get("usage", {})
    _agent_id = "unknown"
    _slot_id  = "unknown"
    _ledger.record(
        agent_id=_agent_id,
        slot_id=_slot_id,
        model=payload["model"],
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        call_type="chat",
    )
    # ───────────────────────────────────────────────

    if content is None:
        finish = data["choices"][0].get("finish_reason", "unknown")
        raise RuntimeError(f"Модель не вернула content (finish_reason={finish})")

    if not content.strip():
        raise RuntimeError("Модель вернула пустую строку")

    return content


def chat_with_images(system: str, user_text: str, images: list = None,
                     knowledge: str = "", history: list = None, temperature: float = None) -> str:
    """
    Отправляет запрос с изображениями (vision).
    
    Args:
        system: системный промпт
        user_text: текстовое сообщение
        images: список dict [{"base64": "...", "mime_type": "image/png", "name": "file.png"}, ...]
        knowledge: база знаний
        history: история диалога
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    
    # Формируем multimodal content
    user_content = []
    
    # Добавляем изображения
    if images:
        for img in images:
            b64 = img.get("base64", "")
            mime = img.get("mime_type", "image/png")
            name = img.get("name", "image")
            
            if not b64:
                continue
            
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}"
                }
            })
            # Подпись к изображению
            user_content.append({
                "type": "text",
                "text": f"[Изображение: {name}]"
            })
    
    # Добавляем текст
    user_content.append({
        "type": "text",
        "text": user_text
    })
    
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    try:
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
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    if r.status_code != 200:
        try:
            err_data = r.json()
            err_msg = err_data.get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ")

    try:
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Ответ не JSON: {raw_text[:200]}")

    if "choices" not in data or not data["choices"]:
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        raise RuntimeError(f"Нет choices в ответе")

    content = data["choices"][0].get("message", {}).get("content")
    
    # ── BillingLedger: запись реальности (Этап 1) ── ДОБАВЛЕНО
    usage = data.get("usage", {})
    _agent_id = "unknown"
    _slot_id  = "unknown"
    _ledger.record(
        agent_id=_agent_id,
        slot_id=_slot_id,
        model=payload["model"],
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        call_type="chat_with_images",
    )
    # ───────────────────────────────────────────────
    
    if not content or not content.strip():
        raise RuntimeError("Модель вернула пустой ответ")

    return content