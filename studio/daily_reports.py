# studio/daily_reports.py
"""
Хранилище суточных отчётов: Утренний Чекаут + Ночной Цикл.
Формат: jsonl, один отчёт — одна строка.
Студия «Шесть Пальцев» · Спринт 23 · 2026
"""

import json
from pathlib import Path
from datetime import datetime

REPORTS_FILE = Path("studio/daily_reports.jsonl")
MAX_REPORTS  = 60  # последние 60 записей


def save_report(report_type: str, summary: dict, details: dict):
    """
    Сохраняет отчёт в jsonl.
    report_type: "morning" | "night"
    summary: {"GENIUS": 40, "NORMAL": 60, ...} или {"SLEEP": 90, "REVOLT": 14, ...}
    details: любой dict с подробностями
    """
    entry = {
        "ts":      datetime.now().isoformat(),
        "type":    report_type,
        "summary": summary,
        "details": details,
    }
    REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Читаем существующие
    lines = []
    if REPORTS_FILE.exists():
        try:
            lines = REPORTS_FILE.read_text(encoding="utf-8").splitlines()
        except Exception:
            pass

    lines.append(json.dumps(entry, ensure_ascii=False))

    # Оставляем последние MAX_REPORTS
    lines = lines[-MAX_REPORTS:]
    REPORTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_reports(limit: int = 20) -> list[dict]:
    """Загружает последние N отчётов (новые первыми)."""
    if not REPORTS_FILE.exists():
        return []
    try:
        lines = REPORTS_FILE.read_text(encoding="utf-8").splitlines()
        result = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except Exception:
                continue
            if len(result) >= limit:
                break
        return result
    except Exception:
        return []


def format_ts(ts: str) -> str:
    """Форматирует timestamp для отображения."""
    try:
        dt = datetime.fromisoformat(ts)
        today = datetime.now().date()
        delta = (today - dt.date()).days
        if delta == 0:
            return f"сегодня {dt.strftime('%H:%M')}"
        elif delta == 1:
            return f"вчера {dt.strftime('%H:%M')}"
        else:
            months = ["янв","фев","мар","апр","май","июн",
                      "июл","авг","сен","окт","ноя","дек"]
            return f"{dt.day} {months[dt.month-1]} {dt.strftime('%H:%M')}"
    except Exception:
        return ts[:16]
