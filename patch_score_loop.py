"""
patch_score_loop.py
===================
Замыкает петлю экономики для TURBO и video_long.

1. Патчит turbo/hooks.py       → task_score + Strategy Registry после A05
2. Патчит video_long/hooks.py  → то же после Боба (A12)
3. Обновляет TURBO_RULES.md    → v4.2, раздел 17
4. Обновляет LONG_RULES.md     → v4.7, раздел 8

Запуск: python patch_score_loop.py
"""

import shutil
import subprocess
from pathlib import Path

TURBO_HOOKS = Path("studio/modules/turbo/hooks.py")
LONG_HOOKS  = Path("studio/modules/video_long/hooks.py")
TURBO_RULES = Path("studio/modules/turbo/TURBO_RULES.md")
LONG_RULES  = Path("studio/modules/video_long/LONG_RULES.md")


def make_loop_code(agents_list, slot_id, qa_label, first_agent_key, first_agent_id):
    """Генерирует код замыкания петли без .format() чтобы не конфликтовать с фигурными скобками."""
    return r"""
        # ── ЗАМЫКАНИЕ ПЕТЛИ: task_score + Strategy Registry ──────────
        # Правило для всех цехов: QA-агент записывает реальный score рана.
        # billing_ledger получает quality, не только cost.
        # Strategy Registry накапливает выжившие стратегии.

        # 1. task_score в billing_ledger
        try:
            from studio.billing_ledger import record as _bl_record
            _loop_agents = """ + repr(agents_list) + r"""
            for _aid in _loop_agents:
                _bl_record(
                    agent_id=_aid,
                    slot_id=slot_id,
                    model=slot_id + "/finalize",
                    prompt_tokens=0,
                    completion_tokens=0,
                    call_type="finalize",
                    task_score=score,
                )
            print(f"[""" + qa_label + r"""] 📊 task_score={score} → ledger ({len(_loop_agents)} агентов)")
        except Exception as _le:
            print(f"[""" + qa_label + r"""] ⚠ ledger task_score: {_le}")

        # 2. Strategy Registry
        try:
            import json as _rj
            from datetime import datetime as _rdt
            _reg_path = Path("studio/strategy_registry.json")
            _reg = {}
            if _reg_path.exists():
                try:
                    _reg = _rj.loads(_reg_path.read_text(encoding="utf-8"))
                except Exception:
                    _reg = {}

            _chain   = state.get("chain_data", {})
            _first   = _chain.get(""" + repr(first_agent_key) + r""", {})
            _summary = (
                _first.get("strategy_summary", "")
                or _first.get("brief", "")
                or _first.get("concept", "")
                or _first.get("synopsis", "")
                or "без описания"
            )[:200]

            _slots    = _reg.setdefault("slots", {})
            _slot_reg = _slots.setdefault(slot_id, {})
            _fa_list  = _slot_reg.setdefault(""" + repr(first_agent_id) + r""", [])

            _existing = next(
                (s for s in _fa_list if s.get("summary", "")[:60] == _summary[:60]),
                None
            )
            if _existing:
                if score >= 6.0:
                    _existing["wins"] = _existing.get("wins", 0) + 1
                _existing["last_score"] = score
                _existing["last_run"]   = _rdt.now().isoformat()
            else:
                _fa_list.append({
                    "ts":           _rdt.now().isoformat(),
                    "score":        score,
                    "last_score":   score,
                    "last_run":     _rdt.now().isoformat(),
                    "run_type":     slot_id,
                    "summary":      _summary,
                    "wins":         1 if score >= 6.0 else 0,
                    "transferable": False,
                })

            _total_wins = sum(
                s.get("wins", 0)
                for _sl in _reg.get("slots", {}).values()
                for _elist in _sl.values()
                for s in _elist
            )
            _reg["total_wins"] = _total_wins
            _reg["updated_at"] = _rdt.now().isoformat()
            _reg.setdefault("version", 1)

            _reg_path.write_text(
                _rj.dumps(_reg, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            _wm = "🏆" if score >= 6.0 else "📝"
            print(f"[""" + qa_label + r"""] {_wm} Registry: score={score}, wins={_total_wins}")
        except Exception as _re:
            print(f"[""" + qa_label + r"""] ⚠ Strategy Registry: {_re}")
"""


LOOP_RULE_TURBO = """
---

## 17. ЗАМЫКАНИЕ ПЕТЛИ — ЗАКОН ДЛЯ ВСЕХ ЦЕХОВ

**QA-агент (финализатор) обязан после каждого рана:**

1. Записать `task_score` в `billing_ledger` для каждого агента цепочки.
2. Обновить `strategy_registry.json` — банк выживших стратегий.

**Зачем:**
- Кей (Совет резидентов) видит не просто $cost, но и quality.
- Strategy Registry знает какие стратегии работают.
- После 10+ ранов система отличает сильные паттерны от слабых.

**Это правило обязательно для всех 11 цехов.**
Каждый новый цех наследует этот механизм в своём `hooks.py`.

*Добавлено: v4.2 | 2026-06-04*
"""

