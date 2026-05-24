# studio/economy/metrics_daemon.py
# Студия «Шесть Пальцев» · 2026 · Спринт 20
#
# Metrics Daemon — независимый фоновый процесс.
# Единственная ответственность: забрать реальные метрики → закрыть петлю.
#
# Алгоритм одного прохода:
#   1. Обойти всех клиентов (clients/*/pending_posts.json)
#   2. Найти посты со статусом "published" у которых прошло > 24ч
#   3. Запросить метрики из API соцсети
#   4. Посчитать real_viral_score
#   5. Вызвать ministry.record_outcome (ЕДИНСТВЕННОЕ место в студии где это происходит)
#   6. Сравнить с прогнозом Тима, записать разницу
#   7. Обновить статус поста → "scored"
#
# Запуск как отдельный процесс:
#   python studio/economy/metrics_daemon.py
#   python studio/economy/metrics_daemon.py --interval 3600   # проверять каждый час
#   python studio/economy/metrics_daemon.py --once            # один проход и выход
#
# Запуск как фоновый поток внутри студии (в studio/__init__.py или main.py):
#   from studio.economy.metrics_daemon import start_background
#   start_background()

from __future__ import annotations

import json
import sys
import time
import threading
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLIENTS_DIR      = Path("clients")
DEFAULT_INTERVAL = 3600        # секунд между проходами (1 час)
MATURITY_HOURS   = 24          # через сколько часов пост "созрел"


# ═══════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════

def run_forever(interval_sec: int = DEFAULT_INTERVAL) -> None:
    """Бесконечный цикл. Проход каждые interval_sec секунд."""
    print(f"[DAEMON] 🟢 Запущен. Интервал: {interval_sec}с. "
          f"Порог созревания: {MATURITY_HOURS}ч.")
    while True:
        try:
            processed = check_all_clients()
            if processed:
                print(f"[DAEMON] ✅ Обработано постов: {processed}")
            else:
                print(f"[DAEMON] 💤 Нет созревших постов. Следующая проверка через {interval_sec}с.")
        except Exception as e:
            print(f"[DAEMON] ❌ Ошибка прохода: {e}")
        time.sleep(interval_sec)


def start_background(interval_sec: int = DEFAULT_INTERVAL) -> threading.Thread:
    """
    Запускает демон в фоновом потоке.
    Вызывай из main.py или studio/__init__.py при старте студии:

        from studio.economy.metrics_daemon import start_background
        start_background()
    """
    t = threading.Thread(
        target=run_forever,
        kwargs={"interval_sec": interval_sec},
        daemon=True,
        name="MetricsDaemon",
    )
    t.start()
    print(f"[DAEMON] 🔄 Фоновый поток запущен (MetricsDaemon)")
    return t


# ═══════════════════════════════════════════════════════════════
# ОДИН ПРОХОД
# ═══════════════════════════════════════════════════════════════

def check_all_clients() -> int:
    """
    Один проход по всем клиентам.
    Возвращает количество обработанных постов.
    """
    if not CLIENTS_DIR.exists():
        return 0

    total = 0
    for client_dir in CLIENTS_DIR.iterdir():
        if not client_dir.is_dir():
            continue
        pending_file = client_dir / "pending_posts.json"
        if not pending_file.exists():
            continue
        total += _process_client(client_dir.name, pending_file)
    return total


