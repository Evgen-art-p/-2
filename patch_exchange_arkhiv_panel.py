#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# patch_exchange_arkhiv_panel.py
# ПРИБОРЫ: табличка Архивариуса (A05) в правой панели Биржи.
#
# Спринт 45 · 2026-06-18 · Брат (Claude) · ШАГ 2
#
# ЧТО ДЕЛАЕТ:
#   Вешает Архивариусу свою приборную панель — как у Моржа/Паникёра/
#   Ганса. При клике на пузырёк 📚 справа показывает:
#     СКЛАД      — sample_size похожих случаев (закрыто N)
#     УДАЧА      — success_rate (доля прибыльных среди закрытых)
#     УВЕРЕННОСТЬ— arkhiv_confidence (LOW/MEDIUM/HIGH, цвет-светофор)
#     ПРИЧИНА    — top_failure_reason (частая причина потерь)
#     снизу      — статистика прогонов (взглядов/HIGH/MEDIUM/LOW/пусто)
#   Все числа — из его signal/digest (КОД посчитал, не выдумано).
#   Пустой Атлас → честная заглушка в духе Архивариуса.
#
#   Плюс ПОДМЕТАНИЕ: дописывает arkhiv-поля в стартовый словарь state
#   (как у соседей morj_/panic_/hans_last_run) — для порядка.
#
# ЗАКОН СТИЛЯ: ни одной новой инлайн-СSS-философии — копия раскладки
#   приборов Ганса (тот же шрифт, отступы, рамки). Цвета confidence
#   как у светофора Паникёра: HIGH=зелёный, MEDIUM=жёлтый, LOW=серый.
#
# ИДЕМПОТЕНТНОСТЬ: маркер EXCHANGE_ARKHIV_PANEL. Повтор — no-op.
# БЭКАП: ui_exchange.py.bak_<timestamp>.
# ─────────────────────────────────────────────────────────────

import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path("studio/economy/ui_exchange.py")
MARKER = "EXCHANGE_ARKHIV_PANEL"

# ── ЯКОРЬ 1: блок приборов Ганса заканчивается на своём `return`.
# Вставляем блок Архивариуса СРАЗУ после него (перед блоком Искры —
# «Только для Искры показываем её приборы»). Берём уникальный хвост
# панели Ганса: закрывающий комментарий + return ветки A04.
ANCHOR_PANEL = (
    '        # Только для Искры показываем её приборы; для других — заглушка.\n'
    '        if state["active_agent"] != "A01":\n'
)

PANEL_BLOCK = '''        # ─── Приборы Архивариуса (A05): склад + удача + уверенность ───  # EXCHANGE_ARKHIV_PANEL
        if state["active_agent"] == "A05":
            asig = state.get("arkhiv_signal", {})
            ast  = state.get("arkhiv_stats", {})
            adg  = state.get("arkhiv_digest", {})
            if not asig and not adg:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Архивариус ещё не листал Атлас — '
                            'нажми РЫНОК (нужен сигнал Искры)</div>')
                return
            sample = asig.get("sample_size", adg.get("sample_size", 0))
            closed = adg.get("closed_trades", "—")
            success = asig.get("success_rate", adg.get("success_rate"))
            success_txt = f"{round(success*100)}%" if isinstance(success, (int, float)) else "—"
            conf = asig.get("arkhiv_confidence", adg.get("arkhiv_confidence", "—"))
            conf_color = {"HIGH": "#00ff88", "MEDIUM": "#ffb400",
                          "LOW": "rgba(255,255,255,0.45)"}.get(conf, "rgba(255,255,255,0.45)")
            reason = asig.get("top_failure_reason", adg.get("top_failure_reason", "—")) or "—"
            # пустой склад — особый честный вид
            empty = (sample == 0)
            sample_color = "rgba(255,255,255,0.4)" if empty else "rgba(0,204,255,0.9)"
            sample_txt = "пусто — первый случай" if empty else f"{sample} (закрыто {closed})"
            with stats_ref["element"]:
                ui.html(f\'\'\'
                <div style="padding:10px 12px; font-family:\\\'JetBrains Mono\\\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">СКЛАД</span>
                    <span style="color:{sample_color}; font-size:11px; font-weight:700;">{sample_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">УДАЧА</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{success_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">УВЕРЕННОСТЬ</span>
                    <span style="color:{conf_color}; font-size:11px; font-weight:700;">{conf}</span>
                  </div>
                  <div style="margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ЧАСТАЯ ПРИЧИНА ПОТЕРЬ</span>
                    <div style="color:rgba(255,255,255,0.7); font-size:10px; font-style:italic;
                                margin-top:3px; line-height:1.4;">«{reason}»</div>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    взглядов: {ast.get("runs",0)} ·
                    HIGH: {ast.get("high",0)} ·
                    MEDIUM: {ast.get("medium",0)} ·
                    LOW: {ast.get("low",0)} ·
                    пусто: {ast.get("empty",0)}
                  </div>
                </div>
                \'\'\')
            return

'''


def main():
    if not TARGET.exists():
        print(f"❌ Не найден {TARGET}. Запусти из корня репозитория студии.")
        return

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"✅ Маркер {MARKER} уже в файле — патч применён ранее. Ничего не делаю.")
        return

    if ANCHOR_PANEL not in src:
        print("❌ Якорь (начало блока Искры в приборах) не найден.")
        print("   Файл изменился — не вставляю вслепую. Покажи ui_exchange.py.")
        return

    # ── 1. Вставляем панель Архивариуса ПЕРЕД блоком Искры ──
    new_src = src.replace(ANCHOR_PANEL, PANEL_BLOCK + ANCHOR_PANEL, 1)

    # ── 2. Подметание: дописываем arkhiv-поля в стартовый state ──
    # Якорь — строка hans_last_run в инициализации state.
    state_anchor = '        "hans_last_run": None,     # рабочая память Ганса для чата\n'
    if state_anchor in new_src:
        state_addition = (
            state_anchor +
            '        "arkhiv_last_run": None,   # рабочая память Архивариуса для чата\n'
            '        "arkhiv_signal": {},       # последний signal Архивариуса → приборы\n'
            '        "arkhiv_stats": {},        # статистика прогонов Архивариуса\n'
            '        "arkhiv_digest": {},       # выжимка из Атласа (digest)\n'
        )
        new_src = new_src.replace(state_anchor, state_addition, 1)
        swept = True
    else:
        swept = False

    if new_src == src:
        print("❌ Замена не сработала. Стоп.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(TARGET.suffix + f".bak_{ts}")
    shutil.copy2(TARGET, backup)

    TARGET.write_text(new_src, encoding="utf-8")

    # Синтаксис
    import py_compile
    try:
        py_compile.compile(str(TARGET), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"❌ СИНТАКСИС СЛОМАН после патча: {e}")
        print(f"   Откатываю из бэкапа {backup.name}")
        shutil.copy2(backup, TARGET)
        return

    print(f"✅ Приборы Архивариуса повешены (пузырёк 📚 → табличка справа).")
    print(f"   Подметание state: {'да' if swept else 'якорь не найден — пропущено'}")
    print(f"   Бэкап: {backup.name}")
    print(f"   Маркер: {MARKER}")
    print()
    print("   Показывает: склад · удача · уверенность · причина потерь · статистика.")
    print("   Пустой Атлас → честная заглушка «первый случай».")


if __name__ == "__main__":
    main()
