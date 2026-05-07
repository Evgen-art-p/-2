#!/usr/bin/env python3
"""
patch_universal_feedback.py
═══════════════════════════
Студия «Шесть Пальцев» — Патч: универсальный feedback для всех цехов.

Что делает:
  1. Правит studio/workshop/pipeline.py — убирает хардкод "A12",
     заменяет на qa_agent из state["_qa_agent"]
  2. Правит studio/cartridge.py — добавляет поле qa_agent в CartridgeManifest
     и пробрасывает его в state перед запуском пайплайна
  3. Добавляет "qa_agent" в manifest.json каждого цеха

Запуск из корня проекта:
  python patch_universal_feedback.py

Безопасно: перед каждым изменением создаёт .bak файл.
"""

import json
import shutil
from pathlib import Path

ROOT = Path(".")
STUDIO = ROOT / "studio"
PIPELINE = STUDIO / "workshop" / "pipeline.py"
CARTRIDGE = STUDIO / "cartridge.py"
MODULES = STUDIO / "modules"

# QA-агент для каждого цеха
QA_AGENTS = {
    "social_mix":   "A12",
    "video_long":   "A12",
    "video_shorts": "A12",
    "web_story":    "A12",
    "clipmakers":   "A12",
    "advertising":  "A12",
    "market_hit":   "A12",
    "logo_design":  "A04",
    "emo_card":     "A04",
    "turbo":        "A05",
    "living_book":  "A16",
}


def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak_feedback")
    shutil.copy2(path, bak)
    print(f"  📦 Бэкап: {bak.name}")


def patch_pipeline():
    """Заменяет хардкод A12 на универсальный qa_agent в pipeline.py"""
    print("\n── pipeline.py ──")

    if not PIPELINE.exists():
        print("  ❌ Файл не найден:", PIPELINE)
        return False

    text = PIPELINE.read_text(encoding="utf-8")

    # Проверяем — уже пропатчен?
    if "_qa_agent" in text and "_apply_qa_feedback" in text:
        print("  ✅ Уже пропатчен, пропускаем")
        return True

    backup(PIPELINE)

    # 1. Заменяем блок feedback (жёсткий A12) на универсальный
    OLD_FEEDBACK = '''    # Feedback loop: если это Артур — сохраняем оценки для следующего рана
    print(f"[DEBUG FEEDBACK] worker={worker_id}, client='{client_slug}'") 
    if worker_id == "A12" and client_slug != "_sandbox":
        try:
            save_feedback(client_slug, raw_result)
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка сохранения: {_fb_err}")

        # ══ NEW: Артур оценивает коллег → влияет на их DNA ══
        if _GRONDHEIM_ENABLED:
            _apply_arthur_feedback(state, raw_result)
        # ══ END NEW ══'''

    NEW_FEEDBACK = '''    # ══ UNIVERSAL FEEDBACK ══
    # qa_agent берётся из state["_qa_agent"] — туда CartridgeRunner кладёт
    # значение из manifest.json["qa_agent"]. Fallback: "A12".
    qa_agent = state.get("_qa_agent", "A12")
    if worker_id == qa_agent and client_slug != "_sandbox":
        try:
            save_feedback(client_slug, raw_result)
            print(f"[FEEDBACK] ✅ {worker_id} → feedback для {client_slug}")
        except Exception as _fb_err:
            print(f"[FEEDBACK] Ошибка: {_fb_err}")
        if _GRONDHEIM_ENABLED:
            _apply_qa_feedback(state, raw_result, qa_agent)
    # ══ END UNIVERSAL FEEDBACK ══'''

    if OLD_FEEDBACK not in text:
        print("  ⚠️  Блок feedback не найден точно — ищем по маркеру...")
        # Мягкий поиск
        if 'worker_id == "A12"' in text:
            # Заменяем только строку с A12
            text = text.replace(
                'if worker_id == "A12" and client_slug != "_sandbox":',
                'qa_agent = state.get("_qa_agent", "A12")\n    if worker_id == qa_agent and client_slug != "_sandbox":'
            )
            text = text.replace(
                'print(f"[DEBUG FEEDBACK] worker={worker_id}, client=\'{client_slug}\'")',
                ''
            )
            print("  ⚠️  Частичная замена (только строка с A12)")
        else:
            print("  ❌ Не удалось найти блок для замены")
            return False
    else:
        text = text.replace(OLD_FEEDBACK, NEW_FEEDBACK)

    # 2. Заменяем _apply_arthur_feedback на _apply_qa_feedback
    OLD_FUNC = '''# ══ NEW: Артур (A12) → оценки коллегам ══
def _apply_arthur_feedback(state: dict, raw_result: str):
    """
    Парсит ответ Артура и транслирует оценки в DNA коллег.
    Артур упоминает агентов — ищем позитивные/негативные маркеры.
    """
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()

    # Все рабочие агенты кроме Артура
    worker_ids = [k for k in state.get("results", {}).keys() if k != "A12"]'''

    NEW_FUNC = '''def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """
    Парсит ответ QA-агента и транслирует оценки в DNA коллег.
    Универсальная версия — работает для любого qa_agent цеха.
    """
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()

    # Все рабочие агенты кроме QA
    worker_ids = [k for k in state.get("results", {}).keys() if k != qa_agent]'''

    if OLD_FUNC in text:
        text = text.replace(OLD_FUNC, NEW_FUNC)
        # Заменяем on_agents_interact внутри функции — "A12" на qa_agent
        text = text.replace(
            'on_agents_interact("A12", wid,',
            'on_agents_interact(qa_agent, wid,'
        )
        # Убираем маркер ══ END NEW ══ после функции если есть
        text = text.replace('# ══ END NEW ══\n\n\nasync def summarize', '\nasync def summarize')
    else:
        # Мягкий вариант — просто добавляем новую функцию если старой нет
        if "_apply_qa_feedback" not in text:
            NEW_FUNC_FULL = '''
def _apply_qa_feedback(state: dict, raw_result: str, qa_agent: str):
    """Парсит ответ QA-агента и транслирует оценки в DNA коллег."""
    dept = state.get("active_dept", "")
    raw_lower = raw_result.lower()
    worker_ids = [k for k in state.get("results", {}).keys() if k != qa_agent]
    positive_markers = ["отлично", "хорошо", "качественно", "сильно", "точно", "великолепно", "браво"]
    negative_markers = ["ошибка", "правки", "слабо", "не соответствует", "переделать", "проблема", "критично"]
    for wid in worker_ids:
        if wid not in raw_result:
            continue
        idx = raw_result.find(wid)
        context_window = raw_lower[max(0, idx-200):idx+200]
        is_positive = any(m in context_window for m in positive_markers)
        is_negative = any(m in context_window for m in negative_markers)
        if is_positive and not is_negative:
            on_agents_interact(qa_agent, wid, "praise", 0.8, f"Оценка QA ({qa_agent})", dept)
        elif is_negative and not is_positive:
            on_agents_interact(qa_agent, wid, "critique", 0.7, f"Замечания QA ({qa_agent})", dept)
        elif is_positive and is_negative:
            on_agents_interact(qa_agent, wid, "critique", 0.3, f"Смешанная оценка QA ({qa_agent})", dept)

'''
            text = text + NEW_FUNC_FULL
            print("  ⚠️  Добавлена новая функция _apply_qa_feedback в конец файла")

    PIPELINE.write_text(text, encoding="utf-8")
    print("  ✅ pipeline.py пропатчен")
    return True


