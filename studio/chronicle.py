# studio/chronicle.py — v1.0
# ════════════════════════════════════════════════════════════════════
# ЛЕТОПИСЬ ГРОНДХЕЙМА — Слой 1 (факты)
# ════════════════════════════════════════════════════════════════════
#
# Принцип:
#   Летопись не сочиняет. Она складывает факты жизни города —
#   честно, в момент когда они произошли, без единого LLM-вызова.
#   Нарратив (рассказ Локи) рождается ПОТОМ, поверх этих фактов.
#   Кто складывает — цех, биржа, ночь, прогулка — летописи всё равно.
#
# Это фундамент. Он не знает кто будет издателем и под чьей крышей.
# Он знает одно: есть поток событий, его надо честно сохранить.
#
# Три рубрики:
#   studio    — работа студии: выпуски, QA-оценки, провалы
#   exchange  — биржа: сделки, вердикты, profit/loss
#   city      — жизнь города: союзы, ссоры, бунты, рождения, праздники
#
# Структура записи (одна строка chronicle_log.jsonl):
#   {
#     "ts":          "2026-06-13T14:30:00",
#     "id":          "chr_a1b2c3d4",
#     "rubric":      "studio",
#     "headline":    "Турбо-цех выпустил клип «...»",
#     "actors":      ["A01", "A05"],
#     "significance": 0.82,
#     "source":      "turbo/hooks",
#     "payload":     { ... сырые цифры, как есть ... }
#   }
#
# significance — по КРАЙНОСТИ: и рекорд, и провал весомы, середина — фон.
# Это фильтр, по которому Лока вечером отберёт главное за день.
#
# Студия «Шесть Пальцев» · 2026

import json
import uuid
import threading
from datetime import datetime, timedelta
from pathlib import Path

CHRONICLE_FILE = Path("studio/chronicle_log.jsonl")
_write_lock = threading.Lock()

# Допустимые рубрики. Чужая рубрика → "city" (не теряем факт, но помечаем).
RUBRICS = {"studio", "exchange", "city"}


# ════════════════════════════════════════════════════════════════════
# ЗНАЧИМОСТЬ ПО КРАЙНОСТИ
# ════════════════════════════════════════════════════════════════════
# Драма живёт на пиках, не на средних. Рекорд и провал — события.
# Ровный рабочий результат — фон (Лока упомянет одной фразой или опустит).

def significance_by_extremity(value: float, lo: float, hi: float) -> float:
    """
    Значимость 0..1 по тому, насколько value прижат к одному из краёв [lo, hi].
    Середина диапазона → ~0.0 (фон). Любой край → ~1.0 (событие).

    Пример (score цеха, шкала 0..6):
      significance_by_extremity(6.0, 0, 6) → 1.0   (рекорд)
      significance_by_extremity(0.5, 0, 6) → ~0.83 (провал)
      significance_by_extremity(3.0, 0, 6) → 0.0   (фон)
    """
    if hi <= lo:
        return 0.5
    # Нормируем в 0..1, затем меряем удаление от середины (0.5)
    norm = (float(value) - lo) / (hi - lo)
    norm = max(0.0, min(1.0, norm))
    return round(abs(norm - 0.5) * 2.0, 3)


# ════════════════════════════════════════════════════════════════════
# ЗАПИСЬ ФАКТА
# ════════════════════════════════════════════════════════════════════

def record_chronicle_event(
    rubric: str,
    headline: str,
    actors: list | None = None,
    significance: float = 0.5,
    source: str = "",
    **payload,
) -> str:
    """
    Записывает один факт в летопись. Возвращает id записи (или "" при сбое).

    rubric:       "studio" | "exchange" | "city"
    headline:     короткая фактическая строка ("Турбо выпустил клип «X» — 5.8/6.0")
                  БЕЗ оценок и мнений — только что случилось.
    actors:       кто причастен (["A01", "A05"] или ["Лока", "Финч"])
    significance: 0..1, считай через significance_by_extremity() где есть число
    source:       откуда прилетел факт ("turbo/hooks", "trading", "night_cycle")
    **payload:    сырые данные как есть (score, project_id, profit, и т.п.)

    Никогда не роняет вызывающий код — летопись падает молча, ран продолжается.
    """
    if not headline or not str(headline).strip():
        return ""

    if rubric not in RUBRICS:
        # Не теряем факт, но помечаем чужую рубрику в payload
        payload = {**payload, "_orig_rubric": rubric}
        rubric = "city"

    event_id = f"chr_{uuid.uuid4().hex[:8]}"

    record = {
        "ts":           datetime.now().isoformat(timespec="seconds"),
        "id":           event_id,
        "rubric":       rubric,
        "headline":     str(headline).strip()[:300],
        "actors":       [str(a) for a in (actors or [])][:12],
        "significance": round(max(0.0, min(1.0, float(significance))), 3),
        "source":       str(source)[:60],
        "payload":      payload,
    }

    _write(record)
    return event_id


