# studio/economy/ledger.py
"""
ПРОКСИ-АЛИАС — перенаправляет в studio/billing_ledger.py

История: было два параллельных леджера:
  - studio/billing_ledger.py (llm.py писал сюда)
  - studio/economy/ledger.py (pipeline.py писал сюда)

Теперь один источник правды: studio/billing_ledger.py
Этот файл — тонкая обёртка для обратной совместимости.
Все from studio.economy import ledger продолжают работать.
"""

# Реэкспортируем всё из главного леджера
from studio.billing_ledger import (  # noqa: F401
    record,
    read_all,
    total_spent,
    agent_spent,
    slot_spent,
    recent_by_agent,
    MODEL_PRICES,
    LEDGER_FILE,
)

__all__ = [
    "record",
    "read_all",
    "total_spent",
    "agent_spent",
    "slot_spent",
    "recent_by_agent",
    "MODEL_PRICES",
    "LEDGER_FILE",
]
