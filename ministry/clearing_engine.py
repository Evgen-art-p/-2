"""
clearing_engine.py — Универсальный контроллер ресурсов Студии
Работает с любым картриджем через абстрактные пути.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import config

class StudioClearing:
    def __init__(self):
        # Базовые константы из общего конфига
        self.base_path = Path(config.STUDIO_MODULES_PATH)
        self.min_deposit = getattr(config, 'MEMORY_DEPOSIT_LIMIT', 100.0)
        self.fuel_rate = getattr(config, 'GND_TO_FUEL_RATE', 1.0)

    def _get_dna_path(self, workshop: str, agent_id: str) -> Path:
        """Универсальный путь к ДНК любого агента в любом цехе"""
        return self.base_path / workshop / agent_id / "dna.json"

    def _update_dna(self, workshop: str, agent_id: str, updates: Dict[str, Any]):
        """Атомарное обновление файла ДНК"""
        path = self._get_dna_path(workshop, agent_id)
        if not path.exists():
            print(f"[ERROR] DNA not found at {path}")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            dna = json.load(f)
        
        # Глубокое обновление (например, баланса или параметров)
        if "balance" in updates:
            dna.setdefault("balance", {})
            for key, val in updates["balance"].items():
                dna["balance"][key] = round(dna["balance"].get(key, 0.0) + val, 4)
            del updates["balance"]
            
        dna.update(updates)
        
        # Автоматическая рекалибровка на основе нового баланса
        balance = dna.get("balance", {}).get("Световики", 0.0)
        if balance < self.min_deposit:
            dna["temperature"] = 0.1
            dna["status"] = "LOW_ENERGY"
        else:
            dna["temperature"] = 0.4
            dna["status"] = "ACTIVE"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(dna, f, ensure_ascii=False, indent=2)

    def process_transaction(self, workshop: str, agent_id: str, tx_type: str, data: Dict[str, Any]):
        """
        Единая точка входа для всех типов экономических событий.
        tx_type: 'launch', 'success', 'failure'
        """
        if tx_type == "launch":
            # Налог на использование ресурсов
            self._update_dna(workshop, agent_id, {"balance": {"Световики": -10.0}})
            
        elif tx_type == "success":
            # Награда с учетом сложности и правок
            revs = data.get("revision_count", 0)
            reward = 100.0 / (revs + 1)
            self._update_dna(workshop, agent_id, {"balance": {"Световики": reward}})
            
        elif tx_type == "failure":
            # Штраф за критическую ошибку
            self._update_dna(workshop, agent_id, {"balance": {"Световики": -50.0}})

# Пример вызова из любого места системы:
# clearing = StudioClearing()
# clearing.process_transaction("any_workshop", "A_ID", "success", {"revision_count": 0})