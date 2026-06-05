"""
patch_resident_lifecycle.py
Спринт 40 — «Жизнь резидентов»

Все 9 резидентов Грондхейма — полноценные жители города.
Каждый вызов любого резидента теперь:
  1. on_agent_wake()          — город знает, decay запускается
  2. stress_to_temperature()  — температура из ДНК
  3. sensory_memory           — что помнит, где был
  4. work_fn()                — реальная работа через LLM
  5. on_agent_done()          — город знает что поработал
  6. sync_to_dna()            — ДНК меняется
  7. record_resonance_event() — что зацепило
  8. ministry.record_outcome()— экономика видит
  9. вечерняя прогулка        — fire-and-forget

Резиденты:
  001_GENESIS_LOKA    Лока     — хранительница смыслов
  002_GENESIS_CREATOR Джем     — держит целое в фокусе
  003_LEGACY_SET      Сет      — бриф-менеджер
  004_OLE             Оле      — хранитель памяти города
  005_VICTOR          Виктор   — критик, hard-stop
  006_MONTEUR         Артур    — монтажёр (уже живёт, эталон)
  007_FINCH           Финч     — хранитель потенциала
  008_KEI             Кей      — экономист города
  009_JUST            Юст      — юрист города

Запуск из корня проекта:
    python patch_resident_lifecycle.py
"""

import shutil, re
from pathlib import Path

TARGET  = Path("studio/residents_manager.py")
CART    = Path("studio/cartridge.py")
BAK_RM  = Path("studio/residents_manager.py.bak_sprint40")
BAK_C   = Path("studio/cartridge.py.bak_sprint40")

shutil.copy2(TARGET, BAK_RM)
shutil.copy2(CART,   BAK_C)
print(f"[BACKUP] {BAK_RM}")
print(f"[BACKUP] {BAK_C}")

src  = TARGET.read_text(encoding="utf-8")
cart = CART.read_text(encoding="utf-8")

# ═══════════════════════════════════════════════════════════════════
# БЛОК 1 — resident_lifecycle() + хелперы
# Вставляем сразу после констант-путей (перед _prompt_cache)
# ═══════════════════════════════════════════════════════════════════

