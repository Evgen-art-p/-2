# -*- coding: utf-8 -*-
# run_council.py
# ─────────────────────────────────────────────────────────────
# СТЕНД для прогона Военного Совета на куске CSV.
#
# Что делает:
#   1) Берёт CSV с историей цены (формат MT5).
#   2) Запускает цех trading на N последних барах
#      (один прогон — Совет смотрит на финальное состояние,
#       Искра/Морж/Паникёр/Ганс/Архивариус + параллельный Трибунал).
#   3) Собирает всё, что сказал каждый агент, через колбэки.
#   4) Записывает протокол заседания в markdown-файл рядом с CSV.
#
# Использование (из корня репо):
#   python run_council.py путь/к/csv.csv XAUUSD H4
#   python run_council.py путь/к/csv.csv XAUUSD H4 --bars 200
#
# Результат:
#   рядом с входным CSV появится council_<symbol>_<tf>_<timestamp>.md
#   открываешь в VSCode — листаешь, читаешь протокол.
#
# ВАЖНО: это РЕАЛЬНЫЙ прогон Совета — LLM-вызовы происходят на самом
# деле. Каждый бар = пять-восемь LLM-вызовов (Искра, Морж, Паникёр,
# Ганс, Архивариус, трое трейдеров параллельно, Исполнитель).
# Это медленно и стоит токенов. Начинай с малого: --bars 50.
# ─────────────────────────────────────────────────────────────

import sys
import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path

# Гарантируем что корень репо в sys.path (для импорта studio.*)
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from studio.cartridge import run_cartridge, PipelineCallbacks


# ════════════════════════════════════════════════════════════
# ПРОТОКОЛЬНЫЕ КОЛБЭКИ — слушают и записывают всё что говорит цех
# ════════════════════════════════════════════════════════════

class ProtocolCallbacks(PipelineCallbacks):
    """
    Наследует базовый интерфейс колбэков, переопределяет нужные,
    собирает события в self.events для последующей записи протокола.
    """
    def __init__(self):
        self.events: list[dict] = []
        self.agent_outputs: dict[str, dict] = {}  # worker_id → последний результат

    def _push(self, kind: str, **payload):
        self.events.append({
            "ts":   datetime.now().isoformat(),
            "kind": kind,
            **payload,
        })

    async def on_pipeline_start(self, slot_id: str, run_type: str):
        self._push("pipeline_start", slot_id=slot_id, run_type=run_type)
        print(f"[COUNCIL] ▶ Совет начал заседание (slot={slot_id})")

    async def on_pipeline_done(self, slot_id: str, results: dict):
        self._push("pipeline_done", results_count=len(results))
        print(f"[COUNCIL] ✅ Заседание завершено, агентов выступило: {len(results)}")

    async def on_pipeline_error(self, slot_id: str, error: str):
        self._push("pipeline_error", error=error)
        print(f"[COUNCIL] ❌ Ошибка заседания: {error}")

    async def on_agent_start(self, slot_id: str, worker_id: str,
                              label: str, phase: str):
        self._push("agent_start", worker_id=worker_id, label=label, phase=phase)
        print(f"[COUNCIL]   → {worker_id} {label} говорит...")

    async def on_agent_done(self, slot_id, worker_id, label,
                             human_text, meta, ghost_ids=None):
        # meta содержит my_output (signal-блок CHAIN_CONTRACT)
        my_output = (meta.get("my_output") if isinstance(meta, dict) else None) or {}
        self.agent_outputs[worker_id] = {
            "label":     label,
            "narrative": human_text,
            "signal":    my_output,
        }
        self._push("agent_done", worker_id=worker_id, label=label,
                   narrative=human_text, signal=my_output)
        # Печатаем короткую сводку в терминал
        verdict_key = next((k for k in my_output if "verdict" in k.lower()), None)
        verdict = my_output.get(verdict_key) if verdict_key else None
        if verdict:
            print(f"[COUNCIL]     {worker_id}: {verdict}")
        else:
            print(f"[COUNCIL]     {worker_id} ответил ({len(human_text)} симв.)")

    async def on_agent_error(self, slot_id, worker_id, error):
        self._push("agent_error", worker_id=worker_id, error=str(error))
        print(f"[COUNCIL]   ⚠ {worker_id} упал: {error}")

    async def on_parallel_start(self, slot_id, agent_ids):
        self._push("parallel_start", agent_ids=list(agent_ids))
        print(f"[COUNCIL]   ⚖ Трибунал говорит параллельно: {agent_ids}")

    async def on_parallel_done(self, slot_id, agent_ids, results):
        self._push("parallel_done", agent_ids=list(agent_ids))

    async def on_status(self, slot_id, message, level="info"):
        # Эти статусы скорее всего шумные, в протокол не льём, но в лог да
        if level in ("warn", "error"):
            self._push("status", message=message, level=level)


# ════════════════════════════════════════════════════════════
# ФОРМАТТЕР — превращает события в читаемый markdown
# ════════════════════════════════════════════════════════════

