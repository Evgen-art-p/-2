# studio/assembly/broadcaster.py
# Студия «Шесть Пальцев» · 2026 · Спринт 20
#
# Broadcaster — публикует пост в социальную сеть.
# Единственная ответственность: получить команду → опубликовать → вернуть post_id.
#
# Правила:
#   - Никакого UI.
#   - Токены читает из clients/{client_id}/social_config.json.
#   - Результат пишет в clients/{client_id}/pending_posts.json.
#   - Статус опубликованного поста: "published".
#   - ministry.record_outcome НЕ вызывает — это работа Metrics Daemon.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CLIENTS_DIR = Path("clients")


# ═══════════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API
# ═══════════════════════════════════════════════════════════════

def publish(client_id: str, project_id: str) -> dict:
    """
    Публикует пост клиента.

    Читает deliverables из папки проекта.
    Читает токены из clients/{client_id}/social_config.json.
    Пишет запись в clients/{client_id}/pending_posts.json.

    Returns:
        {"post_id": str, "platform": str}

    Raises:
        RuntimeError — с понятным текстом если что-то не так.
    """
    cfg          = _load_config(client_id)
    deliverables = _load_deliverables(client_id, project_id)
    platform     = deliverables.get("platform") or cfg.get("default_platform", "telegram")

    if platform == "telegram":
        post_id = _post_telegram(cfg, deliverables)
    elif platform == "vk":
        post_id = _post_vk(cfg, deliverables)
    else:
        raise RuntimeError(f"Неизвестная платформа: {platform}")

    _save_pending(client_id, project_id, platform, post_id,
                  deliverables.get("tim_forecast"))
    return {"post_id": post_id, "platform": platform}


def get_status(client_id: str, project_id: str) -> dict:
    """
    Возвращает текущий статус поста.

    Returns:
        {
            "state": "idle" | "published" | "scored",
            "post_id": str | None,
            "platform": str | None,
            "published_at": str | None,
            "real_viral_score": float | None,
            "tim_forecast": float | None,
        }
    """
    entry = _find_entry(client_id, project_id)
    if not entry:
        return {"state": "idle", "post_id": None, "platform": None,
                "published_at": None, "real_viral_score": None, "tim_forecast": None}
    return {
        "state":           entry.get("status", "published"),
        "post_id":         entry.get("post_id"),
        "platform":        entry.get("platform"),
        "published_at":    entry.get("published_at"),
        "real_viral_score": entry.get("real_viral_score"),
        "tim_forecast":    entry.get("tim_forecast"),
    }


# ═══════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════

def _post_telegram(cfg: dict, deliverables: dict) -> str:
    try:
        import requests
    except ImportError:
        raise RuntimeError("Установи requests: pip install requests")

    tg    = cfg["platforms"]["telegram"]
    token = tg.get("bot_token", "").strip()
    chan  = tg.get("channel_id", "").strip()

    if not token:
        raise RuntimeError("Telegram Bot Token не задан в social_config клиента")
    if not chan:
        raise RuntimeError("Telegram Channel ID не задан в social_config клиента")

    caption  = deliverables.get("caption", "")
    hashtags = " ".join(deliverables.get("hashtags", []))
    text     = f"{caption}\n\n{hashtags}".strip()[:1024]
    base     = f"https://api.telegram.org/bot{token}"
    img      = deliverables.get("image_path", "")

    if img and Path(img).exists():
        with open(img, "rb") as f:
            r = requests.post(f"{base}/sendPhoto",
                              data={"chat_id": chan, "caption": text, "parse_mode": "HTML"},
                              files={"photo": f}, timeout=30)
    else:
        r = requests.post(f"{base}/sendMessage",
                          json={"chat_id": chan, "text": text, "parse_mode": "HTML"},
                          timeout=30)

    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API: {data.get('description', r.text)}")
    return str(data["result"]["message_id"])


# ═══════════════════════════════════════════════════════════════
# VK
# ═══════════════════════════════════════════════════════════════