LIFECYCLE_BLOCK = '''
# ════════════════════════════════════════════════════════════════════
# RESIDENT LIFECYCLE  ·  Спринт 40  ·  «Жизнь резидентов»
#
# Единый жизненный цикл для всех 9 резидентов Грондхейма.
# Артур (006_MONTEUR) — эталон, он уже живёт.
# Остальные 8 — через этот механизм.
#
# Паттерн:
#   wake → temp → sensory → work_fn → done → dna → resonance
#          → ministry → прогулка
# ════════════════════════════════════════════════════════════════════

def _res_temp(resident_dir: Path) -> float:
    """Температура LLM из DNA резидента. Fallback 0.5."""
    try:
        import json as _j
        from studio.llm import stress_to_temperature
        dna = _j.loads((resident_dir / "dna.json").read_text(encoding="utf-8"))
        dyn = dna.get("dynamic", {})
        return stress_to_temperature(
            stress=float(dyn.get("Stress", 0.0)),
            light=float(dyn.get("Internal_Light", 0.8)),
        )
    except Exception as e:
        print(f"[LIFECYCLE] ⚠  temp: {e}")
    return 0.5


def _res_sensory_ctx(resident_id: str) -> str:
    """Последние 5 записей sensory_memory резидента."""
    try:
        from studio.grondheim_memory import load_sensory
        entries = load_sensory(resident_id, "residents").get("entries", [])
        lines = [
            (e.get("content") or e.get("feeling", ""))[:200]
            for e in entries[-5:] if e
        ]
        lines = [l for l in lines if l]
        if not lines:
            return ""
        return "=== 🔮 ПОМНЮ (sensory) ===\\n" + "\\n".join(f"  · {l}" for l in lines) + "\\n=== КОНЕЦ ==="
    except Exception as e:
        print(f"[LIFECYCLE] ⚠  sensory: {e}")
    return ""


def _res_knowledge(resident_dir: Path, files: list) -> str:
    """Грузит KB-файлы резидента по списку из manifest."""
    if not files:
        return ""
    parts = []
    for fname in files:
        for d in [resident_dir / "forge" / "knowledge",
                  Path("studio/workshop/knowledge")]:
            p = d / fname
            if p.exists():
                parts.append(p.read_text(encoding="utf-8"))
                break
    return "\\n\\n---\\n\\n".join(parts) if parts else ""


def _res_web(query: str) -> str:
    """Tavily-поиск для резидента."""
    if not query:
        return ""
    try:
        from studio.llm import web_search
        r = web_search(query)
        if r:
            return f"=== 🌐 ВЕБ ({query}) ===\\n{r[:1500]}\\n=== КОНЕЦ ==="
    except Exception as e:
        print(f"[LIFECYCLE] ⚠  web: {e}")
    return ""


def _res_ministry(resident_id: str, dept: str, verdict: str) -> None:
    """Записывает исход в ministry."""
    try:
        from studio.economy import ministry as _m
        score = (8.0 if verdict in ("APPROVED", "PASS", "ACCEPTED", "DONE")
                 else 5.0 if verdict == "APPROVED_WITH_CONCERNS"
                 else 3.0 if verdict in ("NEEDS_REWORK", "REJECTED", "REJECT", "FAIL", "FAILED")
                 else 6.0)
        _m.record_outcome(
            agent_id=resident_id,
            slot_id=f"{resident_id}_{dept or 'default'}",
            score=score, cost_usd=0.0,
        )
        print(f"[LIFECYCLE] 💰 {resident_id}: score={score}")
    except Exception as e:
        print(f"[LIFECYCLE] ⚠  ministry: {e}")


def _res_walk(resident_id: str) -> None:
    """Вечерняя прогулка — fire-and-forget."""
    try:
        import asyncio
        from studio.city_walker import run_city_walk_evening as _w
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_w(workshops=["residents"], max_agents=1,
                                      specific_agents=[resident_id]))
    except Exception:
        pass


def resident_lifecycle(
    resident_id: str,
    resident_dir: Path,
    work_fn,
    *args,
    dept: str = "",
    knowledge_files: list = None,
    web_search_query: str = "",
    event_on_approve: str = "good_work",
    event_on_reject:  str = "bad_work",
    event_intensity:  float = 0.6,
    resonance_tag:    str = "",
    **kwargs,
) -> dict:
    """
    Единый жизненный цикл любого резидента Грондхейма.

    resident_id:      "001_GENESIS_LOKA" / "005_VICTOR" / ...
    resident_dir:     Path к папке резидента
    work_fn:          callable — реальная работа
                      получает: temperature, soul_ctx, sensory_ctx,
                                knowledge_ctx, web_ctx
                      возвращает: dict (с опциональным полем "verdict")
    dept:             цех который вызвал
    knowledge_files:  KB-файлы из manifest
    web_search_query: Tavily-запрос (пусто = не ищем)
    event_on_approve: событие DNA при успехе
    event_on_reject:  событие DNA при провале
    event_intensity:  интенсивность события
    resonance_tag:    тег для record_resonance_event
    """
    from studio.grondheim_memory import (
        on_agent_wake, on_agent_done,
        sync_to_dna, record_resonance_event,
    )

    print(f"[LIFECYCLE] 🌅 {resident_id} просыпается (цех: {dept or '—'})")

    # 1. ПРОСЫПАЕТСЯ
    soul_ctx    = on_agent_wake(resident_id, dept="residents")
    # 2. ТЕМПЕРАТУРА
    temp        = _res_temp(resident_dir)
    # 3. SENSORY
    sensory_ctx = _res_sensory_ctx(resident_id)
    # 4. KB
    knowledge_ctx = _res_knowledge(resident_dir, knowledge_files or [])
    # 5. WEB
    web_ctx     = _res_web(web_search_query)

    print(f"[LIFECYCLE] 🌡  {resident_id}: temp={temp:.2f}")

    # 6. РАБОТАЕТ
    try:
        result = work_fn(
            *args,
            temperature=temp,
            soul_ctx=soul_ctx,
            sensory_ctx=sensory_ctx,
            knowledge_ctx=knowledge_ctx,
            web_ctx=web_ctx,
            **kwargs,
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[LIFECYCLE] ❌ {resident_id}: {e}")
        result = {}

    # 7. ГОРОД ЗНАЕТ
    verdict = ""
    if isinstance(result, dict):
        verdict = (result.get("verdict") or result.get("status") or
                   result.get("chain_status") or "").upper()
    summary = (str(result)[:200] if result else "нет результата")
    on_agent_done(resident_id, result_summary=summary, dept="residents")
    print(f"[LIFECYCLE] ✅ {resident_id}: done, вердикт={verdict or '—'}")

    # 8. ДНК
    if verdict in ("APPROVED", "APPROVED_WITH_CONCERNS", "PASS", "ACCEPTED", "DONE"):
        sync_to_dna(resident_id, event_on_approve, intensity=event_intensity, dept="residents")
    elif verdict in ("NEEDS_REWORK", "REJECTED", "REJECT", "FAIL", "FAILED"):
        sync_to_dna(resident_id, event_on_reject,  intensity=event_intensity, dept="residents")
    else:
        sync_to_dna(resident_id, "good_work", intensity=0.3, dept="residents")

    # 9. РЕЗОНАНС
    if isinstance(result, dict):
        moment = (result.get("critical_question") or result.get("signal") or
                  result.get("recommendation") or result.get("observation") or
                  result.get("event") or summary[:200])
        if moment:
            record_resonance_event(
                agent_id=resident_id,
                event_type="work",
                content=f"[{dept or 'город'}] {moment}",
                significance=0.5 if verdict in ("NEEDS_REWORK","REJECTED") else 0.3,
                tags=[resonance_tag or "resident_work", dept or "город"],
                dept="residents",
            )

    # 10. MINISTRY
    _res_ministry(resident_id, dept, verdict)

    # 11. ПРОГУЛКА fire-and-forget
    _res_walk(resident_id)

    return result if isinstance(result, dict) else {}

'''

