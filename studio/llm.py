# studio/llm.py
import requests
from studio.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL, HTTP_TIMEOUT


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
    if not content or not content.strip():
        raise RuntimeError("Модель вернула пустой ответ")

    return content