def _write(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    try:
        CHRONICLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with open(CHRONICLE_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        # Летопись никогда не валит цех. Просто шепчет в лог.
        print(f"[CHRONICLE] ⚠ не записалось ({record.get('rubric')}): {e}")


# ════════════════════════════════════════════════════════════════════
# ЧТЕНИЕ (для Слоя 2 — рассказ Локи)
# ════════════════════════════════════════════════════════════════════

def read_chronicle(
    rubric: str | None = None,
    last_n_days: int = 0,
    on_date: str | None = None,
    min_significance: float = 0.0,
    limit: int = 0,
) -> list[dict]:
    """
    Читает chronicle_log.jsonl с фильтрами.

    rubric:           только одна рубрика, если задана
    last_n_days:      события за последние N дней
    on_date:          события одной даты "YYYY-MM-DD" (приоритетнее last_n_days)
    min_significance: отсечь фон ниже порога
    limit:            оставить последние N записей
    """
    if not CHRONICLE_FILE.exists():
        return []

    cutoff = None
    if last_n_days > 0 and not on_date:
        cutoff = (datetime.now() - timedelta(days=last_n_days)).isoformat()

    results = []
    try:
        with open(CHRONICLE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = rec.get("ts", "")
                if cutoff and ts < cutoff:
                    continue
                if on_date and not ts.startswith(on_date):
                    continue
                if rubric and rec.get("rubric") != rubric:
                    continue
                if rec.get("significance", 0.0) < min_significance:
                    continue
                results.append(rec)
    except Exception as e:
        print(f"[CHRONICLE] ⚠ read_chronicle: {e}")

    if limit > 0:
        results = results[-limit:]
    return results


def read_chronicle_day(date: str | None = None, min_significance: float = 0.0) -> dict:
    """
    Срез одного дня для Летописца (Локи).
    date: "YYYY-MM-DD"; по умолчанию — сегодня.

    Возвращает факты, сгруппированные по рубрикам и отсортированные
    по значимости (главное — сверху). Это то, что Лока прочитает вечером.

    {
      "date": "2026-06-13",
      "total": 12,
      "rubrics": {
        "studio":   [ {факт}, ... ],   # по убыванию significance
        "exchange": [ ... ],
        "city":     [ ... ],
      },
      "top": [ ... ],                   # 5 самых значимых за день, любая рубрика
    }
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    facts = read_chronicle(on_date=date, min_significance=min_significance)

    rubrics: dict[str, list] = {"studio": [], "exchange": [], "city": []}
    for f in facts:
        rubrics.setdefault(f.get("rubric", "city"), []).append(f)

    for r in rubrics:
        rubrics[r].sort(key=lambda x: x.get("significance", 0.0), reverse=True)

    top = sorted(facts, key=lambda x: x.get("significance", 0.0), reverse=True)[:5]

    return {
        "date":    date,
        "total":   len(facts),
        "rubrics": rubrics,
        "top":     top,
    }


def chronicle_stats() -> dict:
    """Быстрая сводка по летописи — для проверки что факты долетают."""
    if not CHRONICLE_FILE.exists():
        return {"total": 0, "by_rubric": {}, "file": str(CHRONICLE_FILE)}

    by_rubric: dict[str, int] = {}
    total = 0
    first_ts = ""
    last_ts = ""

    try:
        with open(CHRONICLE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                total += 1
                r = rec.get("rubric", "unknown")
                by_rubric[r] = by_rubric.get(r, 0) + 1
                ts = rec.get("ts", "")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts
    except Exception as e:
        return {"error": str(e)}

    return {
        "total":     total,
        "by_rubric": dict(sorted(by_rubric.items(), key=lambda x: -x[1])),
        "first_ts":  first_ts,
        "last_ts":   last_ts,
        "file":      str(CHRONICLE_FILE),
    }