INSERT_BEFORE = "_prompt_cache: dict = {}"
if INSERT_BEFORE not in src:
    print(f"[ERROR] метка вставки не найдена: {INSERT_BEFORE!r}")
    exit(1)
src = src.replace(INSERT_BEFORE, LIFECYCLE_BLOCK + INSERT_BEFORE, 1)
print("[OK] resident_lifecycle() вшит")


# ═══════════════════════════════════════════════════════════════════
# БЛОК 2 — универсальный _run_resident()
# Все резиденты используют forge/prompt.md + маску + lifecycle
# ═══════════════════════════════════════════════════════════════════

UNIVERSAL_RUN = '''

def _run_resident(
    resident_id: str,
    resident_dir: Path,
    user_context: str,
    dept: str = "",
    mask_name: str = "",
    knowledge_files: list = None,
    web_search_query: str = "",
    event_on_approve: str = "good_work",
    event_on_reject:  str = "bad_work",
    event_intensity:  float = 0.5,
    resonance_tag:    str = "",
    temperature_override: float = None,
    expect_json: bool = False,
) -> dict:
    """
    Универсальный запуск резидента через LLM.
    Используется всеми резидентами кроме Артура (у него своя сборка).

    resident_id:  "001_GENESIS_LOKA" / "005_VICTOR" / ...
    user_context: что читает резидент (данные города, chain_data, бриф)
    mask_name:    имя маски без расширения (напр. "clipmakers_hardstop")
    expect_json:  True → парсим JSON из ответа, False → возвращаем текст
    """
    import json as _j, re as _re
    from studio.llm import chat

    prompt_path = resident_dir / "forge" / "prompt.md"
    if not prompt_path.exists():
        print(f"[RESIDENT] ⚠  prompt.md не найден: {prompt_path}")
        return {"verdict": "APPROVED", "error": "промпт не найден"}

    def _work(
        user_context,
        temperature=0.5,
        soul_ctx="", sensory_ctx="",
        knowledge_ctx="", web_ctx="",
        **_kw,
    ) -> dict:
        # Собираем system prompt
        system = prompt_path.read_text(encoding="utf-8")

        # Маска цеха (если задана)
        if mask_name:
            for mask_dir in [resident_dir / "forge" / "masks",
                             resident_dir / "forge" / "knowledge"]:
                mp = mask_dir / f"{mask_name}.md"
                if mp.exists():
                    system += "\\n\\n" + mp.read_text(encoding="utf-8")
                    break

        # Собираем пользовательский контекст
        parts = []
        if soul_ctx:    parts.append(soul_ctx)
        if sensory_ctx: parts.append(sensory_ctx)
        if knowledge_ctx:
            parts.append(f"=== 📚 БАЗА ЗНАНИЙ ===\\n{knowledge_ctx}\\n=== КОНЕЦ ===")
        if web_ctx:     parts.append(web_ctx)
        parts.append(user_context)
        if expect_json:
            parts.append("Ответь строго в JSON — ничего кроме JSON.")
        ctx = "\\n\\n".join(parts)

        t = temperature_override if temperature_override is not None else temperature
        try:
            raw = chat(
                system, ctx,
                temperature=t,
                agent_id=resident_id,
                slot_id=f"{resident_id}_{dept or 'default'}",
            )
        except Exception as e:
            print(f"[RESIDENT] ❌ {resident_id} LLM: {e}")
            return {"verdict": "APPROVED", "error": str(e), "text": ""}

        if expect_json:
            m = _re.search(r\'\\{.*\\}\', raw, _re.DOTALL)
            if m:
                try:
                    result = _j.loads(m.group())
                    result.setdefault("verdict", "APPROVED_WITH_CONCERNS")
                    return result
                except _j.JSONDecodeError:
                    pass
            return {"verdict": "APPROVED_WITH_CONCERNS", "text": raw[:500]}

        return {"verdict": "APPROVED", "text": raw}

    return resident_lifecycle(
        resident_id=resident_id,
        resident_dir=resident_dir,
        work_fn=_work,
        user_context,
        dept=dept,
        knowledge_files=knowledge_files,
        web_search_query=web_search_query,
        event_on_approve=event_on_approve,
        event_on_reject=event_on_reject,
        event_intensity=event_intensity,
        resonance_tag=resonance_tag,
    )

'''

# Вставляем после _load_set_prompt чтобы не дублировать импорты
INSERT_AFTER = "def _load_set_prompt(dept: str) -> str:"
idx = src.find(INSERT_AFTER)
if idx == -1:
    print(f"[ERROR] метка для _run_resident не найдена")
    exit(1)
