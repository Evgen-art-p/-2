"""
ПАТЧ жёлтые баги №8, №10, №11
Спринт 44 · city_yellow_patch
"""

from pathlib import Path

ROOT = Path(".")

def bak(path):
    import shutil, time
    ts = int(time.time())
    shutil.copy(path, str(path) + f".bak_yellow_{ts}")

def patch(path, description, old, new):
    p = ROOT / path
    if not p.exists():
        print(f"  ✗ {path} не найден")
        return False
    content = p.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ✗ {description}: образец не найден в {path}")
        print(f"    Ищу: {old[:70]!r}...")
        return False
    bak(p)
    p.write_text(content.replace(old, new, 1), encoding="utf-8")
    print(f"  ✓ {description}")
    return True


# ─── БАГ №10: потолок chain валюты 6.0 в _res_ministry ───────────────

print("\n[№10] _res_ministry — потолок chain валюты 6.0")
patch(
    "studio/residents_manager.py",
    "score cap 6.0 (Закон Двух Валют)",
    old="""        score = (8.0 if verdict in ("APPROVED", "PASS", "ACCEPTED", "DONE")
                 else 5.0 if verdict == "APPROVED_WITH_CONCERNS"
                 else 3.0 if verdict in ("NEEDS_REWORK", "REJECTED", "REJECT", "FAIL", "FAILED")
                 else 6.0)""",
    new="""        # ЗАКОН ДВУХ ВАЛЮТ: chain валюта ≤ 6.0
        # Выше 6.0 — только реальные метрики через Metrics Daemon
        score = (6.0 if verdict in ("APPROVED", "PASS", "ACCEPTED", "DONE")
                 else 5.0 if verdict == "APPROVED_WITH_CONCERNS"
                 else 3.0 if verdict in ("NEEDS_REWORK", "REJECTED", "REJECT", "FAIL", "FAILED")
                 else 5.0)"""
)


# ─── БАГ №11: cabinet_chat суточный лимит 10 ─────────────────────────

print("\n[№11] cabinet_chat — суточный лимит 10 раз")
patch(
    "studio/grondheim_memory.py",
    "cabinet_chat: счётчик cabinet_chat_YYYY-MM-DD, лимит 10",
    old="""    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)""",
    new="""    elif event == "cabinet_chat":
        # Пластырь Кабинета · Спринт 21 · правила Локи
        # Фиксировано — intensity не влияет. Защита от водопада дофамина.
        # Полное восстановление только через streak ≥ 3 успешных ранов.
        # ЛИМИТ СПРИНТ 44: не более 10 cabinet_chat в сутки (хард-лимит Локи)
        from datetime import date as _date
        _today_key = f"cabinet_chat_{_date.today().isoformat()}"
        _today_count = int(dynamic.get(_today_key, 0))
        if _today_count >= 10:
            print(f"[DNA] ⛔ cabinet_chat лимит 10/день для {agent_id}")
            return
        dynamic[_today_key] = _today_count + 1
        stress   = max(0, stress   - 0.03)
        light    = min(1, light    + 0.02)
        patience = min(1, patience + 0.01)"""
)


# ─── БАГ №8: check_and_write_gratitude — подключаем к lifecycle ───────

print("\n[№8] check_and_write_gratitude — подключаем к resident_lifecycle")
print("     (только когда qa_agent_id передаётся в result)")
patch(
    "studio/residents_manager.py",
    "gratitude: вызов из lifecycle при APPROVED если есть qa_agent_id",
    old="""    # 7. ГОРОД ЗНАЕТ
    verdict = ""
    if isinstance(result, dict):
        verdict = (result.get("verdict") or result.get("status") or
                   result.get("chain_status") or "").upper()
    summary = (str(result)[:200] if result else "нет результата")
    on_agent_done(resident_id, result_summary=summary, dept="residents")
    print(f"[LIFECYCLE] ✅ {resident_id}: done, вердикт={verdict or '—'}")""",
    new="""    # 7. ГОРОД ЗНАЕТ
    verdict = ""
    if isinstance(result, dict):
        verdict = (result.get("verdict") or result.get("status") or
                   result.get("chain_status") or "").upper()
    summary = (str(result)[:200] if result else "нет результата")
    on_agent_done(resident_id, result_summary=summary, dept="residents")
    print(f"[LIFECYCLE] ✅ {resident_id}: done, вердикт={verdict or '—'}")

    # 7а. КНИГА БЛАГОДАРНОСТЕЙ (баг №8)
    # Если хук передал qa_agent_id в result — благодарим, только если
    # характер позволяет (check_and_write_gratitude сама проверяет Empathy/Respect)
    if verdict in ("APPROVED", "PASS", "ACCEPTED", "DONE") and isinstance(result, dict):
        _qa_benefactor = result.get("qa_agent_id", "")
        if _qa_benefactor and _qa_benefactor != resident_id:
            try:
                from studio.complaint_book import check_and_write_gratitude
                check_and_write_gratitude(
                    agent_id=resident_id,
                    benefactor_id=_qa_benefactor,
                    reason=f"помог пройти {dept or 'задание'}",
                    dept=dept,
                )
            except Exception as _ge:
                print(f"[LIFECYCLE] ⚠  gratitude: {_ge}")"""
)


# ─── КОСТЫЛЬ _find_agent_zone ─────────────────────────────────────────

print("\n[КОСТЫЛЬ] _find_agent_zone: сканируем")
found = []
for f in (ROOT / "studio").rglob("*.py"):
    try:
        txt = f.read_text(encoding="utf-8")
        if "_find_agent_zone" in txt and not f.name.endswith(".bak"):
            found.append(f)
    except Exception:
        pass

if not found:
    print("  ~ _find_agent_zone не найден — возможно уже устранён")
else:
    for f in found:
        print(f"  Найден в: {f}")
        txt = f.read_text(encoding="utf-8")
        idx = txt.find("_find_agent_zone")
        print(f"  Контекст:\n{txt[max(0,idx-150):idx+250]}\n")
    print("  ⚠  Требует ручного анализа контекста перед заменой")


print("\n" + "="*55)
print("Готово. Проверь статусы выше.")
print("Бэкапы: файлы с суффиксом .bak_yellow_*")
print("="*55)
