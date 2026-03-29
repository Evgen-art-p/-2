"""
patch_ui_revision_loop.py — Патч для studio/workshop/ui.py
═══════════════════════════════════════════════════════════
Применяет:
  Патч 7: Ревизионная петля A00a → A00 (после parse_agent_response)
  Патч 8: Rewind-перехват в начале цикла run_pipeline

Использование:
  python patch_ui_revision_loop.py
  
  Или с указанием файла:
  python patch_ui_revision_loop.py studio/workshop/ui.py

Бэкап создаётся автоматически: ui.py.bak_revision
═══════════════════════════════════════════════════════════
"""

import sys
import shutil
from pathlib import Path


def patch_file(filepath: str = None):
    # Определяем путь к файлу
    if filepath:
        ui_path = Path(filepath)
    else:
        # Пробуем типичные расположения
        candidates = [
            Path("studio/workshop/ui.py"),
            Path("workshop/ui.py"),
            Path("ui.py"),
        ]
        ui_path = None
        for c in candidates:
            if c.exists():
                ui_path = c
                break
        
        if not ui_path:
            print("❌ Не найден ui.py! Укажи путь: python patch_ui_revision_loop.py <path>")
            sys.exit(1)

    print(f"📁 Файл: {ui_path}")
    print(f"📏 Размер: {ui_path.stat().st_size:,} байт")

    # Читаем
    source = ui_path.read_text(encoding="utf-8")
    original_len = len(source)

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 8: Rewind-перехват в начале цикла for
    # ═══════════════════════════════════════════════════════
    # Ищем ТОЧНЫЙ блок в run_pipeline (не в turbo_pipeline!)
    
    PATCH8_FIND = '''        for i, (shop_name, worker_id) in enumerate(all_agents):
            if i < start_index:
                continue
            
            try:'''
    
    PATCH8_REPLACE = '''        for i, (shop_name, worker_id) in enumerate(all_agents):
            if i < start_index:
                continue

            # ══ REWIND: ревизионная петля вернула нас назад ══
            if state.get("_rewind_to"):
                target = state["_rewind_to"]
                if worker_id != target:
                    continue  # Пропускаем пока не дойдём до целевого агента
                # Дошли — очищаем маркер и продолжаем нормально
                state.pop("_rewind_to")
                print(f"[REWIND] ✅ Дошли до {target}, продолжаем пайплайн")

            try:'''

    # Проверяем что блок существует (и что это run_pipeline, а не turbo)
    # В файле есть два таких for-loop. Нам нужен ВТОРОЙ (в run_pipeline).
    # turbo_pipeline — первый (около строки ~1200), run_pipeline — второй (около строки ~1520)
    
    count = source.count(PATCH8_FIND)
    
    if count == 0:
        print("⚠️  Патч 8: блок for-loop не найден. Возможно уже применён или файл изменён.")
        patch8_ok = False
    elif count == 1:
        # Только один — заменяем его
        source = source.replace(PATCH8_FIND, PATCH8_REPLACE, 1)
        print("✅ Патч 8: Rewind-перехват — применён (единственный for-loop)")
        patch8_ok = True
    else:
        # Несколько — заменяем ПОСЛЕДНИЙ (run_pipeline идёт после turbo_pipeline)
        # Находим позицию последнего вхождения
        last_pos = source.rfind(PATCH8_FIND)
        source = source[:last_pos] + PATCH8_REPLACE + source[last_pos + len(PATCH8_FIND):]
        print(f"✅ Патч 8: Rewind-перехват — применён (последний из {count} for-loops)")
        patch8_ok = True

    # ═══════════════════════════════════════════════════════
    # ПАТЧ 7: Ревизионная петля A00a → A00
    # ═══════════════════════════════════════════════════════
    # Вставляем ПОСЛЕ:
    #   human_text, meta = parse_agent_response(raw_result)
    #   human_text = _clean_response(human_text)
    # И ПЕРЕД:
    #   # ── Этап 5: валидация asset_ids ──
    
    PATCH7_FIND = '''                # Парсим ответ
                human_text, meta = parse_agent_response(raw_result)
                human_text = _clean_response(human_text)
                
                # ── Этап 5: валидация asset_ids ──'''

    PATCH7_REPLACE = '''                # Парсим ответ
                human_text, meta = parse_agent_response(raw_result)
                human_text = _clean_response(human_text)

                # ══ REVISION LOOP: A00a (Вера Душа) → возврат на A00 ══
                if worker_id == "A00a" and state.get("run_type") == "living_book":
                    verdict = (meta.get("verdict") or meta.get("my_output", {}).get("verdict", "")).upper().strip()
                    revision_count = state.get("_revision_count", 0)
                    _max_rev = 3

                    if verdict == "REVISION" and revision_count < _max_rev:
                        state["_revision_count"] = revision_count + 1
                        _rev_notes = (
                            meta.get("revision_notes")
                            or meta.get("my_output", {}).get("revision_notes", "")
                            or human_text[:500]
                        )

                        ui.notify(
                            f"🔄 Вера Душа: РЕВИЗИЯ #{revision_count + 1}/{_max_rev}. Возврат к Фабуле.",
                            type="warning", timeout=8000
                        )
                        print(f"[REVISION] A00a → A00: loop {revision_count + 1}/{_max_rev}")
                        print(f"[REVISION] Замечания: {_rev_notes[:200]}")

                        # Сохраняем результат Веры
                        state["results"]["A00a"] = {
                            "text": human_text, "meta": meta, "raw": raw_result
                        }
                        if worker_id in avatars_ref['elements']:
                            avatars_ref['elements'][worker_id].classes(remove='working')
                            avatars_ref['elements'][worker_id].classes(add='done')

                        # Добавляем замечания в previous_output для Фабулы
                        previous_output += (
                            f"\\n\\n--- Вера Душа (A00a) — РЕВИЗИЯ #{revision_count + 1} ---\\n"
                            f"СТАТУС: REVISION\\n"
                            f"ЗАМЕЧАНИЯ:\\n{_rev_notes}\\n"
                            f"ИНСТРУКЦИЯ: Переработай сценарий с учётом замечаний выше.\\n"
                        )

                        # Ставим маркер rewind → цикл вернётся на A00
                        state["_rewind_to"] = "A00"
                        continue  # Следующая итерация for — перехватит rewind

                    elif verdict == "APPROVED" or revision_count >= _max_rev:
                        if revision_count >= _max_rev and verdict != "APPROVED":
                            ui.notify(
                                f"⚠️ Вера Душа: {_max_rev} ревизий исчерпано. Принудительно продолжаем.",
                                type="warning", timeout=5000
                            )
                            print(f"[REVISION] A00a: max loops reached, forcing APPROVED")
                        else:
                            ui.notify("✅ Вера Душа: ОДОБРЕНО!", type="positive")
                            print(f"[REVISION] A00a: APPROVED")
                        state["_revision_count"] = 0
                # ══ END REVISION LOOP ══

                # ── Этап 5: валидация asset_ids ──'''

    # Снова — ищем в run_pipeline (последнее вхождение)
    count7 = source.count(PATCH7_FIND)
    
    if count7 == 0:
        print("⚠️  Патч 7: блок 'Парсим ответ' не найден. Возможно уже применён.")
        patch7_ok = False
    elif count7 == 1:
        source = source.replace(PATCH7_FIND, PATCH7_REPLACE, 1)
        print("✅ Патч 7: Ревизионная петля A00a→A00 — применён")
        patch7_ok = True
    else:
        # Заменяем ПОСЛЕДНИЙ (run_pipeline)
        last_pos = source.rfind(PATCH7_FIND)
        source = source[:last_pos] + PATCH7_REPLACE + source[last_pos + len(PATCH7_FIND):]
        print(f"✅ Патч 7: Ревизионная петля — применён (последний из {count7})")
        patch7_ok = True

    # ═══════════════════════════════════════════════════════
    # СОХРАНЕНИЕ
    # ═══════════════════════════════════════════════════════
    
    if not patch7_ok and not patch8_ok:
        print("\n❌ Ни один патч не применён. Файл не изменён.")
        sys.exit(1)

    # Бэкап
    backup_path = ui_path.with_suffix(".py.bak_revision")
    if not backup_path.exists():
        shutil.copy2(ui_path, backup_path)
        print(f"\n💾 Бэкап: {backup_path}")
    else:
        print(f"\n💾 Бэкап уже существует: {backup_path}")

    # Записываем
    ui_path.write_text(source, encoding="utf-8")
    new_len = len(source)
    delta = new_len - original_len

    print(f"\n📝 Записано: {ui_path}")
    print(f"📏 Было: {original_len:,} → Стало: {new_len:,} (+{delta:,} символов)")
    print(f"\n{'='*50}")
    print(f"✅ ГОТОВО! Патчи 7+8 применены.")
    print(f"   Если что-то пошло не так — откатывай из {backup_path.name}")
    print(f"{'='*50}")


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    patch_file(path_arg)