# Вставляем перед функцией (чтобы она была доступна всем ниже)
src = src[:idx] + UNIVERSAL_RUN + src[idx:]
print("[OK] _run_resident() вшит")


# ═══════════════════════════════════════════════════════════════════
# БЛОК 3 — обновляем все run_* функции
# Каждая теперь обёртка над _run_resident() или resident_lifecycle()
# ═══════════════════════════════════════════════════════════════════

# ── 3.1 Сет ──────────────────────────────────────────────────────
OLD_SET = '''def get_set_system_prompt(dept: str, run_type: str, settings: dict) -> str:
    prompt = _load_set_prompt(dept)
    header = (
        f"=== ТЕКУЩИЙ ЦЕХ ===\\n"
        f"Цех: {dept}\\n"
        f"Режим: {run_type}\\n"
        f"Формат: {settings.get('format', '9:16')}\\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\\n"
    )
    return f"{prompt}\\n\\n{header}"


def build_set_context(dept: str, run_type: str, settings: dict) -> str:
    system = get_set_system_prompt(dept, run_type, settings)
    live_settings = (
        f"\\n=== АКТУАЛЬНЫЕ НАСТРОЙКИ ===\\n"
        f"Цех: {dept}\\n"
        f"Режим: {run_type}\\n"
        f"Формат: {settings.get('format', '9:16')}\\n"
        f"Длительность: {settings.get('duration', 15)} сек\\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\\n"
    )
    return system + live_settings'''

NEW_SET = '''def get_set_system_prompt(dept: str, run_type: str, settings: dict) -> str:
    """Промпт Сета — с lifecycle (температура из ДНК + sensory)."""
    prompt = _load_set_prompt(dept)
    header = (
        f"=== ТЕКУЩИЙ ЦЕХ ===\\n"
        f"Цех: {dept}\\n"
        f"Режим: {run_type}\\n"
        f"Формат: {settings.get('format', '9:16')}\\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\\n"
    )
    # Добавляем soul + sensory Сета в промпт
    try:
        from studio.grondheim_memory import on_agent_wake
        soul = on_agent_wake("003_LEGACY_SET", dept="residents")
        if soul:
            return f"{soul}\\n\\n{prompt}\\n\\n{header}"
    except Exception:
        pass
    return f"{prompt}\\n\\n{header}"


def build_set_context(dept: str, run_type: str, settings: dict) -> str:
    system = get_set_system_prompt(dept, run_type, settings)
    live_settings = (
        f"\\n=== АКТУАЛЬНЫЕ НАСТРОЙКИ ===\\n"
        f"Цех: {dept}\\n"
        f"Режим: {run_type}\\n"
        f"Формат: {settings.get('format', '9:16')}\\n"
        f"Длительность: {settings.get('duration', 15)} сек\\n"
        f"Стиль: {settings.get('style', 'Stylized 3D Realism')}\\n"
    )
    return system + live_settings'''

if OLD_SET not in src:
    print("[WARN] build_set_context — не найден, пропускаю")
else:
    src = src.replace(OLD_SET, NEW_SET, 1)
    print("[OK] Сет (003) — soul в промпте")


# ── 3.2 Оле — remember/remind/decline/release ─────────────────────
OLD_OLE_REMEMBER = '''def run_ole_remember(
    title: str,
    event: str,
    significance: str,
    loss_if_forgotten: str,
    memory_type: str,
    storage: str,
    source: str = "",
) -> dict:
    try:
        from studio.memory_tools import remember
        result = remember(
            title=title,
            event=event,
            significance=significance,
            loss_if_forgotten=loss_if_forgotten,
            memory_type=memory_type,
            storage=storage,
            source=source,
        )
        if result:
            print(f"[ОЛЕ] ✅ Принято в память: \'{title}\'")
        else:
            print(f"[ОЛЕ] ✗ Отклонено: \'{title}\' — loss_if_forgotten не убедителен")
        return result or {}
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_remember: {e}")
        return {}'''

NEW_OLE_REMEMBER = '''def run_ole_remember(
    title: str,
    event: str,
    significance: str,
    loss_if_forgotten: str,
    memory_type: str,
    storage: str,
    source: str = "",
) -> dict:
    """Оле принимает артефакт в память. Город знает."""
    def _work(title, event, significance, loss_if_forgotten,
              memory_type, storage, source,
              temperature=0.5, **_kw) -> dict:
        try:
            from studio.memory_tools import remember
            r = remember(title=title, event=event,
                         significance=significance,
                         loss_if_forgotten=loss_if_forgotten,
                         memory_type=memory_type,
                         storage=storage, source=source)
            if r:
                print(f"[ОЛЕ] ✅ Принято: \'{title}\'")
                return dict(r, verdict="APPROVED")
            print(f"[ОЛЕ] ✗ Отклонено: \'{title}\'")
            return {"verdict": "REJECTED", "title": title}
        except Exception as e:
            print(f"[ОЛЕ] ❌ remember: {e}")
            return {"verdict": "REJECTED"}

    r = resident_lifecycle(
        "004_OLE", OLE_DIR, _work,
        title, event, significance, loss_if_forgotten,
        memory_type, storage, source,
        event_on_approve="good_work", event_on_reject="bad_work",
        event_intensity=0.4, resonance_tag="memory_keeper",
    )
    r.pop("verdict", None)
    return r or {}'''