LOOP_RULE_LONG = """
---

## 8. ЗАМЫКАНИЕ ПЕТЛИ — ЗАКОН ДЛЯ ВСЕХ ЦЕХОВ

**QA-агент Боб (A12) обязан после каждого рана:**

1. Записать `task_score` в `billing_ledger` для каждого агента A01–A12.
2. Обновить `strategy_registry.json` — банк выживших стратегий.

**Зачем:**
- Кей (Совет резидентов) видит не просто $cost, но и quality.
- Strategy Registry знает какие стратегии Адама выживают.
- После 10+ ранов система отличает сильные паттерны от слабых.

**Это правило обязательно для всех 11 цехов.**

*Добавлено: v4.7 | 2026-06-04*
"""


def patch_hooks(hooks_path, agents_list, slot_id, qa_label, first_agent_key, first_agent_id):
    if not hooks_path.exists():
        print(f"  ❌ {hooks_path} не найден")
        return False

    src = hooks_path.read_text(encoding="utf-8")

    if "ЗАМЫКАНИЕ ПЕТЛИ" in src:
        print(f"  ⚠  {hooks_path.name} — патч уже применён")
        return True

    code = make_loop_code(agents_list, slot_id, qa_label, first_agent_key, first_agent_id)

    # Ищем: score = round(min(10.0, score), 2)  потом строку с agents =
    import re
    pattern = re.compile(
        r'([ \t]*score\s*=\s*round\(min\(10\.0,\s*score\),\s*2\))'
        r'(\s*\n[ \t]*agents\s*=\s*\[)',
        re.MULTILINE
    )
    m = pattern.search(src)
    if m:
        insert_at = m.end(1)
        src = src[:insert_at] + "\n" + code + src[insert_at:]
        hooks_path.write_text(src, encoding="utf-8")
        print(f"  ✅ {hooks_path.name} — патч применён (после score=round)")
        return True

    # Fallback: ищем ministry.record_outcome
    ministry_idx = src.find("ministry.record_outcome")
    if ministry_idx != -1:
        line_start = src.rfind("\n", 0, ministry_idx) + 1
        src = src[:line_start] + code.rstrip() + "\n" + src[line_start:]
        hooks_path.write_text(src, encoding="utf-8")
        print(f"  ✅ {hooks_path.name} — патч применён (перед ministry)")
        return True

    print(f"  ❌ {hooks_path.name} — маркер не найден")
    return False


def update_rules(rules_path, new_section, old_version, new_version):
    if not rules_path.exists():
        print(f"  ❌ {rules_path} не найден")
        return False

    src = rules_path.read_text(encoding="utf-8")

    if "ЗАМЫКАНИЕ ПЕТЛИ" in src:
        print(f"  ⚠  {rules_path.name} — раздел уже есть")
        return True

    src = src.replace(old_version, new_version)
    src = src.rstrip() + "\n" + new_section

    rules_path.write_text(src, encoding="utf-8")
    print(f"  ✅ {rules_path.name} → {new_version}")
    return True


def check_syntax(path):
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ {path.name} — синтаксис OK")
        return True
    else:
        print(f"  ❌ {path.name} — ошибка:\n{result.stderr}")
        return False


def main():
    print("\n🔗 ПАТЧ: Замыкание петли — TURBO + video_long")
    print("=" * 52)

    for path in [TURBO_HOOKS, LONG_HOOKS]:
        if path.exists():
            bak = path.with_suffix(".py.bak")
            shutil.copy2(path, bak)
            print(f"📦 Бэкап: {bak}")

    print("\n[1/4] Патч turbo/hooks.py...")
    turbo_ok = patch_hooks(
        TURBO_HOOKS,
        agents_list=["A01", "A02", "A03", "A04", "A05"],
        slot_id="turbo",
        qa_label="TURBO A05",
        first_agent_key="stella_strategy",
        first_agent_id="a01",
    )

    print("\n[2/4] Патч video_long/hooks.py...")
    long_ok = patch_hooks(
        LONG_HOOKS,
        agents_list=["A01","A02","A03","A04","A05","A06","A07","A08","A09","A10","A11","A12"],
        slot_id="video_long",
        qa_label="LONG BOB",
        first_agent_key="adam_episode",
        first_agent_id="a01",
    )

    print("\n[3/4] Обновление Rules...")
    update_rules(TURBO_RULES, LOOP_RULE_TURBO,
                 "**Версия:** 4.1", "**Версия:** 4.2")
    update_rules(LONG_RULES, LOOP_RULE_LONG,
                 "**Версия:** 4.6", "**Версия:** 4.7")

    print("\n[4/4] Синтаксис...")
    for path, ok in [(TURBO_HOOKS, turbo_ok), (LONG_HOOKS, long_ok)]:
        if ok and path.exists():
            if not check_syntax(path):
                bak = path.with_suffix(".py.bak")
                if bak.exists():
                    shutil.copy2(bak, path)
                    print(f"  ↩ {path.name} восстановлен из бэкапа")

    print("\n" + "=" * 52)
    print("Готово.")
    print()
    print("  turbo/hooks.py      → task_score + Registry после A05")
    print("  video_long/hooks.py → task_score + Registry после Боба")
    print("  TURBO_RULES.md      → v4.2, раздел 17")
    print("  LONG_RULES.md       → v4.7, раздел 8")
    print()
    print("Закон записан в Rules — все будущие цеха наследуют.")


if __name__ == "__main__":
    main()