def patch_cartridge():
    """Добавляет поле qa_agent в CartridgeManifest и пробрасывает в state"""
    print("\n── cartridge.py ──")

    if not CARTRIDGE.exists():
        print("  ❌ Файл не найден:", CARTRIDGE)
        return False

    text = CARTRIDGE.read_text(encoding="utf-8")

    if "_qa_agent" in text:
        print("  ✅ Уже пропатчен, пропускаем")
        return True

    backup(CARTRIDGE)

    # 1. Добавляем поле qa_agent в dataclass CartridgeManifest
    OLD_FIELD = '    stop_after: Optional[int] = None\n    description: str = ""\n\n    # Run type'
    NEW_FIELD = '    stop_after: Optional[int] = None\n    description: str = ""\n    qa_agent: str = "A12"  # QA-агент цеха, чьи оценки идут в feedback\n\n    # Run type'

    if OLD_FIELD in text:
        text = text.replace(OLD_FIELD, NEW_FIELD)
    else:
        print("  ⚠️  Точное место для поля не найдено — ищем альтернативу...")
        # Мягкий поиск — вставляем после stop_after
        if "stop_after: Optional[int] = None" in text:
            text = text.replace(
                "stop_after: Optional[int] = None",
                "stop_after: Optional[int] = None\n    qa_agent: str = \"A12\"  # QA-агент цеха"
            )
        else:
            print("  ❌ Не удалось найти место для поля qa_agent")

    # 2. Добавляем qa_agent= в cls() внутри load()
    OLD_LOAD = '            stop_after=data.get("stop_after"),\n            description=data.get("description", ""),'
    NEW_LOAD = '            stop_after=data.get("stop_after"),\n            description=data.get("description", ""),\n            qa_agent=data.get("qa_agent", "A12"),'

    if OLD_LOAD in text:
        text = text.replace(OLD_LOAD, NEW_LOAD)
    else:
        print("  ⚠️  Точное место в load() не найдено")

    # 3. Пробрасываем qa_agent в state в CartridgeRunner.run()
    OLD_RUN = '        run_type = self.manifest.run_type or self.manifest.id\n        client_slug = self.state.get("current_client", "_sandbox")'
    NEW_RUN = '        run_type = self.manifest.run_type or self.manifest.id\n        # Сообщаем pipeline.py кто QA-агент этого цеха\n        self.state["_qa_agent"] = getattr(self.manifest, "qa_agent", "A12")\n        client_slug = self.state.get("current_client", "_sandbox")'

    if OLD_RUN in text:
        text = text.replace(OLD_RUN, NEW_RUN)
    else:
        print("  ⚠️  Точное место в run() не найдено — ищем альтернативу...")
        if 'client_slug = self.state.get("current_client", "_sandbox")' in text:
            text = text.replace(
                'client_slug = self.state.get("current_client", "_sandbox")',
                'self.state["_qa_agent"] = getattr(self.manifest, "qa_agent", "A12")\n        client_slug = self.state.get("current_client", "_sandbox")',
                1  # только первое вхождение (в run(), не в run_turbo())
            )

    CARTRIDGE.write_text(text, encoding="utf-8")
    print("  ✅ cartridge.py пропатчен")
    return True