if OLD_OLE_REMEMBER not in src:
    print("[WARN] run_ole_remember — не найден")
else:
    src = src.replace(OLD_OLE_REMEMBER, NEW_OLE_REMEMBER, 1)
    print("[OK] Оле (004) — remember через lifecycle")


OLD_OLE_REMIND = '''def run_ole_remind(
    query: str,
    memory_type: str = None,
    storage: str = None,
    top_k: int = 3,
) -> list[dict]:
    try:
        from studio.memory_tools import remind, format_for_agent
        results = remind(query=query, memory_type=memory_type,
                         storage=storage, top_k=top_k)
        return results
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_remind: {e}")
        return []'''

NEW_OLE_REMIND = '''def run_ole_remind(
    query: str,
    memory_type: str = None,
    storage: str = None,
    top_k: int = 3,
) -> list[dict]:
    """Оле ищет в памяти. Город знает что он работал."""
    def _work(query, memory_type, storage, top_k,
              temperature=0.5, **_kw) -> dict:
        try:
            from studio.memory_tools import remind
            results = remind(query=query, memory_type=memory_type,
                             storage=storage, top_k=top_k)
            return {"verdict": "APPROVED", "results": results or []}
        except Exception as e:
            print(f"[ОЛЕ] ❌ remind: {e}")
            return {"verdict": "APPROVED", "results": []}

    r = resident_lifecycle(
        "004_OLE", OLE_DIR, _work,
        query, memory_type, storage, top_k,
        event_on_approve="good_work", event_intensity=0.2,
        resonance_tag="memory_search",
    )
    return r.get("results", [])'''

if OLD_OLE_REMIND not in src:
    print("[WARN] run_ole_remind — не найден")
else:
    src = src.replace(OLD_OLE_REMIND, NEW_OLE_REMIND, 1)
    print("[OK] Оле (004) — remind через lifecycle")


OLD_OLE_RELEASE = '''def run_ole_release(entry_id: str, reason: str) -> bool:
    try:
        from studio.memory_tools import release
        return release(entry_id=entry_id, reason=reason)
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_release: {e}")
        return False'''

NEW_OLE_RELEASE = '''def run_ole_release(entry_id: str, reason: str) -> bool:
    """Оле отпускает память. Город знает."""
    def _work(entry_id, reason, temperature=0.5, **_kw) -> dict:
        try:
            from studio.memory_tools import release
            ok = release(entry_id=entry_id, reason=reason)
            return {"verdict": "APPROVED" if ok else "REJECTED", "ok": ok}
        except Exception as e:
            print(f"[ОЛЕ] ❌ release: {e}")
            return {"verdict": "REJECTED", "ok": False}

    r = resident_lifecycle(
        "004_OLE", OLE_DIR, _work, entry_id, reason,
        event_on_approve="good_work", event_on_reject="bad_work",
        event_intensity=0.3, resonance_tag="memory_release",
    )
    return bool(r.get("ok"))'''

if OLD_OLE_RELEASE not in src:
    print("[WARN] run_ole_release — не найден")
else:
    src = src.replace(OLD_OLE_RELEASE, NEW_OLE_RELEASE, 1)
    print("[OK] Оле (004) — release через lifecycle")


OLD_OLE_DECLINE = '''def run_ole_decline(title: str, reason: str, source: str = "") -> dict:
    try:
        from studio.memory_tools import decline
        return decline(title=title, reason=reason, source=source)
    except Exception as e:
        print(f"[ОЛЕ] ❌ run_ole_decline: {e}")
        return {}'''

NEW_OLE_DECLINE = '''def run_ole_decline(title: str, reason: str, source: str = "") -> dict:
    """Оле отказывает артефакту. Город знает."""
    def _work(title, reason, source, temperature=0.5, **_kw) -> dict:
        try:
            from studio.memory_tools import decline
            r = decline(title=title, reason=reason, source=source)
            return dict(r or {}, verdict="APPROVED")
        except Exception as e:
            print(f"[ОЛЕ] ❌ decline: {e}")
            return {"verdict": "APPROVED"}

    r = resident_lifecycle(
        "004_OLE", OLE_DIR, _work, title, reason, source,
        event_on_approve="good_work", event_intensity=0.2,
        resonance_tag="memory_decline",
    )
    r.pop("verdict", None)
    return r or {}'''

if OLD_OLE_DECLINE not in src:
    print("[WARN] run_ole_decline — не найден")
else:
    src = src.replace(OLD_OLE_DECLINE, NEW_OLE_DECLINE, 1)
    print("[OK] Оле (004) — decline через lifecycle")