def _post_vk(cfg: dict, deliverables: dict) -> str:
    try:
        import requests
    except ImportError:
        raise RuntimeError("Установи requests: pip install requests")

    vk       = cfg["platforms"]["vk"]
    token    = vk.get("token", "").strip()
    owner_id = vk.get("owner_id", "").strip()

    if not token:
        raise RuntimeError("VK Token не задан в social_config клиента")

    api     = "https://api.vk.com/method"
    base    = {"access_token": token, "v": "5.199"}
    caption = deliverables.get("caption", "")
    tags    = " ".join(deliverables.get("hashtags", []))
    message = f"{caption}\n\n{tags}".strip()
    attach  = ""

    img = deliverables.get("image_path", "")
    if img and Path(img).exists():
        r1  = requests.get(f"{api}/photos.getWallUploadServer",
                           params={**base, "group_id": owner_id.lstrip("-")}, timeout=15).json()
        url = r1["response"]["upload_url"]
        with open(img, "rb") as f:
            r2 = requests.post(url, files={"photo": f}, timeout=30).json()
        r3 = requests.get(f"{api}/photos.saveWallPhoto", params={
            **base, "group_id": owner_id.lstrip("-"),
            "photo": r2["photo"], "server": r2["server"], "hash": r2["hash"],
        }, timeout=15).json()
        ph     = r3["response"][0]
        attach = f"photo{ph['owner_id']}_{ph['id']}"

    params = {**base, "owner_id": owner_id, "message": message, "from_group": 1}
    if attach:
        params["attachments"] = attach

    r = requests.get(f"{api}/wall.post", params=params, timeout=15).json()
    if "error" in r:
        raise RuntimeError(f"VK API: {r['error'].get('error_msg', r)}")
    return str(r["response"]["post_id"])


# ═══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def _load_config(client_id: str) -> dict:
    p = CLIENTS_DIR / client_id / "social_config.json"
    if not p.exists():
        raise RuntimeError(
            f"social_config.json не найден для клиента '{client_id}'.\n"
            f"Создай файл: {p}"
        )
    return json.loads(p.read_text(encoding="utf-8"))


def _load_deliverables(client_id: str, project_id: str) -> dict:
    """Ищет claudia_final.json в папке проекта."""
    search_paths = [
        CLIENTS_DIR / client_id / "jobs",
        Path("runs"),
        Path("output"),
    ]
    for base in search_paths:
        for match in base.glob(f"*{project_id}*"):
            if not match.is_dir():
                continue
            for fname in ("claudia_final.json", "final_output.json", "deliverables.json"):
                p = match / fname
                if p.exists():
                    data = json.loads(p.read_text(encoding="utf-8"))
                    dl   = data.get("deliverables", {})
                    return {
                        "image_path":   dl.get("image_path", ""),
                        "caption":      dl.get("caption", ""),
                        "hashtags":     dl.get("hashtags", []),
                        "platform":     data.get("final_dna", {}).get("platform", ""),
                        "tim_forecast": (
                            data.get("chain_data", {})
                                .get("tim_analytics", {})
                                .get("viral_score")
                        ),
                    }
    raise RuntimeError(
        f"claudia_final.json не найден для проекта '{project_id}'.\n"
        f"Убедись что пайплайн завершён."
    )


def _save_pending(client_id: str, project_id: str, platform: str,
                  post_id: str, tim_forecast) -> None:
    p    = CLIENTS_DIR / client_id / "pending_posts.json"
    data = []
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = [e for e in data if e.get("project_id") != project_id]
    data.append({
        "project_id":      project_id,
        "client_id":       client_id,
        "platform":        platform,
        "post_id":         post_id,
        "published_at":    datetime.now(timezone.utc).isoformat(),
        "status":          "published",
        "tim_forecast":    tim_forecast,
        "scored_at":       None,
        "real_metrics":    None,
        "real_viral_score": None,
    })
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_entry(client_id: str, project_id: str) -> dict | None:
    p = CLIENTS_DIR / client_id / "pending_posts.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return next((e for e in data if e["project_id"] == project_id), None)
    except Exception:
        return None