# Понятные имена и иконки для трейдинг-агентов
AGENT_ICONS = {
    "A01": "🔥", "A02": "🐋", "A03": "🐺", "A04": "🪝",
    "A05": "📚", "A06": "🥶", "A07": "🔥", "A08": "🧊", "A09": "🎯",
}
AGENT_NAMES = {
    "A01": "Искра",      "A02": "Морж",         "A03": "Паникёр",
    "A04": "Ганс",       "A05": "Архивариус",   "A06": "Брут",
    "A07": "Авантюрист", "A08": "Консерватор",  "A09": "Исполнитель",
}

def _trim(text: str, max_chars: int = 600) -> str:
    """Подрезаем длинный narrative до читабельного размера."""
    if not text:
        return "_(молчит)_"
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def format_protocol(callbacks: ProtocolCallbacks, meta: dict) -> str:
    """Собирает markdown-протокол заседания из событий."""
    md = []
    md.append(f"# Протокол заседания Военного Совета")
    md.append(f"")
    md.append(f"**Дата прогона:** {meta['run_date']}")
    md.append(f"**Актив:** {meta['symbol']} · **Таймфрейм:** {meta['timeframe']}")
    md.append(f"**CSV-источник:** `{meta['csv_path']}`")
    md.append(f"**Баров взято:** {meta['bars_used']}")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # ── Фаза I — Сенсоры (последовательно) ──
    md.append(f"## ФАЗА I — Сенсоры")
    md.append(f"")
    for aid in ("A01", "A02", "A03", "A04"):
        out = callbacks.agent_outputs.get(aid)
        if not out:
            md.append(f"### {AGENT_ICONS.get(aid,'')} {AGENT_NAMES.get(aid,aid)} ({aid})")
            md.append(f"*(не выступал — возможно, заблокирован GATE)*")
            md.append("")
            continue
        md.append(f"### {AGENT_ICONS.get(aid,'')} {AGENT_NAMES.get(aid,aid)} ({aid})")
        md.append(f"")
        md.append(f"> {_trim(out['narrative'])}")
        md.append(f"")
        if out["signal"]:
            md.append(f"**Сигнал:**")
            md.append(f"```json")
            md.append(json.dumps(out["signal"], ensure_ascii=False, indent=2))
            md.append(f"```")
            md.append("")

    # ── Фаза II — Память ──
    md.append(f"## ФАЗА II — Память")
    md.append(f"")
    out_a05 = callbacks.agent_outputs.get("A05")
    if out_a05:
        md.append(f"### 📚 Архивариус (A05)")
        md.append(f"")
        md.append(f"> {_trim(out_a05['narrative'])}")
        md.append(f"")
        if out_a05["signal"]:
            md.append(f"```json")
            md.append(json.dumps(out_a05["signal"], ensure_ascii=False, indent=2))
            md.append(f"```")
            md.append("")

    # ── Фаза III — ТРИБУНАЛ (параллельно!) ──
    md.append(f"## ФАЗА III — ⚖ ТРИБУНАЛ (трое говорят одновременно)")
    md.append(f"")
    md.append(f"_Один рынок. Одна книга. Три характера. Три ответа._")
    md.append(f"")
    for aid in ("A06", "A07", "A08"):
        out = callbacks.agent_outputs.get(aid)
        md.append(f"### {AGENT_ICONS.get(aid,'')} {AGENT_NAMES.get(aid,aid)} ({aid})")
        if not out:
            md.append(f"*(не выступал)*")
            md.append("")
            continue
        # Достаём вердикт и причину
        signal = out["signal"] or {}
        verdict_key = next((k for k in signal if "verdict" in k.lower()), None)
        reason_key  = next((k for k in signal if "reason"  in k.lower()), None)
        verdict = signal.get(verdict_key, "—") if verdict_key else "—"
        reason  = signal.get(reason_key,  "—") if reason_key  else "—"
        md.append(f"")
        md.append(f"**Вердикт:** `{verdict}` · **Причина:** `{reason}`")
        md.append(f"")
        md.append(f"> {_trim(out['narrative'])}")
        md.append(f"")
        if signal:
            md.append(f"```json")
            md.append(json.dumps(signal, ensure_ascii=False, indent=2))
            md.append(f"```")
            md.append("")

    # ── Фаза IV — Исполнитель ──
    md.append(f"## ФАЗА IV — Исполнение")
    md.append(f"")
    out_a09 = callbacks.agent_outputs.get("A09")
    if out_a09:
        md.append(f"### 🎯 Исполнитель (A09)")
        md.append(f"")
        md.append(f"> {_trim(out_a09['narrative'])}")
        md.append(f"")
        if out_a09["signal"]:
            md.append(f"```json")
            md.append(json.dumps(out_a09["signal"], ensure_ascii=False, indent=2))
            md.append(f"```")
            md.append("")
    else:
        md.append(f"*Исполнитель не выступал — возможно, хард-стоп после трибунала.*")
        md.append("")

    # ── Итоги ──
    md.append(f"---")
    md.append(f"")
    md.append(f"## Итоги заседания")
    md.append(f"")
    md.append(f"- Событий всего: **{len(callbacks.events)}**")
    md.append(f"- Агентов выступило: **{len(callbacks.agent_outputs)}**")

    # Трибунал — сводка по вердиктам
    tribunal = []
    for aid in ("A06", "A07", "A08"):
        out = callbacks.agent_outputs.get(aid)
        if not out:
            tribunal.append(f"  - {AGENT_NAMES[aid]}: _(нет ответа)_")
            continue
        signal = out["signal"] or {}
        verdict_key = next((k for k in signal if "verdict" in k.lower()), None)
        verdict = signal.get(verdict_key, "?") if verdict_key else "?"
        tribunal.append(f"  - {AGENT_NAMES[aid]}: **{verdict}**")
    if tribunal:
        md.append(f"- Трибунал:")
        md.extend(tribunal)

    md.append(f"")
    md.append(f"---")
    md.append(f"")
    md.append(f"*Протокол собран автоматически из колбэков `cartridge.run_cartridge`.*")
    md.append(f"*Это реальные ответы LLM-агентов — не сценарий.*")
    return "\n".join(md)


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ — собрать state, позвать cartridge, записать протокол
# ════════════════════════════════════════════════════════════

