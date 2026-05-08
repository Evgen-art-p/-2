# studio/economy/calculator.py
"""
Реэкспорт для обратной совместимости.
Все расчёты теперь в studio/billing_ledger.py
"""
from studio.billing_ledger import get_economy_data, get_agent_stats

__all__ = ["get_economy_data", "get_agent_stats"]