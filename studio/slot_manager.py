# studio/slot_manager.py — Управление слотами картриджей
# Студия «Шесть Пальцев» · 2026
#
# Слот = экземпляр картриджа в студии.
# Один модуль может быть вставлен в несколько слотов.
# Каждый слот имеет:
#   - slot_id (уникальный): "turbo_1", "turbo_2", "living_book_1"
#   - module (какой картридж): "turbo", "living_book"
#   - label (отображение): "⚡ TURBO #2"
# Промпты агентов — из оригинального модуля.
# Память (dna.json, sensory, resonance) — отдельная для каждого слота.

from __future__ import annotations

import json
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from studio.cartridge import CartridgeManifest, load_cartridge


SLOTS_FILE = Path("studio/slots.json")
INSTANCES_DIR = Path("studio/instances")
MODULES_DIR = Path("studio/modules")


@dataclass
class Slot:
    """Один слот — экземпляр картриджа в студии."""
    slot_id: str          # Уникальный: "turbo_1"
    module: str           # Модуль-источник: "turbo"
    label: str            # Отображение: "⚡ TURBO"
    enabled: bool = True  # Активен ли слот
    order: int = 0        # Порядок отображения

    def get_manifest(self) -> CartridgeManifest:
        """Загружает manifest картриджа."""
        return CartridgeManifest.load(self.module)

    def get_instance_dir(self) -> Path:
        """Папка экземпляра: studio/instances/{slot_id}/.
        Здесь живёт отдельная память (dna, sensory, resonance).
        """
        return INSTANCES_DIR / self.slot_id

    def get_agent_memory_dir(self, agent_id: str) -> Path:
        """Папка памяти конкретного агента в этом слоте."""
        return self.get_instance_dir() / agent_id


