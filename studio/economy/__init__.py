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
from studio.economy import memory_embedding  # noqa: F401

__all__ = ["ledger", "cost_intuition", "ministry", "memory_embedding"]