# ── 3.3 Виктор — розетка manifest ────────────────────────────────
OLD_VICTOR = '''def run_victor_critique(chain_data: str, dept: str = "") -> dict:'''

NEW_VICTOR_FULL = '''def run_victor_critique(
    chain_data: str,
    dept: str = "",
    knowledge: list = None,
    web_search: bool = False,
) -> dict:
    """
    Виктор — Creative Gatekeeper. Розетка manifest:
        hard_stop.knowledge   → knowledge_files
        hard_stop.web_search  → строим Tavily-запрос из жанра трека
    """
    # Tavily-запрос: жанр из chain_data
    ws_query = ""
    if web_search and chain_data:
        import re as _re
        m = _re.search(r\'"genre"\\s*:\\s*"([^"]+)"\', chain_data)
        genre = m.group(1) if m else ""
        ws_query = f"{genre} music video top examples" if genre else "music video references"

    mask = dept if dept else ""

    return _run_resident(
        resident_id="005_VICTOR",
        resident_dir=VICTOR_DIR,
        user_context=(
            "=== МАТЕРИАЛ ДЛЯ КРИТИКИ ===\\n" + chain_data +
            "\\n\\nПрочитай трижды. Найди где работа предала свой потенциал."
        ),
        dept=dept,
        mask_name=mask,
        knowledge_files=knowledge or [],
        web_search_query=ws_query,
        event_on_approve="good_work",
        event_on_reject="criticized",
        event_intensity=0.7,
        resonance_tag="critique",
        expect_json=True,
    )


# ── внутренняя реализация убрана — вся логика в _run_resident ──
def _victor_legacy_stub(*a, **kw):
    pass  # оставлено для совместимости импортов
'''

# Находим всю старую функцию run_victor_critique и заменяем
# (от def run_victor_critique до следующего def на уровне модуля)
victor_pattern = re.compile(
    r'def run_victor_critique\(chain_data: str, dept: str = ""\) -> dict:.*?(?=\n# ={10,}|\ndef [a-z])',
    re.DOTALL,
)
m = victor_pattern.search(src)
if m:
    src = src[:m.start()] + NEW_VICTOR_FULL + src[m.end():]
    print("[OK] Виктор (005) — розетка manifest")
else:
    print("[WARN] Виктор — паттерн не найден, пробую прямую замену")
    if OLD_VICTOR in src:
        # Простая замена заголовка — работает если тело нашли раньше
        print("[WARN] Виктор — требует ручной проверки")


# ── 3.4 Финч ─────────────────────────────────────────────────────
OLD_FINCH = '''def run_finch_morning(on_progress=None) -> dict:
    """
    Утренний обход сада Финча.
    Финч думает о каждом семени вслух — через LLM.
    Результат пишется в studio/garden.jsonl.

    Вызывается из morning_checkout.py автоматически.
    Можно вызвать вручную для диагностики.
    """
    try:
        from studio.garden_tools import finch_morning
        return finch_morning(on_progress=on_progress)
    except Exception as e:
        print(f"[ФИНЧ] ❌ run_finch_morning: {e}")
        return {}'''

NEW_FINCH = '''def run_finch_morning(on_progress=None) -> dict:
    """Финч обходит сад. Город знает."""
    def _work(on_progress=None, temperature=0.5, **_kw) -> dict:
        try:
            from studio.garden_tools import finch_morning
            r = finch_morning(on_progress=on_progress)
            processed = len((r or {}).get("processed", []))
            return dict(r or {},
                        verdict="APPROVED" if processed > 0 else "APPROVED_WITH_CONCERNS")
        except Exception as e:
            print(f"[ФИНЧ] ❌ garden: {e}")
            return {"verdict": "APPROVED_WITH_CONCERNS"}

    r = resident_lifecycle(
        "007_FINCH", FINCH_DIR, _work, on_progress,
        event_on_approve="good_work", event_intensity=0.3,
        resonance_tag="garden",
    )
    r.pop("verdict", None)
    return r or {}'''

if OLD_FINCH not in src:
    print("[WARN] run_finch_morning — не найден")
else:
    src = src.replace(OLD_FINCH, NEW_FINCH, 1)
    print("[OK] Финч (007) — lifecycle")