class SlotManager:
    """Управляет слотами картриджей.

    Загружает slots.json, позволяет:
    - Получить список активных слотов
    - Добавить/удалить слот
    - Клонировать слот (= добавить ещё один экземпляр того же модуля)
    - Подсчитать общее количество агентов в городе

    Память не теряется:
    - Промпты читаются из modules/{module}/  (оригинал)
    - dna.json клонируется в instances/{slot_id}/{agent_id}/
    - grondheim_memory адресует агентов как slot_id:agent_id
    """

    def __init__(self):
        self.slots: list[Slot] = []
        self._load()

    def _load(self):
        """Загружает slots.json."""
        if not SLOTS_FILE.exists():
            self._init_default_slots()
            return

        try:
            data = json.loads(SLOTS_FILE.read_text(encoding="utf-8"))
            self.slots = [
                Slot(
                    slot_id=s["slot_id"],
                    module=s["module"],
                    label=s.get("label", s["module"]),
                    enabled=s.get("enabled", True),
                    order=s.get("order", 0),
                )
                for s in data.get("slots", [])
            ]
        except Exception as e:
            print(f"[SLOTS] Ошибка загрузки slots.json: {e}")
            self._init_default_slots()

    def _init_default_slots(self):
        """Создаёт дефолтные слоты — по одному на каждый модуль."""
        if not MODULES_DIR.exists():
            self.slots = []
            return

        order = 0
        self.slots = []
        for d in sorted(MODULES_DIR.iterdir()):
            if not d.is_dir():
                continue
            info_path = d / "info.json"
            if not info_path.exists():
                continue

            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
            except Exception:
                info = {}

            module_id = d.name
            # Пропускаем residents — это не цех
            if module_id == "residents":
                continue

            self.slots.append(Slot(
                slot_id=module_id,
                module=module_id,
                label=info.get("label", module_id),
                enabled=True,
                order=info.get("priority", order * 10),
            ))
            order += 1

        self._save()

    def _save(self):
        """Сохраняет slots.json."""
        SLOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "description": "Конфигурация слотов картриджей студии",
            "slots": [asdict(s) for s in self.slots],
        }
        SLOTS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Публичный API ──────────────────────────────────────

    def get_active_slots(self) -> list[Slot]:
        """Возвращает активные слоты, отсортированные по order."""
        return sorted(
            [s for s in self.slots if s.enabled],
            key=lambda s: s.order,
        )

    def get_slot(self, slot_id: str) -> Optional[Slot]:
        """Найти слот по ID."""
        for s in self.slots:
            if s.slot_id == slot_id:
                return s
        return None

    def get_slots_by_module(self, module: str) -> list[Slot]:
        """Все слоты конкретного модуля."""
        return [s for s in self.slots if s.module == module]

    def add_slot(
        self,
        module: str,
        label: Optional[str] = None,
        slot_id: Optional[str] = None,
    ) -> Slot:
        """Добавить новый слот.

        Если slot_id не задан — генерируется автоматически:
        turbo → turbo_2, turbo_3, ...
        """
        if not slot_id:
            existing = self.get_slots_by_module(module)
            n = len(existing) + 1
            slot_id = f"{module}_{n}"

        # Проверяем уникальность
        if self.get_slot(slot_id):
            raise ValueError(f"Слот '{slot_id}' уже существует")

        if not label:
            manifest = CartridgeManifest.load(module)
            label = f"{manifest.label} #{len(self.get_slots_by_module(module)) + 1}"

        max_order = max((s.order for s in self.slots), default=0)

        slot = Slot(
            slot_id=slot_id,
            module=module,
            label=label,
            enabled=True,
            order=max_order + 10,
        )
        self.slots.append(slot)

        # Инициализируем память экземпляра
        self._init_instance(slot)

        self._save()
        print(f"[SLOTS] Добавлен слот: {slot_id} (модуль: {module})")
        return slot

    def clone_slot(self, source_slot_id: str, new_label: Optional[str] = None) -> Slot:
        """Клонировать существующий слот.

        Промпты берутся из того же модуля.
        Память (dna) копируется из источника.
        """
        source = self.get_slot(source_slot_id)
        if not source:
            raise ValueError(f"Слот '{source_slot_id}' не найден")

        new_slot = self.add_slot(
            module=source.module,
            label=new_label,
        )

        # Копируем память из источника (если есть)
        source_dir = source.get_instance_dir()
        if source_dir.exists():
            new_dir = new_slot.get_instance_dir()
            if new_dir.exists():
                shutil.rmtree(new_dir)
            shutil.copytree(source_dir, new_dir)
            print(f"[SLOTS] Память скопирована: {source_slot_id} → {new_slot.slot_id}")

        return new_slot

    def remove_slot(self, slot_id: str, delete_memory: bool = False):
        """Удалить слот.

        delete_memory=True — удаляет и папку instances/{slot_id}/
        delete_memory=False — память остаётся (можно восстановить)
        """
        self.slots = [s for s in self.slots if s.slot_id != slot_id]

        if delete_memory:
            instance_dir = INSTANCES_DIR / slot_id
            if instance_dir.exists():
                shutil.rmtree(instance_dir)
                print(f"[SLOTS] Память удалена: {slot_id}")

        self._save()
        print(f"[SLOTS] Слот удалён: {slot_id}")

    def toggle_slot(self, slot_id: str, enabled: bool):
        """Включить/выключить слот."""
        slot = self.get_slot(slot_id)
        if slot:
            slot.enabled = enabled
            self._save()

    def reorder(self, slot_ids: list[str]):
        """Переупорядочить слоты."""
        for i, sid in enumerate(slot_ids):
            slot = self.get_slot(sid)
            if slot:
                slot.order = i * 10
        self._save()

    # ── Инициализация памяти экземпляра ────────────────────

    def _init_instance(self, slot: Slot):
        """Инициализирует папку памяти для нового экземпляра.

        Копирует dna.json из оригинального модуля для каждого агента.
        Промпты НЕ копируются — они читаются из modules/{module}/ напрямую.
        """
        manifest = slot.get_manifest()
        instance_dir = slot.get_instance_dir()
        instance_dir.mkdir(parents=True, exist_ok=True)

        module_dir = MODULES_DIR / slot.module

        for agent_id in manifest.get_all_agents():
            agent_src = module_dir / agent_id
            agent_dst = instance_dir / agent_id
            agent_dst.mkdir(parents=True, exist_ok=True)

            # Копируем dna.json (если есть)
            dna_src = agent_src / "dna.json"
            if dna_src.exists():
                dna_dst = agent_dst / "dna.json"
                if not dna_dst.exists():  # не перезаписываем
                    shutil.copy2(dna_src, dna_dst)

            # Создаём структуру памяти
            for sub in ["sensory", "resonance", "core"]:
                (agent_dst / sub).mkdir(exist_ok=True)

        print(f"[SLOTS] Инициализирована память: {slot.slot_id} ({len(manifest.get_all_agents())} агентов)")

        # ── 4-й слой: лог взаимодействий для экономики ──
        self._ensure_economy_log(slot.slot_id)

    # ── Economy log ────────────────────────────────────────

    def _ensure_economy_log(self, slot_id: str):
        """Создаёт пустой interaction_log_{slot_id}.jsonl.
        Не перезаписывает если уже существует."""
        log_dir = Path("studio/economy/data")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"interaction_log_{slot_id}.jsonl"
        if not log_path.exists():
            log_path.touch()
            print(f"[SLOTS] Создан лог: {log_path}")

    # ── Статистика ─────────────────────────────────────────

    def count_agents(self) -> int:
        """Общее количество агентов во всех активных слотах."""
        total = 0
        for slot in self.get_active_slots():
            manifest = slot.get_manifest()
            total += len(manifest.get_all_agents())
        return total

    def count_residents(self) -> int:
        """Количество резидентов (из модуля residents)."""
        residents_dir = MODULES_DIR / "residents"
        if not residents_dir.exists():
            return 0
        return sum(
            1 for d in residents_dir.iterdir()
            if d.is_dir() and d.name.startswith("R")
        )

    def summary(self) -> dict:
        """Сводка по студии."""
        active = self.get_active_slots()
        return {
            "total_slots": len(active),
            "total_agents": self.count_agents(),
            "total_residents": self.count_residents(),
            "total_citizens": self.count_agents() + self.count_residents(),
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "module": s.module,
                    "label": s.label,
                    "agents": len(s.get_manifest().get_all_agents()),
                }
                for s in active
            ],
        }

    def print_summary(self):
        """Печатает сводку в консоль."""
        s = self.summary()
        print(f"\n╔═══ СТУДИЯ: {s['total_slots']} картриджей ═══╗")
        print(f"║ Агенты: {s['total_agents']}  Резиденты: {s['total_residents']}  Всего граждан: {s['total_citizens']}")
        for slot in s["slots"]:
            print(f"║  [{slot['slot_id']}] {slot['label']} — {slot['agents']} агентов")
        print(f"╚{'═' * 40}╝\n")
