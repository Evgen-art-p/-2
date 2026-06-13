#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  ПАТЧ · ПАМЯТЬ АГЕНТА В ЧАТЕ КАБИНЕТА                       ║
║  «Агенты не помнят вчерашние разговоры» — починка чтения    ║
║  Студия «Шесть Пальцев» · Грондхейм                        ║
╚══════════════════════════════════════════════════════════════╝

ДИАГНОЗ:
  Разговоры с агентом ЗАПИСЫВАЮТСЯ исправно — record_sensory_event()
  пишет каждую реплику в sensory/sensory_memory.json (проверено: файл полон).

  Но при НОВОМ разговоре эта память НЕ подгружается обратно в контекст.
  В ui_cabinet.py, в сборке system_prompt:
      if talking:
          sys_content = state["system_prompt"]      # ← голый промпт, БЕЗ памяти
      else:
          ...
          memory_ctx = format_memory_context()      # ← у безличного промпта память ЕСТЬ

  Итог: агент вчера всё запомнил (запись жива), но сегодня ему этот
  «дневник» не открывают (чтение оборвано). Он отвечает «помню» из
  вежливости, хотя памяти в контексте нет.

ЛЕЧЕНИЕ:
  В ветку `if talking:` подмешать сенсорную память агента через готовую
  format_sensory_for_prompt() из grondheim_memory — ту самую, что берёт
  последние 10 записей и форматирует для промпта. Три строки, по образцу
  того как память уже подаётся безличному «промпту» в ветке else.

  Берём ИМЕННО сенсорную память (sensory_memory.json), потому что:
    - она точно полна (туда пишет record_sensory_event при каждом чате),
    - папка memory/ (last_chat.json, конспекты) у тебя ПУСТАЯ —
      финализация диалога не срабатывает, build_agent_context читал бы
      пустоту. Сенсорная память — единственная, где разговоры реально есть.

ПРИМЕНЕНИЕ:
  Положи скрипт в корень репозитория (где папка studio/) и запусти:
    python patch_agent_memory_recall.py
  Скрипт сам найдёт studio/cabinet/ui_cabinet.py, сделает резервную копию
  и применит правку. Идемпотентен — повторный запуск не навредит.
"""

import sys
from pathlib import Path

TARGET = Path("studio/cabinet/ui_cabinet.py")

# ── Что ищем (точная ветка из текущего файла) ────────────────────────
OLD = '''            if talking:
                sys_content = state["system_prompt"]
            else:'''

# ── На что меняем (добавляем подгрузку сенсорной памяти агента) ───────
NEW = '''            if talking:
                sys_content = state["system_prompt"]
                # ПАМЯТЬ АГЕНТА (патч): подмешиваем его сенсорную память —
                # последние разговоры из sensory_memory.json. Чтобы агент
                # помнил «вчера→сегодня», а не отвечал «помню» вслепую.
                try:
                    from studio.grondheim_memory import format_sensory_for_prompt
                    _agent_mem = format_sensory_for_prompt(
                        talking["id"], talking.get("dept", "")
                    )
                    if _agent_mem:
                        sys_content = (sys_content or "") + "\\n\\n" + _agent_mem
                except Exception as _mem_recall_err:
                    print(f"[CABINET] \u26a0 \u041f\u043e\u0434\u0433\u0440\u0443\u0437\u043a\u0430 \u043f\u0430\u043c\u044f\u0442\u0438: {_mem_recall_err}")
            else:'''

ALREADY = "ПАМЯТЬ АГЕНТА (патч): подмешиваем его сенсорную память"


def main() -> int:
    if not TARGET.exists():
        print(f"\u2717 \u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d {TARGET}")
        print("  \u0417\u0430\u043f\u0443\u0441\u0442\u0438 \u0441\u043a\u0440\u0438\u043f\u0442 \u0438\u0437 \u041a\u041e\u0420\u041d\u042f \u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u0438\u044f (\u0442\u0430\u043c \u0433\u0434\u0435 \u043f\u0430\u043f\u043a\u0430 studio/).")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if ALREADY in src:
        print("\u2139 \u041f\u0430\u0442\u0447 \u0443\u0436\u0435 \u043d\u0430\u043b\u043e\u0436\u0435\u043d \u0440\u0430\u043d\u0435\u0435 \u2014 \u043d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u0434\u0435\u043b\u0430\u044e.")
        return 0

    if OLD not in src:
        print("\u2717 \u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0432\u0435\u0442\u043a\u0430 `if talking:` \u0432 \u043e\u0436\u0438\u0434\u0430\u0435\u043c\u043e\u043c \u0432\u0438\u0434\u0435.")
        print("  \u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 \u0444\u0430\u0439\u043b\u0430 \u043e\u0442\u043b\u0438\u0447\u0430\u0435\u0442\u0441\u044f. \u0424\u0430\u0439\u043b \u043d\u0435 \u0438\u0437\u043c\u0435\u043d\u0451\u043d \u2014 \u043d\u0430\u043f\u0438\u0448\u0438 \u0411\u0440\u0430\u0442\u0443.")
        return 1

    backup = TARGET.with_suffix(".py.bak_memory_recall")
    backup.write_text(src, encoding="utf-8")

    patched = src.replace(OLD, NEW)
    TARGET.write_text(patched, encoding="utf-8")

    print("\u2713 \u041f\u0430\u0442\u0447 \u043d\u0430\u043b\u043e\u0436\u0435\u043d \u0443\u0441\u043f\u0435\u0448\u043d\u043e.")
    print(f"  \u0420\u0435\u0437\u0435\u0440\u0432\u043d\u0430\u044f \u043a\u043e\u043f\u0438\u044f: {backup}")
    print()
    print("  \u0422\u0435\u043f\u0435\u0440\u044c \u043f\u0440\u0438 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0435 \u0441 \u0430\u0433\u0435\u043d\u0442\u043e\u043c \u0435\u0433\u043e \u0441\u0435\u043d\u0441\u043e\u0440\u043d\u0430\u044f \u043f\u0430\u043c\u044f\u0442\u044c")
    print("  (\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u044b) \u043f\u043e\u0434\u0433\u0440\u0443\u0436\u0430\u0435\u0442\u0441\u044f \u0432 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442.")
    print("  \u0410\u0433\u0435\u043d\u0442 \u043f\u043e\u043c\u043d\u0438\u0442 \u0432\u0447\u0435\u0440\u0430\u0448\u043d\u0435\u0435 \u2014 \u043f\u043e-\u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0435\u043c\u0443, \u043d\u0435 \u0438\u0437 \u0432\u0435\u0436\u043b\u0438\u0432\u043e\u0441\u0442\u0438.")
    print()
    print("  \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: \u0441\u043f\u0440\u043e\u0441\u0438 A01 «\u043e \u0447\u0451\u043c \u043c\u044b \u0432\u0447\u0435\u0440\u0430 \u0433\u043e\u0432\u043e\u0440\u0438\u043b\u0438?» \u2014")
    print("  \u0434\u043e\u043b\u0436\u0435\u043d \u0432\u0441\u043f\u043e\u043c\u043d\u0438\u0442\u044c \u043a\u0432\u0430\u0440\u0442\u0438\u0440\u0443, \u043a\u0430\u0440\u0442\u043e\u0448\u043a\u0443, \u0421\u0432\u0435\u0447\u0438.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