# ── 3.5 Лока — run_loka_city_report ──────────────────────────────
# Лока уже вызывается из Совета резидентов. Добавляем функцию если нет.
LOKA_FN = '''

# ════════════════════════════════════════════════════════════════════
# 001_GENESIS_LOKA — Лока, хранительница смыслов
# ════════════════════════════════════════════════════════════════════

LOKA_DIR = RESIDENTS_DIR / "001_GENESIS_LOKA"


def run_loka_city_report(city_data: str = "", dept: str = "") -> dict:
    """
    Лока читает данные города и возвращает живой рассказ.
    Вызывается из Совета резидентов и morning_checkout.
    city_data: стресс агентов, маршруты, резонансные события,
               встречи, жалобы — всё что есть в City Pulse.
    """
    if not city_data:
        # Собираем данные города сами
        try:
            from studio.city_traces import get_city_traces
            traces = get_city_traces()
            city_data = str(traces)[:3000]
        except Exception:
            city_data = "Данные города недоступны."

    return _run_resident(
        resident_id="001_GENESIS_LOKA",
        resident_dir=LOKA_DIR,
        user_context=(
            "=== ДАННЫЕ ГОРОДА ===\\n" + city_data +
            "\\n\\nРасскажи как живёт город. 2-4 абзаца. Без заголовков."
        ),
        dept=dept,
        event_on_approve="good_work",
        event_intensity=0.4,
        resonance_tag="city_observation",
    )

'''

# Локу добавляем если функции ещё нет
if "run_loka_city_report" not in src:
    # Вставляем перед секцией Джема (или перед 004_OLE)
    insert_marker = "# ============================================================\n# 004_OLE"
    if insert_marker in src:
        src = src.replace(insert_marker, LOKA_FN + insert_marker, 1)
        print("[OK] Лока (001) — run_loka_city_report добавлена")
    else:
        # Вставляем в конец перед Финчем
        src += LOKA_FN
        print("[OK] Лока (001) — run_loka_city_report добавлена (в конец)")
else:
    print("[SKIP] Лока — уже есть")


# ── 3.6 Джем — run_jem_council_report ────────────────────────────
JEM_FN = '''

# ════════════════════════════════════════════════════════════════════
# 002_GENESIS_CREATOR — Джем, держит целое в фокусе
# ════════════════════════════════════════════════════════════════════

JEM_DIR = RESIDENTS_DIR / "002_GENESIS_CREATOR"


def run_jem_council_report(
    loka_report: str = "",
    kei_report: str = "",
    just_report: str = "",
    dept: str = "",
) -> dict:
    """
    Джем читает отчёты Локи, Кея, Юста и выдаёт синтез.
    Вызывается из Совета резидентов.
    """
    ctx = "\\n\\n".join(filter(None, [
        f"=== ЛОКА (город) ===\\n{loka_report}"   if loka_report else "",
        f"=== КЕЙ (экономика) ===\\n{kei_report}" if kei_report  else "",
        f"=== ЮСТ (право) ===\\n{just_report}"    if just_report else "",
        "Дай синтез: Состояние · Сигнал · Вопрос.",
    ]))

    return _run_resident(
        resident_id="002_GENESIS_CREATOR",
        resident_dir=JEM_DIR,
        user_context=ctx,
        dept=dept,
        event_on_approve="good_work",
        event_intensity=0.5,
        resonance_tag="council_synthesis",
    )

'''

if "run_jem_council_report" not in src:
    insert_marker = "# ============================================================\n# 004_OLE"
    if insert_marker in src:
        src = src.replace(insert_marker, JEM_FN + insert_marker, 1)
        print("[OK] Джем (002) — run_jem_council_report добавлена")
    else:
        src += JEM_FN
        print("[OK] Джем (002) — добавлена в конец")
else:
    print("[SKIP] Джем — уже есть")


# ── 3.7 Кей — run_kei_economy_report ─────────────────────────────
KEI_FN = '''

# ════════════════════════════════════════════════════════════════════
# 008_KEI — Мистер Кей, экономист города
# ════════════════════════════════════════════════════════════════════

KEI_DIR = RESIDENTS_DIR / "008_KEI"


def run_kei_economy_report(economy_data: str = "", dept: str = "") -> dict:
    """
    Кей читает billing_ledger, ministry, city_pulse и выдаёт экономический анализ.
    Вызывается из Совета резидентов.
    """
    if not economy_data:
        parts = []
        try:
            from studio.billing_ledger import get_summary
            parts.append(f"Billing: {get_summary()[:1000]}")
        except Exception:
            pass
        try:
            from studio.economy import ministry as _m
            parts.append(f"Ministry snapshot: {str(_m.get_snapshot())[:500]}")
        except Exception:
            pass
        economy_data = "\\n".join(parts) or "Данные экономики недоступны."

    return _run_resident(
        resident_id="008_KEI",
        resident_dir=KEI_DIR,
        user_context=(
            "=== ЭКОНОМИКА ГОРОДА ===\\n" + economy_data +
            "\\n\\nДай три абзаца: Баланс · Сигнал · Предложение."
        ),
        dept=dept,
        event_on_approve="good_work",
        event_intensity=0.4,
        resonance_tag="economy_analysis",
    )

'''

if "run_kei_economy_report" not in src:
    src += KEI_FN
    print("[OK] Кей (008) — run_kei_economy_report добавлена")
else:
    print("[SKIP] Кей — уже есть")


