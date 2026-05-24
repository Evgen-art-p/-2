"""
Cultural Field Tracker — Stage 8: Culture Formation (v2)
Источник правды — Демон (реакция зрителя), не internal QA.
Культура теперь попадает в промпты агентов через format_field_for_prompt().
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class CulturalFieldTracker:
    """
    Строит культурное поле цеха из данных выживания у зрителя (Демон).
    Strategy Registry и QA — вспомогательные источники.
    Основной источник правды: conflict_memory.daemon_wins.
    """

    def __init__(self, studio_root: Optional[Path] = None):
        if studio_root is None:
            studio_root = Path(__file__).resolve().parent.parent
        self.root            = studio_root
        self.culture_dir     = self.root / "culture" / "data"
        self.slot_fields_dir = self.culture_dir / "slot_fields"
        self.slot_fields_dir.mkdir(parents=True, exist_ok=True)

        self.strategy_registry_path = self.root / "strategy_registry.json"
        self.conflict_stats_path    = self.root / "economy" / "data" / "conflict_stats.json"
        self.global_field_path      = self.culture_dir / "global_field.json"

        self._resolve_paths()
        self._slot_fields:  Dict[str, dict] = {}
        self._global_field: Optional[dict]  = None

    def _resolve_paths(self):
        if not self.strategy_registry_path.exists():
            alt = self.root / ".." / "strategy_registry.json"
            if alt.exists():
                self.strategy_registry_path = alt.resolve()
        if not self.conflict_stats_path.exists():
            alt = self.root / "economy" / "data" / "conflict_stats.json"
            if alt.exists():
                self.conflict_stats_path = alt.resolve()

    # ═══════════════════════════════════════════════════════════
    # ЗАГРУЗКА ИСТОЧНИКОВ
    # ═══════════════════════════════════════════════════════════

    def _load_strategy_registry(self) -> dict:
        if not self.strategy_registry_path.exists():
            return {"slots": {}}
        with open(self.strategy_registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_conflict_stats(self) -> dict:
        if not self.conflict_stats_path.exists():
            return {}
        with open(self.conflict_stats_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_daemon_culture(self, slot_id: str) -> List[dict]:
        """
        Загружает победы зрителя по слоту из conflict_memory.
        Это главный источник правды о культуре цеха.

        Возвращает список:
        [{"agent_id": "A03", "phase_id": "ph", "count": 5, "avg_viral_score": 0.72, "mutations": 1}, ...]
        """
        try:
            from studio.economy.conflict_memory import get_slot_daemon_culture
            return get_slot_daemon_culture(slot_id)
        except Exception:
            pass

        # Fallback: читаем напрямую из conflict_stats.json
        stats = self._load_conflict_stats()
        daemon_wins = stats.get("daemon_wins", {})
        result = []
        for key, entry in daemon_wins.items():
            parts = key.split("::")
            if len(parts) < 3 or parts[0] != slot_id:
                continue
            result.append({
                "agent_id":        parts[2],
                "phase_id":        parts[1],
                "count":           entry.get("count", 0),
                "avg_viral_score": entry.get("avg_viral_score", 0.0),
                "mutations":       entry.get("mutations", 0),
            })
        result.sort(key=lambda x: x["avg_viral_score"], reverse=True)
        return result

    def _load_ministry_ratings(self) -> dict:
        ministry_path = self.root / "economy" / "data" / "ministry.json"
        if not ministry_path.exists():
            return {}
        with open(ministry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_slot_field(self, slot_id: str) -> dict:
        if slot_id in self._slot_fields:
            return self._slot_fields[slot_id]
        field_path = self.slot_fields_dir / f"{slot_id}.json"
        if field_path.exists():
            with open(field_path, "r", encoding="utf-8") as f:
                field = json.load(f)
        else:
            field = {
                "slot_id":    slot_id,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "patterns":   [],
                "meta": {
                    "total_runs_observed":   0,
                    "distinct_patterns_seen": 0,
                    "stable_norms_count":    0,
                    "daemon_approved_count": 0,
                }
            }
        self._slot_fields[slot_id] = field
        return field

    def _load_global_field(self) -> dict:
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
                    "cross_slot_survivors":          0,
                    "last_updated":                  None,
                }
            }
        return self._global_field

    # ═══════════════════════════════════════════════════════════
    # АНАЛИЗ ПАТТЕРНОВ — главное изменение v2
    # ═══════════════════════════════════════════════════════════

    def _detect_behavioral_patterns(self, slot_id: str) -> List[dict]:
        """
        Собирает паттерны из трёх источников в порядке приоритета:
        1. daemon_wins      — победы у реального зрителя (главный источник)
        2. strategy_registry — внутренние стратегии агентов (дополнение)
        3. conflict_stats   — released/wins из старой логики (fallback)
        """
        aggregated = defaultdict(lambda: {
            "pattern":            "",
            "occurrences":        0,
            "agents":             set(),
            "slots":              set(),
            "total_viral_score":  0.0,
            "daemon_approvals":   0,
            "mutation_wins":      0,
            "total_success_rate": 0.0,
            "first_seen":         None,
            "last_seen":          None,
        })

        # ── 1. Daemon wins — реальная культура ──
        daemon_culture = self._load_daemon_culture(slot_id)
        for entry in daemon_culture:
            key = f"daemon_survivor_{entry['agent_id']}_{entry['phase_id']}"
            agg = aggregated[key]
            agg["pattern"]           = key
            agg["occurrences"]      += entry["count"]
            agg["agents"].add(entry["agent_id"])
            agg["slots"].add(slot_id)
            agg["total_viral_score"] += entry["avg_viral_score"] * entry["count"]
            agg["daemon_approvals"]  += entry["count"]
            agg["mutation_wins"]     += entry.get("mutations", 0)

        # ── 2. Strategy Registry — внутренний опыт ──
        strategies = self._load_strategy_registry()
        for sid, slot_data in strategies.get("slots", {}).items():
            if slot_id and sid != slot_id:
                continue
            for agent_id, agent_strategies in slot_data.items():
                for strat in (agent_strategies or []):
                    if not isinstance(strat, dict):
                        continue
                    key = strat.get("pattern_description", strat.get("strategy", "unknown"))
                    agg = aggregated[key]
                    agg["pattern"]            = key
                    agg["occurrences"]       += 1
                    agg["agents"].add(agent_id)
                    agg["slots"].add(sid)
                    agg["total_success_rate"] += strat.get("success_rate", 0.5)
                    ts = strat.get("last_seen", strat.get("timestamp", ""))
                    if ts:
                        if not agg["first_seen"] or ts < agg["first_seen"]:
                            agg["first_seen"] = ts
                        if not agg["last_seen"] or ts > agg["last_seen"]:
                            agg["last_seen"] = ts

        # ── 3. Вычисление метрик ──
        result = []
        for key, agg in aggregated.items():
            n            = max(agg["occurrences"], 1)
            n_agents     = len(agg["agents"])
            adoption_rate = n_agents / max(n_agents + 3, 1)

            # Survival: если есть daemon_approvals — они определяют выживание
            survival_duration = agg["daemon_approvals"] if agg["daemon_approvals"] > 0 else n

            # Viral score: среднее по approvals или fallback на success_rate
            if agg["daemon_approvals"] > 0:
                avg_viral = agg["total_viral_score"] / agg["daemon_approvals"]
                failure_resistance = min(1.0, avg_viral / 10.0)
            else:
                avg_viral = 0.0
                failure_resistance = agg["total_success_rate"] / n if n > 0 else 0.5

            cross_slot_success = len(agg["slots"]) / max(len(agg["slots"]) + 1, 1)

            result.append({
                "pattern":            key,
                "cross_slot_success": round(cross_slot_success, 3),
                "survival_duration":  survival_duration,
                "adoption_rate":      round(adoption_rate, 3),
                "failure_resistance": round(failure_resistance, 3),
                "avg_viral_score":    round(avg_viral, 3),
                "daemon_approvals":   agg["daemon_approvals"],
                "mutation_wins":      agg["mutation_wins"],
                "source_agents":      sorted(list(agg["agents"])),
                "observed_slots":     sorted(list(agg["slots"])),
                "first_seen":         agg["first_seen"] or datetime.now(timezone.utc).isoformat(),
                "occurrences":        agg["occurrences"],
            })

        # Сортировка: daemon_approvals → adoption_rate
        result.sort(
            key=lambda x: (x["daemon_approvals"], x["adoption_rate"] + x["failure_resistance"]),
            reverse=True,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # СТАТУС ПАТТЕРНА — v2: stable требует одобрения Демона
    # ═══════════════════════════════════════════════════════════

    def _determine_status(self, pattern: dict, existing_pattern: Optional[dict] = None) -> str:
        """
        candidate: нет одобрений Демона или < 3 ранов
        stable:    Демон одобрил 3+ раз, avg_viral_score > 0
        declining: был stable, метрики упали
        global:    выжил в 3+ слотах
        """
        daemon_approvals = pattern.get("daemon_approvals", 0)
        avg_viral        = pattern.get("avg_viral_score", 0.0)
        duration         = pattern.get("survival_duration", 0)
        adoption         = pattern.get("adoption_rate", 0)
        cross            = pattern.get("cross_slot_success", 0)

        # Declining: был stable/global, метрики упали
        if existing_pattern and existing_pattern.get("status") in ("stable", "global"):
            old_viral    = existing_pattern.get("avg_viral_score", 0)
            old_adoption = existing_pattern.get("adoption_rate", 0)
            if (old_viral - avg_viral > 0.15) or (old_adoption - adoption > 0.15):
                return "declining"

        # Global: выжил в 3+ слотах от Демона
        if cross > 0.6 and daemon_approvals >= 5:
            return "global"

        # Stable: Демон одобрил 3+ раз
        if daemon_approvals >= 3 and avg_viral > 0:
            return "stable"

        # Stable по старой логике (если нет данных Демона)
        if daemon_approvals == 0 and duration >= 10 and adoption >= 0.3:
            return "stable"

        return "candidate"

    # ═══════════════════════════════════════════════════════════
    # ОБНОВЛЕНИЕ ПОЛЕЙ
    # ═══════════════════════════════════════════════════════════

    def update_slot_field(self, slot_id: str) -> dict:
        """Обновляет культурное поле для одного слота."""
        field        = self._load_slot_field(slot_id)
        old_patterns = {p["pattern"]: p for p in field.get("patterns", [])}
        detected     = self._detect_behavioral_patterns(slot_id)

        field["meta"]["total_runs_observed"]    += 1
        field["meta"]["distinct_patterns_seen"]  = len(detected)

        updated_patterns = []
        for pat in detected:
            existing   = old_patterns.get(pat["pattern"])
            pat["status"] = self._determine_status(pat, existing)
            updated_patterns.append(pat)

        stable_count  = sum(1 for p in updated_patterns if p["status"] == "stable")
        global_count  = sum(1 for p in updated_patterns if p["status"] == "global")
        daemon_count  = sum(p.get("daemon_approvals", 0) for p in updated_patterns)

        field["patterns"]                            = updated_patterns
        field["meta"]["stable_norms_count"]          = stable_count
        field["meta"]["global_patterns_count"]       = global_count
        field["meta"]["daemon_approved_count"]       = daemon_count
        field["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._save_slot_field(slot_id, field)
        self._slot_fields[slot_id] = field
        return field

    def _save_slot_field(self, slot_id: str, field: dict):
        field_path = self.slot_fields_dir / f"{slot_id}.json"
        with open(field_path, "w", encoding="utf-8") as f:
            json.dump(field, f, ensure_ascii=False, indent=2)

    def update_all_slots(self) -> Dict[str, dict]:
        strategies = self._load_strategy_registry()
        slot_ids   = list(strategies.get("slots", {}).keys())

        conflict_stats = self._load_conflict_stats()
        for key in conflict_stats.get("daemon_wins", {}):
            sid = key.split("::")[0]
            if sid not in slot_ids:
                slot_ids.append(sid)

        results = {}
        for sid in slot_ids:
            results[sid] = self.update_slot_field(sid)
        self._update_global_field()
        return results

    # ═══════════════════════════════════════════════════════════
    # ФОРМАТ ДЛЯ ПРОМПТА — культура наконец доходит до агентов
    # ═══════════════════════════════════════════════════════════

    def format_field_for_prompt(self, slot_id: str) -> str:
        """
        Форматирует культурное поле цеха для инжекта в контекст агента.
        Не директива — фон. Агент чувствует что здесь работало у зрителя.

        Вызывается из build_agent_context() в pipeline.py.
        Показывает только stable и global паттерны — шум не нужен.
        """
        field    = self._load_slot_field(slot_id)
        patterns = field.get("patterns", [])

        stable  = [p for p in patterns if p["status"] in ("stable", "global")]
        if not stable:
            return ""

        lines = [f"=== КУЛЬТУРА ЦЕХА {slot_id} (опыт реального зрителя) ==="]
        lines.append("Эти подходы выжили у аудитории — не потому что так решил алгоритм,")
        lines.append("а потому что зритель их принял. Это не правила — это эхо реальности.")
        lines.append("")

        for p in stable[:5]:  # топ-5, не перегружаем
            viral  = p.get("avg_viral_score", 0)
            agents = ", ".join(p.get("source_agents", [])[:3])
            mut    = " [мутация выжила]" if p.get("mutation_wins", 0) > 0 else ""
            lines.append(
                f"  • {p['pattern']}{mut} "
                f"(одобрений Демона: {p.get('daemon_approvals', 0)}, "
                f"viral: {viral:.1f})"
            )
            if agents:
                lines.append(f"    носители: {agents}")

        lines.append("")
        lines.append("Используй это как ориентир — не как клетку.")
        lines.append("=== КОНЕЦ КУЛЬТУРЫ ЦЕХА ===")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # ГЛОБАЛЬНОЕ ПОЛЕ
    # ═══════════════════════════════════════════════════════════

    def _update_global_field(self):
        """Паттерны выжившие в 3+ слотах у Демона — цивилизационный слой."""
        seen_patterns = defaultdict(lambda: {
            "pattern":        "",
            "slots":          set(),
            "total_duration": 0,
            "total_adoption": 0.0,
            "total_viral":    0.0,
            "occurrences":    0,
        })

        for slot_file in self.slot_fields_dir.glob("*.json"):
            with open(slot_file, "r", encoding="utf-8") as f:
                field = json.load(f)
            slot_id = field.get("slot_id", slot_file.stem)
            for pat in field.get("patterns", []):
                key          = pat["pattern"]
                agg          = seen_patterns[key]
                agg["pattern"] = key
                agg["slots"].add(slot_id)
                agg["total_duration"] += pat.get("survival_duration", 0)
                agg["total_adoption"] += pat.get("adoption_rate", 0)
                agg["total_viral"]    += pat.get("avg_viral_score", 0)
                agg["occurrences"]    += pat.get("occurrences", 0)

        global_patterns = []
        for key, agg in seen_patterns.items():
            n_slots = len(agg["slots"])
            if n_slots >= 3 and agg["total_duration"] >= 20:
                global_patterns.append({
                    "pattern":               key,
                    "observed_in_slots":     sorted(list(agg["slots"])),
                    "total_survival_duration": agg["total_duration"],
                    "average_adoption":      round(agg["total_adoption"] / n_slots, 3),
                    "average_viral_score":   round(agg["total_viral"] / n_slots, 3),
                    "status":                "global",
                    "emerged_at":            datetime.now(timezone.utc).isoformat(),
                })

        global_patterns.sort(
            key=lambda x: (len(x["observed_in_slots"]), x["total_survival_duration"]),
            reverse=True,
        )

        self._global_field = {
            "patterns": global_patterns,
            "meta": {
                "total_civilizational_patterns": len(global_patterns),
                "cross_slot_survivors":          len(global_patterns),
                "last_updated":                  datetime.now(timezone.utc).isoformat(),
            }
        }
        self._save_global_field()

    def _save_global_field(self):
        with open(self.global_field_path, "w", encoding="utf-8") as f:
            json.dump(self._global_field, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════════════════════
    # ПУБЛИЧНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════════

    def get_slot_summary(self, slot_id: str) -> dict:
        field      = self._load_slot_field(slot_id)
        stable     = [p for p in field.get("patterns", []) if p["status"] == "stable"]
        candidates = [p for p in field.get("patterns", []) if p["status"] == "candidate"]
        declining  = [p for p in field.get("patterns", []) if p["status"] == "declining"]
        return {
            "slot_id":       slot_id,
            "last_updated":  field.get("last_updated"),
            "total_patterns": len(field.get("patterns", [])),
            "stable_norms":  len(stable),
            "candidates":    len(candidates),
            "declining":     len(declining),
            "top_patterns":  field.get("patterns", [])[:5],
            "field_trend":   "stable" if not declining else "shifting",
            "data_source":   "daemon" if field["meta"].get("daemon_approved_count", 0) > 0 else "internal_qa",
        }

    def get_global_summary(self) -> dict:
        global_field = self._load_global_field()
        return {
            "total_civilizational_patterns": len(global_field.get("patterns", [])),
            "patterns":    global_field.get("patterns", []),
            "last_updated": global_field.get("meta", {}).get("last_updated"),
        }

    def get_all_slots_summary(self) -> List[dict]:
        summaries = []
        for slot_file in self.slot_fields_dir.glob("*.json"):
            summaries.append(self.get_slot_summary(slot_file.stem))
        return summaries