def _process_client(client_id: str, pending_file: Path) -> int:
    """Обрабатывает pending_posts одного клиента."""
    try:
        posts = json.loads(pending_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[DAEMON] ⚠️ {client_id}: не могу прочитать pending_posts.json: {e}")
        return 0

    cfg = _load_social_config(client_id)
    if not cfg:
        return 0

    now       = datetime.now(timezone.utc)
    threshold = timedelta(hours=MATURITY_HOURS)
    processed = 0
    changed   = False

    for entry in posts:
        if entry.get("status") != "published":
            continue

        # Проверяем зрелость
        try:
            pub_dt = datetime.fromisoformat(entry["published_at"])
        except (KeyError, ValueError):
            continue

        if now - pub_dt < threshold:
            remaining = threshold - (now - pub_dt)
            h = int(remaining.total_seconds() // 3600)
            m = int((remaining.total_seconds() % 3600) // 60)
            print(f"[DAEMON] ⏳ {client_id}/{entry['project_id']}: созреет через {h}ч {m}мин")
            continue

        # Забираем метрики
        platform   = entry["platform"]
        metrics    = _fetch_metrics(entry, cfg)

        if not metrics:
            print(f"[DAEMON] ⚠️ {client_id}/{entry['project_id']}: метрики недоступны")
            continue

        # Считаем реальный viral_score
        real_score = _calc_score(metrics, platform, cfg.get("score_weights", {}))
        tim_score  = entry.get("tim_forecast")

        print(f"[DAEMON] 📊 {client_id}/{entry['project_id']}: "
              f"реальный={real_score} | прогноз Тима={tim_score}")

        # Закрываем петлю → Министерство
        _report_to_ministry(client_id, platform, real_score, entry["project_id"])

        # Обновляем запись
        entry["status"]          = "scored"
        entry["scored_at"]       = now.isoformat()
        entry["real_metrics"]    = metrics
        entry["real_viral_score"] = real_score
        if tim_score is not None:
            entry["forecast_delta"] = round(real_score - float(tim_score), 2)

        # Патчим claudia_final.json проекта
        _patch_final_dna(client_id, entry["project_id"], real_score)

        processed += 1
        changed    = True

    if changed:
        pending_file.write_text(
            json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return processed


# ═══════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ МЕТРИК
# ═══════════════════════════════════════════════════════════════

def _fetch_metrics(entry: dict, cfg: dict) -> dict:
    platform   = entry["platform"]
    post_id    = entry["post_id"]
    channel_id = entry.get("channel_id", "")

    if platform == "telegram":
        token = cfg["platforms"]["telegram"].get("bot_token", "")
        chan  = channel_id or cfg["platforms"]["telegram"].get("channel_id", "")
        return _fetch_telegram(post_id, chan, token)
    elif platform == "vk":
        token    = cfg["platforms"]["vk"].get("token", "")
        owner_id = channel_id or cfg["platforms"]["vk"].get("owner_id", "")
        return _fetch_vk(post_id, owner_id, token)
    return {}


def _fetch_telegram(post_id: str, channel_id: str, token: str) -> dict:
    if not token or not channel_id:
        return {}
    try:
        import requests
        base = f"https://api.telegram.org/bot{token}"
        r    = requests.get(f"{base}/getMessages", params={
            "chat_id":     channel_id,
            "message_ids": json.dumps([int(post_id)]),
        }, timeout=15).json()

        if r.get("ok") and r.get("result"):
            m = r["result"][0]
            return {
                "views":     m.get("views", 0),
                "forwards":  m.get("forwards", 0),
                "reactions": sum(
                    x.get("count", 0)
                    for x in m.get("reactions", {}).get("reactions", [])
                ),
            }
    except Exception as e:
        print(f"[DAEMON] Telegram fetch error: {e}")
    return {}


def _fetch_vk(post_id: str, owner_id: str, token: str) -> dict:
    if not token or not owner_id:
        return {}
    try:
        import requests
        r = requests.get("https://api.vk.com/method/wall.getById", params={
            "posts":        f"{owner_id}_{post_id}",
            "access_token": token,
            "v":            "5.199",
        }, timeout=15).json()

        if "response" in r and r["response"]:
            p = r["response"][0]
            return {
                "views":    p.get("views",    {}).get("count", 0),
                "likes":    p.get("likes",    {}).get("count", 0),
                "reposts":  p.get("reposts",  {}).get("count", 0),
                "comments": p.get("comments", {}).get("count", 0),
            }
    except Exception as e:
        print(f"[DAEMON] VK fetch error: {e}")
    return {}


# ═══════════════════════════════════════════════════════════════
# ПОДСЧЁТ VIRAL_SCORE
# ═══════════════════════════════════════════════════════════════

_DEFAULT_WEIGHTS = {
    "telegram": {
        "views_per_point": 500,   "views_max_points": 4.0,
        "forwards_per_point": 5,  "forwards_max_points": 3.0,
        "reactions_per_point": 20,"reactions_max_points": 3.0,
    },
    "vk": {
        "views_per_point": 1000,  "views_max_points": 3.0,
        "likes_per_point": 20,    "likes_max_points": 3.0,
        "reposts_per_point": 5,   "reposts_max_points": 2.5,
        "comments_per_point": 10, "comments_max_points": 1.5,
    },
}


def _calc_score(metrics: dict, platform: str, weights: dict) -> float:
    cfg   = weights.get(platform) or _DEFAULT_WEIGHTS.get(platform, {})
    score = 0.0

    def _add(metric_key: str, per_key: str, max_key: str):
        nonlocal score
        val = metrics.get(metric_key, 0)
        per = max(cfg.get(per_key, 1), 1)
        mx  = float(cfg.get(max_key, 3.0))
        score += min(mx, val / per)

    if platform == "telegram":
        _add("views",     "views_per_point",     "views_max_points")
        _add("forwards",  "forwards_per_point",  "forwards_max_points")
        _add("reactions", "reactions_per_point", "reactions_max_points")
    elif platform == "vk":
        _add("views",    "views_per_point",    "views_max_points")
        _add("likes",    "likes_per_point",    "likes_max_points")
        _add("reposts",  "reposts_per_point",  "reposts_max_points")
        _add("comments", "comments_per_point", "comments_max_points")

    return round(min(10.0, score), 2)


# ═══════════════════════════════════════════════════════════════
# MINISTRY — ЕДИНСТВЕННОЕ МЕСТО ВЫЗОВА В СТУДИИ
# ═══════════════════════════════════════════════════════════════

def _report_to_ministry(client_id: str, platform: str,
                         real_score: float, project_id: str) -> None:
    """
    Вызывает ministry.record_outcome с РЕАЛЬНЫМИ данными.
    Это единственное место в студии где вызывается ministry.record_outcome
    для social_mix. Клавдия (A12) этого НЕ делает.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parents[2]))
        from studio.economy import ministry
        ministry.record_outcome("A06",      f"{platform}_fal", real_score, cost_usd=0.0)
        ministry.record_outcome("pipeline", "social_mix",      real_score, cost_usd=0.0)
        print(f"[DAEMON] 🏛 Ministry обновлён: {project_id} → score={real_score}")
    except Exception as e:
        print(f"[DAEMON] ⚠️ ministry.record_outcome: {e}")


# ═══════════════════════════════════════════════════════════════
# ПАТЧ FINAL_DNA
# ═══════════════════════════════════════════════════════════════

def _patch_final_dna(client_id: str, project_id: str, real_score: float) -> None:
    """Дописывает real_viral_score в claudia_final.json проекта."""
    search = [
        CLIENTS_DIR / client_id / "jobs",
        Path("runs"),
        Path("output"),
    ]
    for base in search:
        for match in base.glob(f"*{project_id}*"):
            if not match.is_dir():
                continue
            p = match / "claudia_final.json"
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    data.setdefault("final_dna", {})["real_viral_score"] = real_score
                    data.setdefault("final_dna", {})["status"]           = "scored"
                    data.setdefault("claudia_final", {})["status"]       = "scored"
                    p.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except Exception as e:
                    print(f"[DAEMON] ⚠️ patch_final_dna: {e}")
                return


# ═══════════════════════════════════════════════════════════════
# КОНФИГ КЛИЕНТА
# ═══════════════════════════════════════════════════════════════

def _load_social_config(client_id: str) -> dict | None:
    p = CLIENTS_DIR / client_id / "social_config.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metrics Daemon — сборщик реальных метрик")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"интервал между проходами в секундах (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--once",     action="store_true",
                        help="один проход и выход")
    args = parser.parse_args()

    if args.once:
        n = check_all_clients()
        print(f"[DAEMON] Готово. Обработано: {n}")
    else:
        run_forever(args.interval)