async def run_council(csv_path: Path, symbol: str, timeframe: str,
                      bars_limit: int) -> Path:
    print(f"\n{'═' * 60}")
    print(f"  ВОЕННЫЙ СОВЕТ — {symbol} {timeframe}")
    print(f"  CSV: {csv_path}")
    print(f"  Баров: {bars_limit}")
    print(f"{'═' * 60}\n")

    # ── state, который ожидает cartridge ────────────────────
    # active_dept = trading — это и есть выбор картриджа.
    # master_brief — фоновый текст «зачем мы здесь», без него
    # пайплайн жалуется. Делаем минимальный осмысленный.
    state = {
        "active_dept":   "trading",
        "run_type":      "council_test",
        "master_brief":  (
            f"Военный Совет цеха trading заседает по активу {symbol} {timeframe}. "
            f"Прогон-тест на последних {bars_limit} барах истории. "
            f"Это не боевой ордер — это исследование того, как трое расходятся "
            f"в чтении одного и того же рынка."
        ),
        "settings": {
            "csv_path":   str(csv_path),
            "symbol":     symbol,
            "timeframe":  timeframe,
            "bars_limit": bars_limit,
        },
        "chain_data":    {},
        "results":       {},
        "_agent_ids":    [],
    }

    callbacks = ProtocolCallbacks()

    # ── Зовём cartridge ─────────────────────────────────────
    # turbo=True → параллельный запуск Трибунала через asyncio.gather
    # (это уже встроено в cartridge для групп из turbo_parallel manifest).
    try:
        await run_cartridge(
            module_id="trading",
            state=state,
            callbacks=callbacks,
            slot_id="council_test",
            turbo=True,
        )
    except Exception as e:
        print(f"\n[COUNCIL] ❌ Прогон упал: {e}")
        import traceback
        traceback.print_exc()
        # Всё равно сохраняем то, что успели собрать
        callbacks._push("pipeline_crashed", error=str(e))

    # ── Пишем протокол рядом с CSV ──────────────────────────
    out_dir = csv_path.parent
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    protocol_path = out_dir / f"council_{symbol}_{timeframe}_{ts}.md"

    meta = {
        "run_date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol":     symbol,
        "timeframe":  timeframe,
        "csv_path":   str(csv_path),
        "bars_used":  bars_limit,
    }
    protocol_md = format_protocol(callbacks, meta)
    protocol_path.write_text(protocol_md, encoding="utf-8")

    # Сырые события — рядом, для будущего разбора
    events_path = out_dir / f"council_{symbol}_{timeframe}_{ts}_events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for ev in callbacks.events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"\n{'═' * 60}")
    print(f"  📜 Протокол:  {protocol_path}")
    print(f"  📋 События:   {events_path}")
    print(f"{'═' * 60}\n")
    print(f"Открой протокол в VSCode — там расписано кто что сказал.")

    return protocol_path


def main():
    parser = argparse.ArgumentParser(
        description="Стенд: прогнать Военный Совет на куске CSV."
    )
    parser.add_argument("csv_path", help="Путь к CSV (формат MT5).")
    parser.add_argument("symbol",   help="Тикер (XAUUSD, EURUSD, ...).")
    parser.add_argument("timeframe",help="Таймфрейм (H1, H4, D1, ...).")
    parser.add_argument("--bars", type=int, default=200,
                        help="Сколько последних баров взять (по умолчанию 200).")
    args = parser.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        print(f"❌ CSV не найден: {csv_path}")
        sys.exit(1)

    try:
        asyncio.run(run_council(
            csv_path, args.symbol, args.timeframe, args.bars
        ))
    except KeyboardInterrupt:
        print("\n[COUNCIL] прервано пользователем")
        sys.exit(130)


if __name__ == "__main__":
    main()