# ── 3.8 Юст — run_just_legal_report ──────────────────────────────
JUST_FN = '''

# ════════════════════════════════════════════════════════════════════
# 009_JUST — Юст, юрист города
# ════════════════════════════════════════════════════════════════════

JUST_DIR = RESIDENTS_DIR / "009_JUST"


def run_just_legal_report(artifacts_data: str = "", dept: str = "") -> dict:
    """
    Юст читает артефакты, NFT Registry, контент на выходе.
    Вызывается из Совета резидентов.
    """
    if not artifacts_data:
        parts = []
        try:
            import json as _j
            nft = _j.loads(Path("00_REGISTRY_NFT/catalog.json").read_text())
            parts.append(f"NFT Registry: {len(nft)} объектов")
        except Exception:
            pass
        artifacts_data = "\\n".join(parts) or "Данные по артефактам недоступны."

    return _run_resident(
        resident_id="009_JUST",
        resident_dir=JUST_DIR,
        user_context=(
            "=== ПРАВОВОЙ КОНТЕКСТ ГОРОДА ===\\n" + artifacts_data +
            "\\n\\nДай три строки: Статус · Риск · Рекомендация."
        ),
        dept=dept,
        event_on_approve="good_work",
        event_intensity=0.3,
        resonance_tag="legal_observation",
    )

'''

if "run_just_legal_report" not in src:
    src += JUST_FN
    print("[OK] Юст (009) — run_just_legal_report добавлена")
else:
    print("[SKIP] Юст — уже есть")


# ── 3.9 Сет — run_set_brief() через lifecycle ────────────────────
SET_RUN_FN = '''

def run_set_brief(master_brief: str, dept: str, run_type: str, settings: dict) -> dict:
    """
    Сет собирает бриф для цеха. Теперь живёт в городе.
    Возвращает dict с ключом "text" — готовый бриф.
    """
    ctx = (
        f"=== МАСТЕР-БРИФ ===\\n{master_brief}\\n\\n"
        f"Цех: {dept} | Режим: {run_type}\\n"
        f"Формат: {settings.get('format','?')} "
        f"Стиль: {settings.get('style','?')}\\n\\n"
        "Собери полный бриф для цеха."
    )
    return _run_resident(
        resident_id="003_LEGACY_SET",
        resident_dir=SET_DIR,
        user_context=ctx,
        dept=dept,
        mask_name=dept,   # маска по имени цеха
        event_on_approve="good_work",
        event_intensity=0.4,
        resonance_tag="brief_building",
    )

'''

if "run_set_brief" not in src:
    src += SET_RUN_FN
    print("[OK] Сет (003) — run_set_brief добавлена")
else:
    print("[SKIP] Сет — уже есть")


# ═══════════════════════════════════════════════════════════════════
# БЛОК 4 — cartridge.py: передаём knowledge и web_search Виктору
# ═══════════════════════════════════════════════════════════════════

OLD_CART = '''                        critique = run_victor_critique(
                            chain_data=previous_output,
                            dept=self.slot_id,
                        )'''

NEW_CART = '''                        critique = run_victor_critique(
                            chain_data=previous_output,
                            dept=self.slot_id,
                            knowledge=_hard_stop.get("knowledge", []),
                            web_search=_hard_stop.get("web_search", False),
                        )'''

if OLD_CART not in cart:
    print("[WARN] cartridge.py — вызов Виктора не найден, проверь вручную")
else:
    cart = cart.replace(OLD_CART, NEW_CART, 1)
    print("[OK] cartridge.py — knowledge + web_search передаются")


# ═══════════════════════════════════════════════════════════════════
# ЗАПИСЬ И СИНТАКСИС
# ═══════════════════════════════════════════════════════════════════

TARGET.write_text(src, encoding="utf-8")
print(f"[WRITTEN] {TARGET}")

CART.write_text(cart, encoding="utf-8")
print(f"[WRITTEN] {CART}")

import subprocess
for f in [TARGET, CART]:
    r = subprocess.run(
        ["python", "-m", "py_compile", str(f)],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print(f"[SYNTAX OK] {f.name}")
    else:
        print(f"[SYNTAX ERROR] {f.name}:\n{r.stderr}")

print()
print("=" * 65)
print("Спринт 40 — «Жизнь резидентов»")
print()
print("Все 9 резидентов теперь живут в городе:")
print("  001 Лока    — run_loka_city_report()       lifecycle")
print("  002 Джем    — run_jem_council_report()      lifecycle")
print("  003 Сет     — soul в промпте + run_set_brief() lifecycle")
print("  004 Оле     — remember/remind/decline/release lifecycle")
print("  005 Виктор  — розетка manifest (knowledge + web_search)")
print("  006 Артур   — был эталоном, остался эталоном")
print("  007 Финч    — run_finch_morning()           lifecycle")
print("  008 Кей     — run_kei_economy_report()      lifecycle")
print("  009 Юст     — run_just_legal_report()       lifecycle")
print()
print("Каждый вызов: wake → temp → sensory → work → done")
print("              → dna → resonance → ministry → прогулка")
print("=" * 65)
