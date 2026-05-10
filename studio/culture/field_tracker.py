"""
Cultural Field Tracker — Stage 8: Culture Formation
Наблюдает за выжившими стратегиями, считает метрики устойчивости.
Формирует локальные (slot) и глобальное поля.
НЕ влияет на промпты.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class CulturalFieldTracker:
    """
    Анализирует Strategy Registry, Conflict Memory, Ministry ratings —
    и строит распределение вероятностей выживших паттернов.
    """

    def __init__(self, studio_root: Optional[Path] = None):
        if studio_root is None:
            studio_root = Path(__file__).resolve().parent.parent  # studio/
        self.root = studio_root
        self.culture_dir = self.root / "culture" / "data"
        self.slot_fields_dir = self.culture_dir / "slot_fields"
        self.slot_fields_dir.mkdir(parents=True, exist_ok=True)

        # Input источники
        self.strategy_registry_path = self.root / "strategy_registry.json"
        self.conflict_stats_path = self.root / ".." / "studio" / "economy" / "data" / "conflict_stats.json"
        # поправка: conflict_stats лежит в economy/data/
        self._resolve_paths()
        
        # Output
        self.global_field_path = self.culture_dir / "global_field.json"

        # Кеш загруженных полей
        self._slot_fields: Dict[str, dict] = {}
        self._global_field: Optional[dict] = None

    def _resolve_paths(self):
        """Разрешает относительные пути к источникам данных"""
        # strategy_registry
        if not self.strategy_registry_path.exists():
            alt = self.root / ".." / "strategy_registry.json"
            if alt.exists():
                self.strategy_registry_path = alt.resolve()
        
        # conflict_stats — лежит в economy/data/
        if not self.conflict_stats_path.exists():
            alt = self.root / "economy" / "data" / "conflict_stats.json"
            if alt.exists():
                self.conflict_stats_path = alt.resolve()

    # ═══════════════════════════════════════════════════════════
    # ЗАГРУЗКА ИСТОЧНИКОВ
    # ═══════════════════════════════════════════════════════════

    def _load_strategy_registry(self) -> dict:
        """Загружает реестр стратегий"""
        if not self.strategy_registry_path.exists():
            return {"slots": {}}
        with open(self.strategy_registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_conflict_stats(self) -> dict:
        """Загружает статистику конфликтов"""
        if not self.conflict_stats_path.exists():
            return {}
        with open(self.conflict_stats_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_ministry_ratings(self) -> dict:
        """Загружает рейтинги Министерства"""
        ministry_path = self.root / "economy" / "data" / "ministry.json"
        if not ministry_path.exists():
            return {}
        with open(ministry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_slot_field(self, slot_id: str) -> dict:
        """Загружает существующее поле слота или создаёт новое"""
        if slot_id in self._slot_fields:
            return self._slot_fields[slot_id]
        
        field_path = self.slot_fields_dir / f"{slot_id}.json"
        if field_path.exists():
            with open(field_path, "r", encoding="utf-8") as f:
                field = json.load(f)
        else:
            field = {
                "slot_id": slot_id,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "patterns": [],
                "meta": {
                    "total_runs_observed": 0,
                    "distinct_patterns_seen": 0,
                    "stable_norms_count": 0
                }
            }
        self._slot_fields[slot_id] = field
        return field

    def _load_global_field(self) -> dict:
        """Загружает глобальное поле или создаёт новое"""
        if self._global_field is not None:
            return self._global_field
        
        if self.global_field_path.exists():
            with open(self.global_field_path, "r", encoding="utf-8") as f:
                self._global_field = json.load(f)
        else:
            self._global_field = {
                "patterns": [],
                "meta": {
                    "total_civilizational_patterns": 0,
                    "cross_slot_survivors": 0,
                    "last_updated": None
                }
            }
        return self._global_field

    # ═══════════════════════════════════════════════════════════
    # АНАЛИЗ ПАТТЕРНОВ
    # ═══════════════════════════════════════════════════════════

    def _extract_strategy_patterns(self, strategies: dict, slot_id: Optional[str] = None) -> List[dict]:
        """
        Извлекает паттерны из Strategy Registry.
        strategy = {"pattern_description": str, "success_rate": float, "agent_id": str, ...}
        """
        patterns = []
        slots = strategies.get("slots", {})
        
        for sid, slot_data in slots.items():
            if slot_id and sid != slot_id:
                continue
            
            for agent_id, agent_strategies in slot_data.items():
                for strat in agent_strategies:
                    if isinstance(strat, dict):
                        pattern = {
                            "pattern": strat.get("pattern_description", strat.get("strategy", "unknown")),
                            "agent_id": agent_id,
                            "slot_id": sid,
                            "success_rate": strat.get("success_rate", 0.5),
                            "timestamp": strat.get("last_seen", strat.get("timestamp", "")),
                        }
                        patterns.append(pattern)
        
        return patterns

    def _extract_conflict_winners(self, conflict_stats: dict, slot_id: Optional[str] = None) -> List[dict]:
        """
        Извлекает паттерны победителей конфликтов.
        """
        patterns = []
        
        for key, stats in conflict_stats.items():
            # ключ: "slot_id::phase_id::agent_id"
            parts = key.split("::")
            if len(parts) < 3:
                continue
            sid, phase_id, agent_id = parts[0], parts[1], parts[2]
            
            if slot_id and sid != slot_id:
                continue
            
            if isinstance(stats, dict):
                pattern = {
                    "pattern": f"conflict_winner_{phase_id}",
                    "agent_id": agent_id,
                    "slot_id": sid,
                    "wins": stats.get("wins", 0),
                    "total": stats.get("total", 1),
                    "win_rate": stats.get("win_rate", stats.get("wins", 0) / max(stats.get("total", 1), 1)),
                }
                patterns.append(pattern)
        
        return patterns

    def _detect_behavioral_patterns(self, slot_id: str) -> List[dict]:
        """
        Аггрегирует данные из всех источников и выделяет устойчивые паттерны.
        """
        strategies = self._load_strategy_registry()
        conflict_stats = self._load_conflict_stats()
        ministry_ratings = self._load_ministry_ratings()
        
        # 1. Паттерны из стратегий
        strat_patterns = self._extract_strategy_patterns(strategies, slot_id)
        
        # 2. Паттерны из конфликтов
        conflict_patterns = self._extract_conflict_winners(conflict_stats, slot_id)
        
        # 3. Аггрегация по описанию паттерна
        aggregated = defaultdict(lambda: {
            "pattern": "",
            "occurrences": 0,
            "agents": set(),
            "slots": set(),
            "total_success_rate": 0.0,
            "total_wins": 0,
            "total_conflicts": 0,
            "first_seen": None,
            "last_seen": None,
        })
        
        for p in strat_patterns:
            key = p["pattern"]
            agg = aggregated[key]
            agg["pattern"] = key
            agg["occurrences"] += 1
            agg["agents"].add(p["agent_id"])
            agg["slots"].add(p["slot_id"])
            agg["total_success_rate"] += p["success_rate"]
            
            ts = p.get("timestamp", "")
            if ts:
                if not agg["first_seen"] or ts < agg["first_seen"]:
                    agg["first_seen"] = ts
                if not agg["last_seen"] or ts > agg["last_seen"]:
                    agg["last_seen"] = ts
        
        for p in conflict_patterns:
            key = p["pattern"]
            agg = aggregated[key]
            agg["pattern"] = key
            agg["agents"].add(p["agent_id"])
            agg["slots"].add(p["slot_id"])
            agg["total_wins"] += p.get("wins", 0)
            agg["total_conflicts"] += p.get("total", 0)
            if not agg["occurrences"]:
                agg["occurrences"] = 1  # минимум
        
        # 4. Вычисление метрик
        result = []
        for key, agg in aggregated.items():
            n = max(agg["occurrences"], 1)
            
            # adoption_rate = сколько агентов используют / общее число агентов в слоте
            # оценка: используем количество уникальных агентов
            adoption_rate = len(agg["agents"]) / max(len(agg["agents"]) + 3, 1)  # +3 — smoothing
            
            # cross_slot_success = работает ли в других слотах
            cross_slot_success = len(agg["slots"]) / max(len(agg["slots"]) + 1, 1)  # >0.5 если 2+ слота
            
            # survival_duration = оценка по времени (пока proxy: occurrences)
            survival_duration = n
            
            # failure_resistance = доля конфликтов с победами
            if agg["total_conflicts"] > 0:
                failure_resistance = agg["total_wins"] / agg["total_conflicts"]
            else:
                failure_resistance = agg["total_success_rate"] / (n * 1.0) if n > 0 else 0.5
            
            # energy_efficiency — пока оценка: успешные паттерны считаем эффективными
            energy_efficiency = min(agg["total_success_rate"] / n, 1.0) if n > 0 else 0.5
            
            result.append({
                "pattern": key,
                "cross_slot_success": round(cross_slot_success, 3),
                "survival_duration": survival_duration,
                "adoption_rate": round(adoption_rate, 3),
                "failure_resistance": round(failure_resistance, 3),
                "energy_efficiency": round(energy_efficiency, 3),
                "source_agents": sorted(list(agg["agents"])),
                "observed_slots": sorted(list(agg["slots"])),
                "first_seen": agg["first_seen"] or datetime.now(timezone.utc).isoformat(),
                "occurrences": agg["occurrences"],
            })
        
        # Сортировка: сначала стабильные с высокой adoption
        result.sort(key=lambda x: (x["adoption_rate"] + x["failure_resistance"]), reverse=True)
        
        return result

    # ═══════════════════════════════════════════════════════════
    # ОПРЕДЕЛЕНИЕ СТАТУСА ПАТТЕРНА
    # ═══════════════════════════════════════════════════════════

    def _determine_status(self, pattern: dict, existing_pattern: Optional[dict] = None) -> str:
        """
        Определяет статус паттерна:
        - candidate: успешен < 10 ранов
        - stable: держится 10+ ранов, adoption > 0.3
        - declining: был stable, но метрики падают
        - global: выжил в 3+ слотах > 20 ранов (назначается отдельно)
        """
        duration = pattern.get("survival_duration", 0)
        adoption = pattern.get("adoption_rate", 0)
        cross = pattern.get("cross_slot_success", 0)
        
        # Проверка на declining
        if existing_pattern and existing_pattern.get("status") in ("stable", "global"):
            old_adoption = existing_pattern.get("adoption_rate", 0)
            old_resistance = existing_pattern.get("failure_resistance", 0)
            new_adoption = pattern.get("adoption_rate", 0)
            new_resistance = pattern.get("failure_resistance", 0)
            
            # Падение более чем на 15% — declining
            if (old_adoption - new_adoption > 0.15) or (old_resistance - new_resistance > 0.15):
                return "declining"
        
        # Глобальный паттерн
        if cross > 0.6 and duration >= 20:
            return "global"
        
        # Стабильный
        if duration >= 10 and adoption >= 0.3:
            return "stable"
        
        # Кандидат
        return "candidate"

    # ═══════════════════════════════════════════════════════════
    # ОБНОВЛЕНИЕ ПОЛЕЙ
    # ═══════════════════════════════════════════════════════════

    def update_slot_field(self, slot_id: str) -> dict:
        """
        Обновляет культурное поле для одного слота.
        Вызывается после каждого рана или пакетно.
        """
        field = self._load_slot_field(slot_id)
        old_patterns = {p["pattern"]: p for p in field.get("patterns", [])}
        
        # Детектируем текущие паттерны
        detected = self._detect_behavioral_patterns(slot_id)
        
        # Обновляем метаданные
        field["meta"]["total_runs_observed"] += 1
        field["meta"]["distinct_patterns_seen"] = len(detected)
        
        # Обновляем паттерны
        updated_patterns = []
        for pat in detected:
            existing = old_patterns.get(pat["pattern"])
            pat["status"] = self._determine_status(pat, existing)
            updated_patterns.append(pat)
        
        stable_count = sum(1 for p in updated_patterns if p["status"] == "stable")
        global_count = sum(1 for p in updated_patterns if p["status"] == "global")
        
        field["patterns"] = updated_patterns
        field["meta"]["stable_norms_count"] = stable_count
        field["meta"]["global_patterns_count"] = global_count
        field["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Сохраняем
        self._save_slot_field(slot_id, field)
        self._slot_fields[slot_id] = field
        
        return field

    def _save_slot_field(self, slot_id: str, field: dict):
        """Сохраняет поле слота на диск"""
        field_path = self.slot_fields_dir / f"{slot_id}.json"
        with open(field_path, "w", encoding="utf-8") as f:
            json.dump(field, f, ensure_ascii=False, indent=2)

    def update_all_slots(self) -> Dict[str, dict]:
        """
        Обновляет культурные поля для всех известных слотов.
        """
        strategies = self._load_strategy_registry()
        slot_ids = list(strategies.get("slots", {}).keys())
        
        # Также проверяем слоты из conflict_stats
        conflict_stats = self._load_conflict_stats()
        for key in conflict_stats:
            sid = key.split("::")[0]
            if sid not in slot_ids:
                slot_ids.append(sid)
        
        results = {}
        for sid in slot_ids:
            results[sid] = self.update_slot_field(sid)
        
        # Обновляем глобальное поле
        self._update_global_field()
        
        return results

    # ═══════════════════════════════════════════════════════════
    # ГЛОБАЛЬНОЕ ПОЛЕ (цивилизационный слой)
    # ═══════════════════════════════════════════════════════════

    def _update_global_field(self):
        """
        Формирует глобальное поле — паттерны, выжившие в 3+ слотах > 20 ранов.
        """
        global_patterns = []
        seen_patterns = defaultdict(lambda: {
            "pattern": "",
            "slots": set(),
            "total_duration": 0,
            "total_adoption": 0.0,
            "occurrences": 0,
        })
        
        # Собираем паттерны из всех слотов
        for slot_file in self.slot_fields_dir.glob("*.json"):
            with open(slot_file, "r", encoding="utf-8") as f:
                field = json.load(f)
            slot_id = field.get("slot_id", slot_file.stem)
            
            for pat in field.get("patterns", []):
                key = pat["pattern"]
                agg = seen_patterns[key]
                agg["pattern"] = key
                agg["slots"].add(slot_id)
                agg["total_duration"] += pat.get("survival_duration", 0)
                agg["total_adoption"] += pat.get("adoption_rate", 0)
                agg["occurrences"] += pat.get("occurrences", 0)
        
        # Фильтр: 3+ слота, суммарная длительность > 20
        for key, agg in seen_patterns.items():
            if len(agg["slots"]) >= 3 and agg["total_duration"] >= 20:
                n_slots = len(agg["slots"])
                global_patterns.append({
                    "pattern": key,
                    "observed_in_slots": sorted(list(agg["slots"])),
                    "total_survival_duration": agg["total_duration"],
                    "average_adoption": round(agg["total_adoption"] / n_slots, 3),
                    "status": "global",
                    "emerged_at": datetime.now(timezone.utc).isoformat(),
                })
        
        # Сортировка: больше слотов + длительность
        global_patterns.sort(key=lambda x: (len(x["observed_in_slots"]), x["total_survival_duration"]), reverse=True)
        
        self._global_field = {
            "patterns": global_patterns,
            "meta": {
                "total_civilizational_patterns": len(global_patterns),
                "cross_slot_survivors": len(global_patterns),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        }
        self._save_global_field()

    def _save_global_field(self):
        """Сохраняет глобальное поле"""
        with open(self.global_field_path, "w", encoding="utf-8") as f:
            json.dump(self._global_field, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════════════════════
    # ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ ОТЧЁТОВ
    # ═══════════════════════════════════════════════════════════

    def get_slot_summary(self, slot_id: str) -> dict:
        """Возвращает сводку по культурному полю слота"""
        field = self._load_slot_field(slot_id)
        
        stable = [p for p in field.get("patterns", []) if p["status"] == "stable"]
        candidates = [p for p in field.get("patterns", []) if p["status"] == "candidate"]
        declining = [p for p in field.get("patterns", []) if p["status"] == "declining"]
        
        return {
            "slot_id": slot_id,
            "last_updated": field.get("last_updated"),
            "total_patterns": len(field.get("patterns", [])),
            "stable_norms": len(stable),
            "candidates": len(candidates),
            "declining": len(declining),
            "top_patterns": field.get("patterns", [])[:5],
            "field_trend": "stable" if len(declining) == 0 else "shifting",
        }

    def get_global_summary(self) -> dict:
        """Возвращает сводку по глобальному цивилизационному слою"""
        global_field = self._load_global_field()
        return {
            "total_civilizational_patterns": len(global_field.get("patterns", [])),
            "patterns": global_field.get("patterns", []),
            "last_updated": global_field.get("meta", {}).get("last_updated"),
        }

    def get_all_slots_summary(self) -> List[dict]:
        """Сводка по всем слотам"""
        summaries = []
        for slot_file in self.slot_fields_dir.glob("*.json"):
            slot_id = slot_file.stem
            summaries.append(self.get_slot_summary(slot_id))
        return summaries