def patch_manifests():
    """Добавляет qa_agent в manifest.json каждого цеха"""
    print("\n── manifests ──")

    patched = 0
    skipped = 0
    errors = 0

    for module_id, qa_agent in QA_AGENTS.items():
        manifest_path = MODULES / module_id / "manifest.json"

        if not manifest_path.exists():
            print(f"  ⚠️  {module_id}: manifest.json не найден")
            errors += 1
            continue

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))

            if data.get("qa_agent") == qa_agent:
                print(f"  ✅ {module_id}: уже есть qa_agent={qa_agent}")
                skipped += 1
                continue

            backup(manifest_path)
            data["qa_agent"] = qa_agent
            manifest_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"  ✅ {module_id}: qa_agent={qa_agent}")
            patched += 1

        except Exception as e:
            print(f"  ❌ {module_id}: {e}")
            errors += 1

    print(f"\n  Итого манифестов: {patched} пропатчено, {skipped} уже ок, {errors} ошибок")


def verify():
    """Проверяем результат патча"""
    print("\n── Проверка ──")
    ok = True

    # pipeline.py
    if PIPELINE.exists():
        text = PIPELINE.read_text(encoding="utf-8")
        if "_qa_agent" in text and "_apply_qa_feedback" in text:
            print("  ✅ pipeline.py: универсальный feedback")
        else:
            print("  ❌ pipeline.py: что-то не так")
            ok = False
    
    # cartridge.py
    if CARTRIDGE.exists():
        text = CARTRIDGE.read_text(encoding="utf-8")
        if "_qa_agent" in text and "qa_agent" in text:
            print("  ✅ cartridge.py: поле qa_agent добавлено")
        else:
            print("  ❌ cartridge.py: поле не найдено")
            ok = False

    # Манифесты
    missing = []
    for module_id in QA_AGENTS:
        mp = MODULES / module_id / "manifest.json"
        if mp.exists():
            data = json.loads(mp.read_text(encoding="utf-8"))
            if "qa_agent" not in data:
                missing.append(module_id)
    
    if missing:
        print(f"  ❌ Манифесты без qa_agent: {missing}")
        ok = False
    else:
        print(f"  ✅ Все {len(QA_AGENTS)} манифестов содержат qa_agent")

    return ok


def main():
    print("=" * 55)
    print("  Патч: универсальный feedback — Студия «Шесть Пальцев»")
    print("=" * 55)

    # Проверяем что мы в корне проекта
    if not STUDIO.exists():
        print(f"\n❌ Папка studio/ не найдена в {ROOT.absolute()}")
        print("   Запусти скрипт из корня проекта!")
        return

    p1 = patch_pipeline()
    p2 = patch_cartridge()
    patch_manifests()

    print("\n" + "=" * 55)
    if verify():
        print("  🎉 Патч применён успешно!")
        print("\n  Что изменилось:")
        print("  • feedback теперь работает во ВСЕХ 11 цехах")
        print("  • living_book → A16 (Марка Файн) собирает оценки")
        print("  • turbo → A05 собирает оценки")
        print("  • logo_design/emo_card → A04 собирает оценки")
        print("  • остальные → A12 как раньше")
        print("\n  Бэкапы сохранены как *.bak_feedback")
    else:
        print("  ⚠️  Патч применён частично — проверь файлы вручную")
    print("=" * 55)


if __name__ == "__main__":
    main()
