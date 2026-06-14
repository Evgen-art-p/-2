# patch_market_data_context.py
# Запускать из корня проекта:
#   python patch_market_data_context.py
#
# Патчит studio/workshop/pipeline.py:
#   Добавляет блок chain_data в build_agent_context — сразу перед
#   "ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ".
#   Агенты trading-цеха получат market_data, atlas_digest, trade_setup
#   и весь остальной chain_data в своём контексте.

from pathlib import Path
import shutil
from datetime import datetime
import json

TARGET = Path("studio/workshop/pipeline.py")

# Якорь — вставляем перед этим блоком
OLD = (
    "    # ══ ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ ════════════════════════\n"
    "    if files_ctx:\n"
    "        context += files_ctx + \"\\n\\n\"\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)

NEW = (
    "    # ══ CHAIN DATA (market_data и другие данные цеха) ══════════\n"
    "    # Форматируем chain_data в текст для агентов.\n"
    "    # trading-цех кладёт сюда market_data, atlas_digest, trade_setup и т.д.\n"
    "    _chain = state.get(\"chain_data\", {})\n"
    "    if _chain:\n"
    "        _md = _chain.get(\"market_data\")\n"
    "        if _md:\n"
    "            # Форматируем market_data читаемо для промпта\n"
    "            _md_lines = [\"=== MARKET DATA ===\"]\n"
    "            _md_lines.append(f\"symbol: {_md.get('symbol', '')}\")\n"
    "            _md_lines.append(f\"timeframe: {_md.get('timeframe', '')}\")\n"
    "            _md_lines.append(f\"bar_time: {_md.get('bar_time', '')}\")\n"
    "            # price\n"
    "            _p = _md.get(\"price\", {})\n"
    "            if _p:\n"
    "                _md_lines.append(\n"
    "                    f\"price: open={_p.get('open')} high={_p.get('high')} \"\n"
    "                    f\"low={_p.get('low')} close={_p.get('close')}\"\n"
    "                )\n"
    "            # alligator\n"
    "            _al = _md.get(\"alligator\", {})\n"
    "            if _al:\n"
    "                _al_state = (\n"
    "                    \"sleeping\" if _al.get(\"sleeping\") else\n"
    "                    \"mature\" if _al.get(\"mature\") else\n"
    "                    f\"open {_al.get('bars_open', 0)} bars\"\n"
    "                )\n"
    "                _md_lines.append(\n"
    "                    f\"alligator: jaw={_al.get('jaw')} teeth={_al.get('teeth')} \"\n"
    "                    f\"lips={_al.get('lips')} state={_al_state}\"\n"
    "                )\n"
    "            # ao\n"
    "            _ao = _md.get(\"ao\", {})\n"
    "            if _ao:\n"
    "                _md_lines.append(\n"
    "                    f\"ao: value={_ao.get('value')} prev={_ao.get('prev_value')} \"\n"
    "                    f\"direction={_ao.get('direction')} crossed_zero={_ao.get('crossed_zero')}\"\n"
    "                )\n"
    "                # ao history для дивергенций\n"
    "                if _ao.get(\"history\"):\n"
    "                    _md_lines.append(f\"ao.history (last 10): {_ao['history'][-10:]}\")\n"
    "                if _ao.get(\"pivots\"):\n"
    "                    _md_lines.append(f\"ao.pivots: {_ao['pivots'][-5:]}\")\n"
    "            # ac\n"
    "            _ac = _md.get(\"ac\", {})\n"
    "            if _ac:\n"
    "                _md_lines.append(\n"
    "                    f\"ac: value={_ac.get('value')} direction={_ac.get('direction')}\"\n"
    "                )\n"
    "            # mfi\n"
    "            _mfi = _md.get(\"mfi\", {})\n"
    "            if _mfi:\n"
    "                _md_lines.append(\n"
    "                    f\"mfi: type={_mfi.get('type')} volume={_mfi.get('volume')}\"\n"
    "                )\n"
    "            # fractals\n"
    "            _fr = _md.get(\"fractals\", {})\n"
    "            if _fr:\n"
    "                _md_lines.append(\n"
    "                    f\"fractals: up={_fr.get('count_up')} down={_fr.get('count_down')}\"\n"
    "                )\n"
    "                if _fr.get(\"last_up\"):\n"
    "                    _md_lines.append(f\"fractals.last_up: {_fr['last_up']}\")\n"
    "                if _fr.get(\"last_down\"):\n"
    "                    _md_lines.append(f\"fractals.last_down: {_fr['last_down']}\")\n"
    "            # divergence / exit_bell\n"
    "            if _md.get(\"divergence_ao\"):\n"
    "                _md_lines.append(\"divergence_ao: TRUE (бычья дивергенция AO — Точка Ноль!)\")\n"
    "            if _md.get(\"exit_bell\"):\n"
    "                _md_lines.append(\"exit_bell: TRUE (импульс выдохся — звонок выхода)\")\n"
    "            _md_lines.append(\"=== END MARKET DATA ===\")\n"
    "            context += \"\\n\".join(_md_lines) + \"\\n\\n\"\n"
    "            print(f\"[CONTEXT] {worker_id}: market_data инжектирован ({len(_md_lines)} строк)\")\n"
    "\n"
    "        # Остальные ключи chain_data (кроме market_data — уже выше)\n"
    "        _chain_other = {k: v for k, v in _chain.items() if k != \"market_data\"}\n"
    "        if _chain_other:\n"
    "            try:\n"
    "                _chain_str = json.dumps(_chain_other, ensure_ascii=False, indent=2)\n"
    "                context += (\n"
    "                    f\"=== CHAIN DATA ===\\n{_chain_str}\\n=== END CHAIN DATA ===\\n\\n\"\n"
    "                )\n"
    "            except Exception:\n"
    "                pass\n"
    "\n"
    "    # ══ ФАЙЛЫ И ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ ════════════════════════\n"
    "    if files_ctx:\n"
    "        context += files_ctx + \"\\n\\n\"\n"
    "    if previous_output:\n"
    "        context += f\"=== РЕЗУЛЬТАТЫ ПРЕДЫДУЩИХ ЭТАПОВ ===\\n{previous_output}\\n\""
)


def main():
    if not TARGET.exists():
        print(f"❌ Файл не найден: {TARGET}")
        print("   Убедись что запускаешь из корня проекта.")
        return

    text = TARGET.read_text(encoding="utf-8")

    if OLD not in text:
        print("⚠️  Якорь не найден — возможно pipeline.py уже изменён.")
        print("   Патч не применён.")
        return

    # Проверяем что json уже импортирован
    if "import json" not in text:
        print("⚠️  'import json' не найден в pipeline.py — добавь вручную в начало файла.")
        return

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_suffix(f".py.bak_{ts}")
    shutil.copy2(TARGET, backup)
    print(f"💾 Бэкап: {backup}")

    patched = text.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    print(f"✅ Патч применён: {TARGET}")
    print("   + chain_data (market_data + остальное) теперь идёт в контекст агентов")
    print()
    print("Теперь запускай:")
    print("  python run_council.py EURUSDDaily.csv EURUSDDaily D1 --bars 50")


if __name__ == "__main__":
    main()
