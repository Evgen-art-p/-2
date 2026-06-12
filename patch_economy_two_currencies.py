# -*- coding: utf-8 -*-
"""
ПАТЧ · СПРИНТ 44 — «ЗАКОН ДВУХ ВАЛЮТ» (экономика-аудит Брата, одобрено Локой)
==============================================================================

Запускать из корня проекта:  python patch_economy_two_currencies.py
Тестовый прогон:             python patch_economy_two_currencies.py --root <путь>

Что чинит (по аудиту):
  1.  video_long/hooks.py — блок «Замыкание петли» лежал ВНУТРИ docstring
      _bob_record_ministry и никогда не исполнялся. Функция пересобрана.
  2.  Потолок 6.0 теперь честный ВЕЗДЕ:
      - agent_feedback.py: blocks-путь режется потолком (раньше давал до 10);
      - turbo: формула финализатора переведена в шкалу 0–6;
      - video_long / video_shorts: детерминированный chain-score 0–6,
        viral_score из outcome_signal больше НЕ читается (закон §6).
  3.  Закон двух валют:
      - CHAIN (0–6, ремесло): единственный писатель Ministry — pipeline
        после QA (per-agent оценки из feedback.json, source="chain");
      - REAL (0–10, зритель): единственный писатель — Metrics Daemon
        (source="real", честные ключи Axx::slot вместо "{platform}_fal");
      - хуки цехов Ministry больше не трогают (дубли убраны);
      - generous-режим открывает только real-успех.
  4.  Стоимость рана = дельта от старта рана (cartridge ставит метку
      _run_started_ts; billing_ledger.agent_spent_since), а не пожизненная
      сумма агента.
  5.  Прайс: deepseek-v4-pro, fal/Nano Banana 2, elevenlabs, siliconflow/*
      (⚠ суммы-ОЦЕНКИ — проверь тарифы, пометки в коде).
  6.  Strategy Registry: ключ 'a01' → 'A01' во всех хуках + миграция
      strategy_registry.json + регистронезависимое чтение get_strategies.
  7.  cost_intuition v2: ощущение = ROI (стоимость × качество из task_score),
      как в исходной спеке ЭТАПА 2 (outcome_quality).
  8.  Пороги серий/звёзд и DNA-синка перекалиброваны под chain-шкалу 6.0.
  9.  Мелочи: has_music в turbo (читал не тот ключ), пути от BASE_DIR
      в strategy_registry/metrics_daemon, предупреждение про Telegram Bot API.

Каждый файл бэкапится в *.bak_YYYYMMDD_HHMMSS. Патч идемпотентен:
повторный запуск пропускает уже применённые шаги.
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# ИНФРАСТРУКТУРА
# ──────────────────────────────────────────────────────────────────

ROOT = Path(".")
if len(sys.argv) >= 3 and sys.argv[1] == "--root":
    ROOT = Path(sys.argv[2])

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
APPLIED, SKIPPED, FAILED = [], [], []
_backed_up = set()


def _backup(path: Path):
    if str(path) in _backed_up:
        return
    bak = path.with_name(path.name + f".bak_{STAMP}")
    shutil.copy2(path, bak)
    _backed_up.add(str(path))
    print(f"  💾 бэкап: {bak.name}")


def replace_exact(relpath: str, old: str, new: str, tag: str) -> bool:
    """Точная замена уникального фрагмента. Идемпотентно."""
    path = ROOT / relpath
    if not path.exists():
        FAILED.append(f"{tag}: файл не найден {relpath}")
        print(f"  ❌ {tag}: файл не найден {relpath}")
        return False
    text = path.read_text(encoding="utf-8")
    if new in text:
        SKIPPED.append(tag)
        print(f"  ⏭  {tag}: уже применено")
        return True
    cnt = text.count(old)
    if cnt == 0:
        FAILED.append(f"{tag}: фрагмент не найден в {relpath}")
        print(f"  ❌ {tag}: фрагмент не найден (файл отличается от ожидаемого)")
        return False
    if cnt > 1:
        FAILED.append(f"{tag}: фрагмент не уникален ({cnt}) в {relpath}")
        print(f"  ❌ {tag}: фрагмент встречается {cnt} раз — пропускаю")
        return False
    _backup(path)
    path.write_text(text.replace(old, new), encoding="utf-8")
    APPLIED.append(tag)
    print(f"  ✅ {tag}")
    return True


def replace_span(relpath: str, start_marker: str, end_marker: str,
                 new_code: str, tag: str, idempotency_key: str) -> bool:
    """Замена блока от start_marker (включительно) до end_marker (не вкл.)."""
    path = ROOT / relpath
    if not path.exists():
        FAILED.append(f"{tag}: файл не найден {relpath}")
        print(f"  ❌ {tag}: файл не найден {relpath}")
        return False
    text = path.read_text(encoding="utf-8")
    if idempotency_key in text:
        SKIPPED.append(tag)
        print(f"  ⏭  {tag}: уже применено")
        return True
    i = text.find(start_marker)
    j = text.find(end_marker, i + len(start_marker)) if i != -1 else -1
    if i == -1 or j == -1:
        FAILED.append(f"{tag}: маркеры не найдены в {relpath}")
        print(f"  ❌ {tag}: маркеры не найдены")
        return False
    _backup(path)
    path.write_text(text[:i] + new_code + text[j:], encoding="utf-8")
    APPLIED.append(tag)
    print(f"  ✅ {tag}")
    return True


def write_full(relpath: str, content: str, tag: str, idempotency_key: str) -> bool:
    """Полная перезапись небольшого модуля (с бэкапом)."""
    path = ROOT / relpath
    if not path.exists():
        FAILED.append(f"{tag}: файл не найден {relpath}")
        print(f"  ❌ {tag}: файл не найден {relpath}")
        return False
    if idempotency_key in path.read_text(encoding="utf-8"):
        SKIPPED.append(tag)
        print(f"  ⏭  {tag}: уже применено")
        return True
    _backup(path)
    path.write_text(content, encoding="utf-8")
    APPLIED.append(tag)
    print(f"  ✅ {tag}")
    return True


# ──────────────────────────────────────────────────────────────────
# ШАГ 1 · studio/economy/ministry.py — ДВЕ ВАЛЮТЫ (полная перезапись)
# ──────────────────────────────────────────────────────────────────

MINISTRY_V2 = '''# studio/economy/ministry.py
"""
ЭТАПЫ 6-7 — MINISTRY AS SELECTION · v2.0 «Закон двух валют» (Спринт 44)

Министерство НЕ принимает решения во время рана. Только post-fact:
фиксирует исходы, усиливает успешные паттерны, ослабляет неуспешные,
формирует режим для следующего рана. Естественный отбор, не контроль.

ДВЕ ВАЛЮТЫ (одна шкала 0–10, два источника):
  CHAIN (source="chain", 0–6.0) — ремесло. Детерминированная оценка
    цепочки после QA. Потолок 6.0 = «выжил, сделал по ТЗ, чисто».
    Успех = score >= 6.0 (чистая шестёрка). Провал = score < 4.0.
    Писатель: workshop/pipeline.py после QA-агента.
  REAL (source="real", 0–10) — зритель. Реальные метрики после
    публикации (real_viral_score) или живой QA Шефа.
    Успех = score >= 7.0. Провал = score < 5.0.
    Писатель: economy/metrics_daemon.py.

Манифест: Reward > Punishment. Режим generous открывает ТОЛЬКО
real-успех — скрипт не имеет права чеканить девятки.

Хранение: studio/economy/data/ministry.json
"""

import json
import threading
from pathlib import Path

from studio.config import BASE_DIR

DATA_DIR      = BASE_DIR / "studio" / "economy" / "data"
MINISTRY_FILE = DATA_DIR / "ministry.json"
_lock = threading.Lock()

# Пороги валют
CHAIN_SUCCESS = 6.0   # чистое ремесло
CHAIN_FAIL    = 4.0   # развал цепочки
REAL_SUCCESS  = 7.0   # зритель отозвался
REAL_FAIL     = 5.0   # глухо


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    if not MINISTRY_FILE.exists():
        return {}
    try:
        return json.loads(MINISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _ensure()
    MINISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _key(agent_id: str, slot_id: str) -> str:
    return f"{agent_id}::{slot_id}"


def _empty_record(agent_id: str, slot_id: str) -> dict:
    return {
        "agent_id":       agent_id,
        "slot_id":        slot_id,
        "runs_total":     0,
        "runs_success":   0,
        "runs_fail":      0,
        "cost_success":   0.0,
        "cost_fail":      0.0,
        "score_sum":      0.0,
        "economy_rating": 1.0,
        "mode":           "normal",
        # Спринт 44 — раздельные счётчики валют
        "chain": {"runs": 0, "success": 0, "fail": 0},
        "real":  {"runs": 0, "success": 0, "fail": 0},
        "last_source": "",
        "last_score":  None,
    }


def record_outcome(
    agent_id: str,
    slot_id: str,
    score: float,
    cost_usd: float,
    source: str = "chain",
) -> None:
    """
    Фиксирует исход рана. Вызывается post-fact.

    Args:
        agent_id: ID агента
        slot_id:  ID цеха
        score:    Оценка (chain: 0–6.0; real: 0–10)
        cost_usd: Стоимость РАНА (дельта, не пожизненная сумма!)
        source:   "chain" (pipeline после QA) | "real" (Metrics Daemon)
    """
    if source not in ("chain", "real"):
        source = "chain"

    with _lock:
        data = _load()
        k = _key(agent_id, slot_id)

        if k not in data:
            data[k] = _empty_record(agent_id, slot_id)
        r = data[k]
        # миграция старых записей (до Спринта 44)
        r.setdefault("chain", {"runs": 0, "success": 0, "fail": 0})
        r.setdefault("real",  {"runs": 0, "success": 0, "fail": 0})

        r["runs_total"] += 1
        r["score_sum"]  += score
        r["last_source"] = source
        r["last_score"]  = score

        bucket = r[source]
        bucket["runs"] += 1

        if source == "chain":
            ok, bad = (score >= CHAIN_SUCCESS), (score < CHAIN_FAIL)
        else:
            ok, bad = (score >= REAL_SUCCESS), (score < REAL_FAIL)

        if ok:
            bucket["success"]  += 1
            r["runs_success"]  += 1
            r["cost_success"]  += cost_usd
        elif bad:
            bucket["fail"]     += 1
            r["runs_fail"]     += 1
            r["cost_fail"]     += cost_usd

        r["economy_rating"] = _calc_rating(r)
        r["mode"]           = _calc_mode(r)
        _save(data)


def get_agent_stats(agent_id: str, slot_id: str) -> dict:
    """Статистика агента в цехе."""
    return _load().get(_key(agent_id, slot_id), {
        "agent_id": agent_id, "slot_id": slot_id,
        "runs_total": 0, "economy_rating": 1.0, "mode": "normal",
    })


def get_mode(agent_id: str, slot_id: str) -> str:
    """Режим для следующего рана: frugal | normal | generous."""
    return get_agent_stats(agent_id, slot_id).get("mode", "normal")


def get_prompt_hint(agent_id: str, slot_id: str) -> str:
    """Текстовый блок от Министерства для промпта агента.

    Манифест: «Не наказывай жёстко — получится забитый отличник».
    Frugal говорит про экономику путей, не про слабость агента.
    """
    stats = get_agent_stats(agent_id, slot_id)
    if stats.get("runs_total", 0) < 3:
        return ""  # мало данных — молчим

    mode = stats.get("mode", "normal")
    return {
        "frugal":   "[МИНИСТЕРСТВО] Последние раны не окупались. Ищи более экономные пути: меньше токенов — точнее результат. Качество держи, расход режь.",
        "normal":   "",
        "generous": "[МИНИСТЕРСТВО] Зритель отозвался на твою работу. Можешь позволить себе глубже проработать задачу.",
    }.get(mode, "")


def leaderboard(slot_id: str = None) -> list[dict]:
    """Рейтинг агентов по экономической эффективности."""
    records = list(_load().values())
    if slot_id:
        records = [r for r in records if r.get("slot_id") == slot_id]
    return sorted(records, key=lambda r: r.get("economy_rating", 1.0), reverse=True)


def _calc_rating(r: dict) -> float:
    total = r["runs_total"]
    if total == 0:
        return 1.0
    success_rate = r["runs_success"] / total
    avg_sc = r["cost_success"] / r["runs_success"] if r["runs_success"] else 0.0
    avg_fc = r["cost_fail"]    / r["runs_fail"]    if r["runs_fail"]    else 0.0
    penalty = min(0.3, avg_fc / avg_sc * 0.15) if avg_sc > 0 and avg_fc > 0 else 0.0
    return round(max(0.1, min(2.0, 0.5 + success_rate * 1.5 - penalty)), 3)


def _calc_mode(r: dict) -> str:
    """frugal | normal | generous.

    Закон двух валют: generous открывает ТОЛЬКО real-успех (зритель/Шеф).
    Чистое ремесло (серия chain-6.0) держит normal с высоким рейтингом —
    девятки скрипт не чеканит.
    """
    if r["runs_total"] < 3:
        return "normal"
    rating = r["economy_rating"]
    real_success = r.get("real", {}).get("success", 0)
    if rating >= 1.4 and real_success >= 1:
        return "generous"
    if rating <= 0.6:
        return "frugal"
    return "normal"
'''

# ──────────────────────────────────────────────────────────────────
# ШАГ 2 · studio/billing_ledger.py — прайс + стоимость рана
# ──────────────────────────────────────────────────────────────────

def patch_billing_ledger():
    print("\n── ШАГ 2 · billing_ledger.py: прайс + agent_spent_since ──")

    # 2a. DeepSeek в MODEL_PRICES
    replace_exact(
        "studio/billing_ledger.py",
        '    # Fallback (неизвестная модель)\n'
        '    "_default":                         {"input": 0.50,  "output": 2.00},',
        '    # DeepSeek (основная модель студии) · Спринт 44\n'
        '    # ⚠ ОЦЕНКА — проверь актуальный тариф на openrouter.ai/models\n'
        '    "deepseek/deepseek-v4-pro":         {"input": 0.40,  "output": 1.60},\n'
        '    # Fallback (неизвестная модель)\n'
        '    "_default":                         {"input": 0.50,  "output": 2.00},',
        "ledger: deepseek в прайсе",
    )

    # 2b. Flat-цены + префиксы
    replace_exact(
        "studio/billing_ledger.py",
        'MODEL_FLAT_PRICES: dict[str, float] = {\n'
        '    "fal/Nano Banana Pro":   0.04,\n'
        '    "fal/Seedream 4.5":      0.04,\n'
        '    # Suno, ElevenLabs, SiliconFlow — добавишь позже\n'
        '    # "suno/...":            0.05,\n'
        '    # "elevenlabs/...":      0.03,\n'
        '    # "siliconflow/...":     0.02,\n'
        '}',
        'MODEL_FLAT_PRICES: dict[str, float] = {\n'
        '    "fal/Nano Banana Pro":   0.04,\n'
        '    "fal/Nano Banana 2":     0.04,   # Спринт 44: активная модель писала $0!\n'
        '    "fal/Seedream 4.5":      0.04,\n'
        '    # ⚠ ОЦЕНКИ — сверь с реальными тарифами провайдеров:\n'
        '    "elevenlabs":            0.10,   # музыка/SFX, средний вызов\n'
        '    "ffmpeg":                0.0,    # локальная сборка — бесплатно\n'
        '}\n'
        '\n'
        '# Префиксные flat-цены (модель в леджере с динамическим суффиксом)\n'
        '# Спринт 44: siliconflow/{MODEL_I2V} писал $0 — видео было невидимо для физики\n'
        'MODEL_FLAT_PREFIXES: dict[str, float] = {\n'
        '    "siliconflow/":          0.20,   # ⚠ ОЦЕНКА Wan2.2 I2V 720p — сверь тариф\n'
        '}',
        "ledger: flat-цены медиа + префиксы",
    )

    # 2c. _calc_cost с префиксами и явным правилом нулевых токенов
    replace_exact(
        "studio/billing_ledger.py",
        'def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:\n'
        '    """Считает стоимость в USD по токенам или фиксированной цене."""\n'
        '    # Flat-price модели (FAL, Suno, ElevenLabs и т.д.)\n'
        '    if model in MODEL_FLAT_PRICES:\n'
        '        return MODEL_FLAT_PRICES[model]\n'
        '    # Per-token модели\n'
        '    prices = MODEL_PRICES.get(model, MODEL_PRICES["_default"])',
        'def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:\n'
        '    """Считает стоимость в USD: точный flat → префиксный flat → per-token.\n'
        '\n'
        '    Спринт 44: нулевые токены у неизвестной модели = служебная запись\n'
        '    (finalize и т.п.) → $0. Медиа-модели ОБЯЗАНЫ иметь flat-цену,\n'
        '    иначе физика мира их не видит.\n'
        '    """\n'
        '    # Flat-price модели (FAL, ElevenLabs и т.д.)\n'
        '    if model in MODEL_FLAT_PRICES:\n'
        '        return MODEL_FLAT_PRICES[model]\n'
        '    for _prefix, _price in MODEL_FLAT_PREFIXES.items():\n'
        '        if model.startswith(_prefix):\n'
        '            return _price\n'
        '    if prompt_tokens == 0 and completion_tokens == 0:\n'
        '        return 0.0  # служебная запись (finalize) — без стоимости\n'
        '    # Per-token модели\n'
        '    prices = MODEL_PRICES.get(model, MODEL_PRICES["_default"])',
        "ledger: _calc_cost v2",
    )

    # 2d. agent_spent_since — стоимость рана как дельта
    replace_exact(
        "studio/billing_ledger.py",
        'def slot_spent(slot_id: str) -> float:',
        'def agent_spent_since(agent_id: str, slot_id: str = None,\n'
        '                      since_iso: str = "") -> float:\n'
        '    """Расходы агента С МОМЕНТА since_iso — стоимость РАНА, не жизни.\n'
        '\n'
        '    Спринт 44: Ministry получал пожизненную сумму как cost_usd рана,\n'
        '    из-за чего расходы росли квадратично. Метку старта ставит\n'
        '    cartridge.py в state["_run_started_ts"].\n'
        '    Пустой/битый since_iso → fallback на пожизненную сумму.\n'
        '    """\n'
        '    if not since_iso:\n'
        '        return agent_spent(agent_id, slot_id)\n'
        '    try:\n'
        '        since = datetime.fromisoformat(since_iso)\n'
        '    except (ValueError, TypeError):\n'
        '        return agent_spent(agent_id, slot_id)\n'
        '    total = 0.0\n'
        '    for e in read_ledger():\n'
        '        if e.get("agent_id") != agent_id:\n'
        '            continue\n'
        '        if slot_id and e.get("slot_id") != slot_id:\n'
        '            continue\n'
        '        try:\n'
        '            if datetime.fromisoformat(e["ts"]) >= since:\n'
        '                total += e.get("cost_usd", 0.0)\n'
        '        except Exception:\n'
        '            continue\n'
        '    return round(total, 6)\n'
        '\n'
        '\n'
        'def slot_spent(slot_id: str) -> float:',
        "ledger: agent_spent_since (дельта рана)",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 3 · studio/agent_feedback.py — потолок на blocks-пути + серии 6.0
# ──────────────────────────────────────────────────────────────────

def patch_agent_feedback():
    print("\n── ШАГ 3 · agent_feedback.py: честный потолок + chain-серии ──")

    replace_exact(
        "studio/agent_feedback.py",
        '        # Оценка блока: 10 * (pass / checks) если checks > 0\n'
        '        score = round(10 * passed / checks, 1) if checks > 0 else 5.0',
        '        # Оценка блока: 10 * (pass / checks), РЕЖЕТСЯ потолком 6.0\n'
        '        # Спринт 44: раньше blocks-путь обходил потолок и давал до 10 —\n'
        '        # «фальшивые девятки» от детерминированного парсинга QA\n'
        '        score = _apply_score_ceiling(round(10 * passed / checks, 1)) if checks > 0 else 5.0',
        "feedback: потолок 6.0 на blocks-пути",
    )

    replace_exact(
        "studio/agent_feedback.py",
        '            "overall_status": overall or ("READY" if universal_score >= 8 else "OK"),',
        '            "overall_status": overall or ("READY" if universal_score >= 6.0 else "OK"),',
        "feedback: READY-порог под chain-шкалу",
    )

    replace_exact(
        "studio/agent_feedback.py",
        '        # Streak logic\n'
        '        score = run_data.get("score", 5.0)\n'
        '        if score >= 8:',
        '        # Streak logic · Спринт 44: chain-шкала (потолок 6.0)\n'
        '        # Победа = чистое ремесло (>= 6.0), провал = развал (< 4.0).\n'
        '        # Раньше победа требовала >= 8 — недостижимо при честном потолке,\n'
        '        # серии и звёзды были мертвы.\n'
        '        score = run_data.get("score", 5.0)\n'
        '        if score >= 6.0:',
        "feedback: победа серии = чистая 6.0",
    )

    replace_exact(
        "studio/agent_feedback.py",
        '        elif score < 5:\n'
        '            # Провал\n'
        '            if ga["streak"] <= 0:',
        '        elif score < 4.0:\n'
        '            # Провал (chain-шкала: развал цепочки)\n'
        '            if ga["streak"] <= 0:',
        "feedback: провал серии < 4.0",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 4 · studio/workshop/pipeline.py — один писатель chain + дельта
# ──────────────────────────────────────────────────────────────────

PIPELINE_MINISTRY_OLD = '''        # ══ Ministry: фиксируем исходы post-fact (Этапы 6-7) ══
        if _ECONOMY_ENABLED:
            _results_data = state.get("results", {})
            _agents_fb    = {}
            try:
                from pathlib import Path as _Path
                import json as _json
                _fb_path = _Path("clients") / client_slug / "feedback.json"
                if _fb_path.exists():
                    _agents_fb = _json.loads(_fb_path.read_text(encoding="utf-8")).get("agents", {})
            except Exception:
                pass
            _ec_slot = state.get("_slot_id", "")
            for _wid, _wdata in _agents_fb.items():
                _wscore = float(_wdata.get("score", 5.0))
                try:
                    from studio.economy import ledger as _ledger
                    _wcost = _ledger.agent_spent(_wid, slot_id=_ec_slot)
                except Exception:
                    _wcost = 0.0
                try:
                    if not state.get("async_scoring", False):  # patch_ministry_qa
                        _ministry.record_outcome(
                            agent_id=_wid,
                            slot_id=_ec_slot,
                            score=_wscore,
                            cost_usd=_wcost,
                        )
                except Exception as _me:
                    print(f"[MINISTRY] record_outcome ошибка: {_me}")
        # ══ END Ministry ══'''

PIPELINE_MINISTRY_NEW = '''        # ══ Ministry: единственный писатель CHAIN-валюты · Спринт 44 ══
        # Закон двух валют: pipeline после QA пишет per-agent chain-исходы
        # (оценки из feedback.json, потолок 6.0, source="chain").
        # REAL-валюту (>6.0) пишет только Metrics Daemon (source="real").
        # Хуки цехов Ministry больше не трогают — дубли убраны.
        # Стоимость = дельта расходов ОТ СТАРТА РАНА, не пожизненная сумма.
        if _ECONOMY_ENABLED:
            _agents_fb = {}
            try:
                from pathlib import Path as _Path
                import json as _json
                _fb_path = _Path("clients") / client_slug / "feedback.json"
                if _fb_path.exists():
                    _agents_fb = _json.loads(_fb_path.read_text(encoding="utf-8")).get("agents", {})
            except Exception:
                pass
            _ec_slot = state.get("_slot_id", "")
            _run_ts  = state.get("_run_started_ts", "")
            for _wid, _wdata in _agents_fb.items():
                _wscore = float(_wdata.get("score", 5.0))
                try:
                    from studio import billing_ledger as _bl44
                    _wcost = _bl44.agent_spent_since(
                        _wid, slot_id=_ec_slot, since_iso=_run_ts)
                except Exception:
                    _wcost = 0.0
                try:
                    _ministry.record_outcome(
                        agent_id=_wid,
                        slot_id=_ec_slot,
                        score=_wscore,
                        cost_usd=_wcost,
                        source="chain",
                    )
                except TypeError:
                    # совместимость со старым ministry без source
                    _ministry.record_outcome(_wid, _ec_slot, _wscore, _wcost)
                except Exception as _me:
                    print(f"[MINISTRY] record_outcome ошибка: {_me}")
        # ══ END Ministry ══'''

PIPELINE_DNA_OLD = '''        if score >= 8.0:
            event = "good_work"
            intensity = normalized
        elif score < 5.0:
            event = "bad_work"
            intensity = 1.0 - normalized      # чем хуже — тем сильнее
        else:
            event = "good_work"
            intensity = 0.4                   # нейтральная работа'''

PIPELINE_DNA_NEW = '''        # Спринт 44 · chain-шкала (потолок 6.0):
        #   >= 6.0 — чистое ремесло, полноценная награда
        #   4.0–5.9 — выжил, лёгкий позитив
        #   < 4.0 — развал цепочки
        # Real-оценки зрителя (>6.0) в DNA понесёт Демон отдельным каналом.
        if score >= 6.0:
            event = "good_work"
            intensity = 0.7                   # чистая шестёрка — заслуженно
        elif score < 4.0:
            event = "bad_work"
            intensity = round(min(1.0, 1.0 - normalized), 2)
        else:
            event = "good_work"
            intensity = 0.35                  # выжил — лёгкий след'''

def patch_pipeline():
    print("\n── ШАГ 4 · pipeline.py: один писатель chain + дельта + DNA-шкала ──")

    replace_exact("studio/workshop/pipeline.py",
                  PIPELINE_MINISTRY_OLD, PIPELINE_MINISTRY_NEW,
                  "pipeline: Ministry → единственный chain-писатель")

    replace_exact("studio/workshop/pipeline.py",
                  PIPELINE_DNA_OLD, PIPELINE_DNA_NEW,
                  "pipeline: DNA-синк под chain-шкалу")

    replace_exact(
        "studio/workshop/pipeline.py",
        '    class _ministry:\n'
        '        @staticmethod\n'
        '        def get_prompt_hint(agent_id, slot_id): return ""\n'
        '        @staticmethod\n'
        '        def record_outcome(agent_id, slot_id, score, cost_usd): pass',
        '    class _ministry:\n'
        '        @staticmethod\n'
        '        def get_prompt_hint(agent_id, slot_id): return ""\n'
        '        @staticmethod\n'
        '        def record_outcome(agent_id, slot_id, score, cost_usd, source="chain"): pass',
        "pipeline: заглушка ministry с source",
    )

    # docstring функции синка — поправим описание шкалы
    replace_exact(
        "studio/workshop/pipeline.py",
        '    score 0–4   → bad_work  (intensity = 1 - score/10)\n'
        '    score 5–7   → нейтрально, лёгкий good_work\n'
        '    score 8–10  → good_work (intensity = score/10)\n'
        '    """',
        '    Chain-шкала (Спринт 44, потолок 6.0):\n'
        '      score >= 6.0 → good_work 0.7 (чистое ремесло)\n'
        '      4.0–5.9      → good_work 0.35 (выжил)\n'
        '      < 4.0        → bad_work (развал цепочки)\n'
        '    """',
        "pipeline: docstring DNA-синка",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 5 · studio/cartridge.py — метка старта рана
# ──────────────────────────────────────────────────────────────────

def patch_cartridge():
    print("\n── ШАГ 5 · cartridge.py: метка _run_started_ts ──")
    replace_exact(
        "studio/cartridge.py",
        '        self.state["_slot_id"] = self.slot_id  # ← slot_id для feedback/reflection\n'
        '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч',
        '        self.state["_slot_id"] = self.slot_id  # ← slot_id для feedback/reflection\n'
        '        # ПАТЧ economy_sprint44: метка старта рана — стоимость рана\n'
        '        # считается как дельта расходов от этой метки (не пожизненно)\n'
        '        from datetime import datetime as _dt44, timezone as _tz44\n'
        '        self.state["_run_started_ts"] = _dt44.now(_tz44.utc).isoformat()\n'
        '        self.state["active_dept"] = self.manifest.id  # ← dept-aware патч',
        "cartridge: метка старта рана",
    )

# ──────────────────────────────────────────────────────────────────
# ШАГ 6 · turbo/hooks.py — шкала 0–6, has_music, без Ministry, ключ A01
# ──────────────────────────────────────────────────────────────────

def patch_turbo():
    print("\n── ШАГ 6 · turbo/hooks.py ──")

    # 6a. has_music в _a05_record_ministry (читал несуществующий ключ)
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '        # Аудио (новое)\n'
        '        mimi = chain.get("mimi_sound", {})\n'
        '        has_music = bool(mimi.get("music_path"))',
        '        # Аудио (новое) · Спринт 44: A02 пишет music.audio_path (вложенно),\n'
        '        # старый код читал плоский music_path и музыка всегда была "❌"\n'
        '        mimi = chain.get("mimi_sound", {})\n'
        '        _mus = mimi.get("music", {})\n'
        '        if isinstance(_mus, str):\n'
        '            _mus = {"audio_path": _mus}\n'
        '        has_music = bool(_mus.get("audio_path") or mimi.get("music_path"))',
        "turbo: has_music читает music.audio_path",
    )

    # 6b. формула → шкала 0–6 (потолок ремесла)
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '        # Формула: +2.0 кадры, +1.5 клипы, +1.0 обложки, +0.5 музыка, +0.5 качество\n'
        '        score = 4.0\n'
        '        score += 2.0 * (ready_frames / total_frames)\n'
        '        score += 1.5 * (ready_clips  / total_frames)\n'
        '        score += 1.0 * (ready_thumbs / 2)\n'
        '        score += 0.5 * (1.0 if has_music else 0.0)\n'
        '        score += 0.5 * (avg_qs / 10.0)\n'
        '        score  = round(min(10.0, score), 2)',
        '        # Формула CHAIN-валюты · Спринт 44: шкала 0–6.0 (потолок ремесла).\n'
        '        # 6.0 = всё на месте и чисто. Выше — только зритель/Шеф (real).\n'
        '        # Старая формула давала до 9.5 — скрипт чеканил фальшивые девятки.\n'
        '        score = 6.0 * (\n'
        '            0.35 * (ready_frames / total_frames)\n'
        '            + 0.25 * (ready_clips / total_frames)\n'
        '            + 0.20 * (ready_thumbs / 2)\n'
        '            + 0.10 * (1.0 if has_music else 0.0)\n'
        '            + 0.10 * (avg_qs / 10.0)\n'
        '        )\n'
        '        score = round(min(6.0, max(0.0, score)), 2)',
        "turbo: chain-score 0–6",
    )

    # 6c. Strategy Registry ключ 'a01' → 'A01'
    replace_exact(
        "studio/modules/turbo/hooks.py",
        "            _fa_list  = _slot_reg.setdefault('a01', [])",
        "            _fa_list  = _slot_reg.setdefault('A01', [])  # Спринт 44: регистр как у pipeline",
        "turbo: ключ Registry → A01",
    )

    # 6d. Ministry из хука убираем (единственный писатель — pipeline)
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '        agents = ["A01", "A02", "A03", "A04", "A05"]\n'
        '        for agent_id in agents:\n'
        '            try:\n'
        '                from studio.economy import ledger as _led\n'
        '                cost = _led.agent_spent(agent_id, slot_id=slot_id)\n'
        '            except Exception:\n'
        '                cost = 0.0\n'
        '            _min.record_outcome(\n'
        '                agent_id=agent_id,\n'
        '                slot_id=slot_id,\n'
        '                score=score,\n'
        '                cost_usd=cost,\n'
        '            )\n'
        '\n'
        '        print(f"[TURBO A05] 🏛 Ministry: score={score} "',
        '        # Спринт 44 · Закон двух валют: Ministry хук НЕ трогает.\n'
        '        # Chain-исходы per-agent пишет pipeline после QA (feedback.json),\n'
        '        # real-исходы — Metrics Daemon. Дубли и пожизненный cost убраны.\n'
        '\n'
        '        print(f"[TURBO A05] ✅ chain_score={score} "',
        "turbo: Ministry-дубль убран",
    )

    # 6e. неиспользуемый импорт ministry + текст except
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '    try:\n'
        '        from studio.economy import ministry as _min\n'
        '        slot_id = state.get("_slot_id", "turbo")\n'
        '\n'
        '        chain  = state.get("chain_data", {})\n'
        '        deliv  = chain.get("t5_deliverables", {})',
        '    try:\n'
        '        slot_id = state.get("_slot_id", "turbo")\n'
        '\n'
        '        chain  = state.get("chain_data", {})\n'
        '        deliv  = chain.get("t5_deliverables", {})',
        "turbo: лишний импорт ministry убран",
    )
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '        print(f"[TURBO A05] ⚠ ministry.record_outcome: {e}")',
        '        print(f"[TURBO A05] ⚠ замыкание петли: {e}")',
        "turbo: текст except",
    )

    # 6f. has_audio в deliverables (тот же битый ключ)
    replace_exact(
        "studio/modules/turbo/hooks.py",
        '    has_audio = bool(mimi_sound.get("music_path"))',
        '    _ms44 = mimi_sound.get("music", {})\n'
        '    if isinstance(_ms44, str):\n'
        '        _ms44 = {"audio_path": _ms44}\n'
        '    has_audio = bool(_ms44.get("audio_path") or mimi_sound.get("music_path"))',
        "turbo: has_audio читает music.audio_path",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 7 · video_long/hooks.py — воскрешение мёртвого кода
# ──────────────────────────────────────────────────────────────────

VL_BOB_NEW = '''def _bob_record_ministry(state: dict, my_output: dict) -> None:
    """
    ЗАМЫКАНИЕ ПЕТЛИ video_long · Спринт 44 (Закон двух валют).

    CHAIN-валюта (0–6.0, детерминированно по фактам файлов):
      1. task_score → billing_ledger (для всех агентов цепочки)
      2. Strategy Registry → стратегия A01 (wins++ если score >= 6.0)

    Ministry хук НЕ трогает: per-agent chain-исходы пишет pipeline после
    QA (feedback.json, source="chain"), real-валюту — Metrics Daemon.
    viral_score из outcome_signal НЕ читается: по закону §6 outcome_signal
    от QA-агента всегда null, читать его как оценку = есть фантазию LLM.

    Историческая справка: до Спринта 44 весь этот блок лежал ВНУТРИ
    docstring и не исполнялся ни разу.
    """
    slot_id = state.get("_slot_id", "video_long")
    try:
        # ── Детерминированный chain-score: потолок 6.0 ────────────────
        deliv    = state.get("_last_output", {}).get("deliverables", {}) or {}
        kf       = deliv.get("key_frames", []) or []
        ready_kf = sum(1 for f in kf if isinstance(f, dict) and f.get("path"))
        total_kf = len(kf) or 1
        thumb    = deliv.get("thumbnail", {}) or {}
        ready_th = sum(
            1 for v in ("variant_a", "variant_b")
            if isinstance(thumb.get(v), dict) and thumb.get(v, {}).get("path")
        )
        score = 4.0 * (ready_kf / total_kf) + 2.0 * (ready_th / 2)
        score = round(min(6.0, max(0.0, score)), 2)

        agents = list(state.get("results", {}).keys()) or [
            "A01", "A02", "A03", "A04", "A05",
            "A06", "A07", "A08", "A09", "A10", "A11", "A12",
        ]

        # ── 1. task_score → billing_ledger ────────────────────────────
        try:
            from studio.billing_ledger import record as _bl_record
            for _aid in agents:
                _bl_record(
                    agent_id=_aid,
                    slot_id=slot_id,
                    model=slot_id + "/finalize",
                    prompt_tokens=0,
                    completion_tokens=0,
                    call_type="finalize",
                    task_score=score,
                )
            print(f"[LONG BOB] 📊 chain_score={score} → ledger ({len(agents)} агентов)")
        except Exception as _le:
            print(f"[LONG BOB] ⚠ ledger task_score: {_le}")

        # ── 2. Strategy Registry (ключ 'A01' — регистр как у pipeline) ─
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

            _chain   = state.get("chain_data", {}) or {}
            _first   = _chain.get("adam_episode", {})
            _summary = (
                _first.get("strategy_summary", "")
                or _first.get("brief", "")
                or _first.get("concept", "")
                or _first.get("synopsis", "")
                or "без описания"
            )[:200]

            _slots    = _reg.setdefault("slots", {})
            _slot_reg = _slots.setdefault(slot_id, {})
            _fa_list  = _slot_reg.setdefault("A01", [])

            _existing = next(
                (s for s in _fa_list if s.get("summary", "")[:60] == _summary[:60]),
                None
            )
            _now = _rdt.now().isoformat()
            if _existing:
                if score >= 6.0:
                    _existing["wins"] = _existing.get("wins", 0) + 1
                _existing["last_score"] = score
                _existing["last_run"]   = _now
            else:
                _fa_list.append({
                    "ts":           _now,
                    "score":        score,
                    "last_score":   score,
                    "last_run":     _now,
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
            _reg["updated_at"] = _now
            _reg.setdefault("version", 1)
            _reg_path.write_text(
                _rj.dumps(_reg, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            _wm = "🏆" if score >= 6.0 else "📝"
            print(f"[LONG BOB] {_wm} Registry: score={score}, wins={_total_wins}")
        except Exception as _re:
            print(f"[LONG BOB] ⚠ Strategy Registry: {_re}")

    except Exception as e:
        print(f"[VL A12] ⚠ замыкание петли: {e}")
    finally:
        # ── РАБОЧИЙ СТАТУС: все агенты video_long свободны ────────
        try:
            from studio.city_pulse import log_work_end as _lwe
            _slot = state.get("_slot_id", "video_long")
            _pid  = state.get("project_id", "")
            for _aid in ["A01", "A02", "A03", "A04", "A05",
                         "A06", "A07", "A08", "A09", "A10", "A11", "A12"]:
                _lwe(agent=_aid, dept="video_long",
                     slot_id=_slot, project_id=_pid, status="DONE")
            print("[VL A12] 🏁 work_end → все 12 агентов video_long свободны")
        except Exception:
            pass
        # ── END РАБОЧИЙ СТАТУС ──


'''

def patch_video_long():
    print("\n── ШАГ 7 · video_long/hooks.py: воскрешение замыкания петли ──")
    replace_span(
        "studio/modules/video_long/hooks.py",
        "def _bob_record_ministry(state: dict, my_output: dict) -> None:",
        "def _bob_collect_media(",
        VL_BOB_NEW,
        "video_long: _bob_record_ministry пересобран (был в docstring)",
        "Историческая справка: до Спринта 44 весь этот блок",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 8 · video_shorts/hooks.py — честный chain-score вместо фантазий
# ──────────────────────────────────────────────────────────────────

VS_TOM_NEW = '''def _tom_record_ministry(state: dict, outcome_signal: dict, my_output: dict) -> None:
    """
    CHAIN-валюта · Спринт 44: ledger task_score + Strategy Registry.

    Детерминированный chain-score (потолок 6.0) по фактам файлов:
    кадры Веры + клипы (video_path в chain_data) + музыка Джулии.

    viral_score из outcome_signal НЕ читается: по закону §6 он всегда
    null от QA — real-валюту приносит Metrics Daemon после публикации.
    Ministry хук не трогает (per-agent chain пишет pipeline после QA).
    """
    slot_id = state.get("_slot_id", "video_shorts")
    try:
        chain = state.get("chain_data", {}) or {}

        # кадры Веры (A07)
        vera    = chain.get("vera_visual", {}) or {}
        frames  = vera.get("frames", []) if isinstance(vera, dict) else []
        ready_f = sum(1 for f in frames if isinstance(f, dict) and f.get("path"))
        total_f = len(frames) or 1

        # клипы — ищем по факту поля video_path в любом блоке chain_data
        ready_c, total_c = 0, 0
        for _v in chain.values():
            _items = []
            if isinstance(_v, dict):
                for _lv in _v.values():
                    if isinstance(_lv, list):
                        _items.extend(_lv)
            elif isinstance(_v, list):
                _items = _v
            for _it in _items:
                if isinstance(_it, dict) and "video_path" in _it:
                    total_c += 1
                    if _it.get("video_path"):
                        ready_c += 1
        total_c = total_c or 1

        # музыка Джулии (A03)
        _js  = chain.get("julia_sound_code", chain.get("julia_sound", {})) or {}
        _mus = _js.get("music", {}) if isinstance(_js, dict) else {}
        has_music = bool(_mus.get("audio_path")) if isinstance(_mus, dict) else False

        score = 6.0 * (
            0.40 * (ready_f / total_f)
            + 0.35 * (ready_c / total_c)
            + 0.25 * (1.0 if has_music else 0.0)
        )
        score = round(min(6.0, max(0.0, score)), 2)

        agents = list(state.get("results", {}).keys()) or [
            "A01", "A02", "A03", "A04", "A05",
            "A06", "A07", "A08", "A09", "A10", "A11", "A12",
        ]

        # ── 1. task_score → billing_ledger ────────────────────────────
        try:
            from studio.billing_ledger import record as _bl_record
            for aid in agents:
                _bl_record(
                    agent_id=aid,
                    slot_id=slot_id,
                    model=slot_id + "/finalize",
                    prompt_tokens=0,
                    completion_tokens=0,
                    call_type="finalize",
                    task_score=score,
                )
            print(f"[VS A12 Том] 📊 chain_score={score} → ledger "
                  f"(frames={ready_f}/{total_f} clips={ready_c}/{total_c} "
                  f"music={'✅' if has_music else '—'}, {len(agents)} агентов)")
        except Exception as e:
            print(f"[VS A12 Том] ⚠️  billing_ledger: {e}")

        # ── 2. Strategy Registry (ключ 'A01') ─────────────────────────
        try:
            import json as _rj
            reg_path = Path("studio/strategy_registry.json")
            reg = {}
            if reg_path.exists():
                try:
                    reg = _rj.loads(reg_path.read_text(encoding="utf-8"))
                except Exception:
                    reg = {}

            first   = chain.get("trixie_trend", chain.get("trixie_episode", {}))
            summary = (
                first.get("series_concept", {}).get("viral_angle", "")
                or first.get("episode_brief", "")
                or "без описания"
            )[:200]

            slots    = reg.setdefault("slots", {})
            slot_reg = slots.setdefault(slot_id, {})
            fa_list  = slot_reg.setdefault("A01", [])

            existing = next(
                (s for s in fa_list if s.get("summary", "")[:60] == summary[:60]),
                None,
            )
            now = datetime.datetime.now().isoformat()
            if existing:
                if score >= 6.0:
                    existing["wins"] = existing.get("wins", 0) + 1
                existing["last_score"] = score
                existing["last_run"]   = now
            else:
                fa_list.append({
                    "ts":           now,
                    "score":        score,
                    "last_score":   score,
                    "last_run":     now,
                    "run_type":     slot_id,
                    "summary":      summary,
                    "wins":         1 if score >= 6.0 else 0,
                    "transferable": False,
                })

            total_wins = sum(
                s.get("wins", 0)
                for sl in reg.get("slots", {}).values()
                for elist in sl.values()
                for s in elist
            )
            reg["total_wins"] = total_wins
            reg["updated_at"] = now
            reg.setdefault("version", 1)
            reg_path.write_text(
                _rj.dumps(reg, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            wm = "🏆" if score >= 6.0 else "📝"
            print(f"[VS A12 Том] {wm} strategy_registry: score={score} wins={total_wins}")
        except Exception as e:
            print(f"[VS A12 Том] ⚠️  strategy_registry: {e}")

    except Exception as e:
        print(f"[VS A12 Том] ⚠️  замыкание петли: {e}")


'''

def patch_video_shorts():
    print("\n── ШАГ 8 · video_shorts/hooks.py: честный chain-score ──")
    replace_span(
        "studio/modules/video_shorts/hooks.py",
        "def _tom_record_ministry(state: dict, outcome_signal: dict, my_output: dict) -> None:",
        "def _tom_save_feedback(",
        VS_TOM_NEW,
        "video_shorts: _tom_record_ministry пересобран",
        "CHAIN-валюта · Спринт 44: ledger task_score + Strategy Registry",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 9 · social_mix/hooks.py — ключ Registry → A01
# ──────────────────────────────────────────────────────────────────

def patch_social_mix():
    print("\n── ШАГ 9 · social_mix/hooks.py: ключ Registry → A01 ──")
    replace_exact(
        "studio/modules/social_mix/hooks.py",
        '        fa_list   = slot_reg.setdefault("a01", [])',
        '        fa_list   = slot_reg.setdefault("A01", [])  # Спринт 44: регистр как у pipeline',
        "social_mix: ключ Registry → A01",
    )

# ──────────────────────────────────────────────────────────────────
# ШАГ 10 · strategy_registry.py — BASE_DIR + регистронезависимое чтение
# ──────────────────────────────────────────────────────────────────

def patch_strategy_registry():
    print("\n── ШАГ 10 · strategy_registry.py ──")

    replace_exact(
        "studio/strategy_registry.py",
        'REGISTRY_PATH = Path("studio") / "strategy_registry.json"',
        '# Спринт 44: путь от BASE_DIR — запуск не из корня создавал файл-двойник\n'
        'try:\n'
        '    from studio.config import BASE_DIR as _BASE_DIR\n'
        '    REGISTRY_PATH = _BASE_DIR / "studio" / "strategy_registry.json"\n'
        'except Exception:\n'
        '    REGISTRY_PATH = Path("studio") / "strategy_registry.json"',
        "registry: путь от BASE_DIR",
    )

    replace_exact(
        "studio/strategy_registry.py",
        '# Порог оценки для фиксации стратегии\n'
        'STRATEGY_SCORE_THRESHOLD = 8.0',
        '# Порог оценки для фиксации стратегии.\n'
        '# Спринт 44 (Закон двух валют): 8.0 — это REAL-валюта (зритель/Шеф).\n'
        '# Chain-победы (потолок 6.0) пишут хуки финализаторов напрямую в JSON;\n'
        '# этот модульный путь зарезервирован под real-оценки (Демон/живой QA).\n'
        'STRATEGY_SCORE_THRESHOLD = 8.0',
        "registry: docstring порога (real-валюта)",
    )

    replace_exact(
        "studio/strategy_registry.py",
        '        slot_agents = registry.get("slots", {}).get(slot_id, {})\n'
        '        agent_strats = slot_agents.get(agent_id, [])',
        '        slot_agents = registry.get("slots", {}).get(slot_id, {})\n'
        '        # Спринт 44: регистронезависимо — хуки писали \'a01\', pipeline читал \'A01\',\n'
        '        # стратегии копились, но НИКОГДА не доходили до промпта агента\n'
        '        agent_strats = (\n'
        '            slot_agents.get(agent_id)\n'
        '            or slot_agents.get(agent_id.upper())\n'
        '            or slot_agents.get(agent_id.lower())\n'
        '            or []\n'
        '        )',
        "registry: чтение слотовых без учёта регистра",
    )

    replace_exact(
        "studio/strategy_registry.py",
        '    agent_globals = registry.get("global", {}).get(agent_id, [])\n'
        '    agent_globals_sorted = sorted(',
        '    _glob = registry.get("global", {})\n'
        '    agent_globals = (\n'
        '        _glob.get(agent_id)\n'
        '        or _glob.get(agent_id.upper())\n'
        '        or _glob.get(agent_id.lower())\n'
        '        or []\n'
        '    )\n'
        '    agent_globals_sorted = sorted(',
        "registry: чтение глобальных без учёта регистра",
    )


# ──────────────────────────────────────────────────────────────────
# ШАГ 11 · strategy_registry.json — миграция ключей a01 → A01
# ──────────────────────────────────────────────────────────────────

def migrate_registry_json():
    print("\n── ШАГ 11 · strategy_registry.json: миграция a01 → A01 ──")
    path = ROOT / "studio" / "strategy_registry.json"
    if not path.exists():
        print("  ⏭  файла нет — создастся при первом ране, пропускаю")
        SKIPPED.append("registry.json: миграция (файла нет)")
        return
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        FAILED.append(f"registry.json: не читается ({e})")
        print(f"  ❌ не читается: {e}")
        return

    changed = False

    def _merge_case(d: dict) -> bool:
        nonlocal changed
        local = False
        for key in list(d.keys()):
            up = key.upper()
            if key != up and re.fullmatch(r"[a-z]\d+", key):
                d.setdefault(up, [])
                d[up].extend(d.pop(key))
                local = True
        return local

    for slot_id, agents in (reg.get("slots") or {}).items():
        if isinstance(agents, dict) and _merge_case(agents):
            changed = True
            print(f"  🔧 слот {slot_id}: ключи приведены к верхнему регистру")
    if isinstance(reg.get("global"), dict) and _merge_case(reg["global"]):
        changed = True
        print("  🔧 global: ключи приведены к верхнему регистру")

    if changed:
        _backup(path)
        path.write_text(json.dumps(reg, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        APPLIED.append("registry.json: миграция a01 → A01")
        print("  ✅ миграция выполнена")
    else:
        SKIPPED.append("registry.json: миграция не требуется")
        print("  ⏭  миграция не требуется")


# ──────────────────────────────────────────────────────────────────
# ШАГ 12 · cost_intuition.py v2 — ROI: стоимость × качество
# ──────────────────────────────────────────────────────────────────

COST_INTUITION_V2 = '''# studio/economy/cost_intuition.py
"""
ЭТАП 2 — COST INTUITION · v2.0 «ROI-ощущение» (Спринт 44)

Агент НЕ видит деньги напрямую. Он чувствует ОКУПАЕМОСТЬ:
не «сколько я потратил», а «стоило ли оно того».

Исходная спека ЭТАПА 2 требовала пару (cost, outcome_quality) —
v1 читала только cost, и художник с честными flat-вызовами вечно
чувствовал «бюджет под угрозой» независимо от качества работы.

Качество берётся из task_score в billing_ledger (finalize-записи
финализаторов цехов, chain-шкала 0–6.0).

get_prompt_hint() → вставляй в промпт агента перед работой.
"""

from studio.economy import ledger

COST_THRESHOLDS = {
    "cheap":     0.0005,
    "medium":    0.003,
    "expensive": 0.010,
}
WINDOW_COST    = 10   # последних платных вызовов для среднего чека
WINDOW_QUALITY = 5    # последних task_score для среднего качества
SCAN_DEPTH     = 40   # сколько записей леджера сканируем


def _classify(avg_cost: float) -> str:
    if avg_cost < COST_THRESHOLDS["cheap"]:
        return "cheap"
    elif avg_cost < COST_THRESHOLDS["medium"]:
        return "medium"
    elif avg_cost < COST_THRESHOLDS["expensive"]:
        return "expensive"
    return "risky"


def _quality_bucket(avg_q: float | None) -> str:
    """Chain-шкала 0–6: clean (>=5.5) / solid (4.0–5.4) / weak (<4.0) / none."""
    if avg_q is None:
        return "none"
    if avg_q >= 5.5:
        return "clean"
    if avg_q >= 4.0:
        return "solid"
    return "weak"


# Ощущение = пара (вес расходов, окупаемость)
_FEELINGS = {
    ("cheap", "clean"):     "Лёгкая рука и чистый результат — работаешь без потерь, так держать.",
    ("cheap", "solid"):     "Расходы лёгкие, ремесло держится. Есть запас — можно копнуть глубже.",
    ("cheap", "weak"):      "Дёшево, но цепочка сыпется. Дешевизна не оправдывает брак — собери качество.",
    ("cheap", "none"):      "Ты чувствуешь лёгкость — последние действия не давили на бюджет. Работай уверенно.",
    ("medium", "clean"):    "Каждый вложенный токен окупается. Сбалансированная, честная работа.",
    ("medium", "solid"):    "Умеренный вес решений, ремесло на уровне. Выбирай стратегии осознанно.",
    ("medium", "weak"):     "Тратишь умеренно, но результат не держится. Пересмотри подход, не бюджет.",
    ("medium", "none"):     "Ты чувствуешь умеренный вес своих решений. Каждый шаг имеет значение.",
    ("expensive", "clean"): "Дорого — но чисто. Тяжёлая работа, которая того стоит. Следи за весом.",
    ("expensive", "solid"): "Тяжёлые вызовы при среднем результате. Ищи более лёгкие пути к тому же качеству.",
    ("expensive", "weak"):  "Дорого и не окупается. Остановись, подумай: меньше попыток — точнее замысел.",
    ("expensive", "none"):  "Ты ощущаешь тяжесть — последние вызовы стоили дорого. Думай экономно.",
    ("risky", "clean"):     "На грани бюджета, но результат блестит. Оправданный риск — не превращай его в привычку.",
    ("risky", "solid"):     "Бюджет под давлением, отдача средняя. Режь расход, качество держи.",
    ("risky", "weak"):      "Давление на пределе и работа сыпется. Максимальная осторожность: один точный шаг вместо пяти.",
    ("risky", "none"):      "Ты чувствуешь давление — бюджет под угрозой. Действуй с максимальной осторожностью.",
}


def get_intuition(agent_id: str, slot_id: str = None) -> dict:
    """Полная экономическая интуиция агента: вес расходов × окупаемость."""
    recent = ledger.recent_by_agent(agent_id, slot_id=slot_id, n=SCAN_DEPTH)
    total  = ledger.agent_spent(agent_id, slot_id=slot_id)

    if not recent:
        return {
            "level": "medium", "label": "нет истории",
            "avg_cost": 0.0, "total_spent": 0.0, "calls_seen": 0,
            "avg_quality": None, "quality_bucket": "none",
            "prompt_hint": "",
        }

    # средний чек — только по платным вызовам (finalize-нули не разбавляют)
    paid = [e for e in recent if e.get("cost_usd", 0) > 0]
    paid_window = paid[-WINDOW_COST:] if paid else recent[-WINDOW_COST:]
    avg_cost = (sum(e.get("cost_usd", 0) for e in paid_window) / len(paid_window)
                if paid_window else 0.0)

    # качество — из task_score (finalize-записи финализаторов)
    scores = [e["task_score"] for e in recent
              if e.get("task_score") is not None]
    q_window = scores[-WINDOW_QUALITY:]
    avg_q = round(sum(q_window) / len(q_window), 2) if q_window else None

    level   = _classify(avg_cost)
    bucket  = _quality_bucket(avg_q)
    feeling = _FEELINGS.get((level, bucket),
                            _FEELINGS[(level, "none")])

    q_line = (f"\\nОкупаемость: качество последних ранов {avg_q}/6.0"
              if avg_q is not None else "")
    hint = (f"[ЭКОНОМИЧЕСКОЕ ОЩУЩЕНИЕ]\\n{feeling}"
            f"\\nУровень расходов: {level.upper()}{q_line}")

    return {
        "level":          level,
        "avg_cost":       round(avg_cost, 8),
        "total_spent":    total,
        "calls_seen":     len(recent),
        "avg_quality":    avg_q,
        "quality_bucket": bucket,
        "prompt_hint":    hint,
    }


def get_prompt_hint(agent_id: str, slot_id: str = None) -> str:
    """Быстрый доступ: только строка для вставки в промпт."""
    return get_intuition(agent_id, slot_id)["prompt_hint"]
'''


# ──────────────────────────────────────────────────────────────────
# ШАГ 13 · metrics_daemon.py — REAL-валюта под честными ключами
# ──────────────────────────────────────────────────────────────────

def patch_metrics_daemon():
    print("\n── ШАГ 13 · metrics_daemon.py ──")

    replace_exact(
        "studio/economy/metrics_daemon.py",
        'CLIENTS_DIR      = Path("clients")',
        '# Спринт 44: путь от BASE_DIR — демон запускается и не из корня\n'
        'try:\n'
        '    import sys as _sys44\n'
        '    _sys44.path.insert(0, str(Path(__file__).parents[2]))\n'
        '    from studio.config import BASE_DIR as _BASE_DIR\n'
        '    CLIENTS_DIR = _BASE_DIR / "clients"\n'
        'except Exception:\n'
        '    CLIENTS_DIR = Path("clients")',
        "daemon: clients от BASE_DIR",
    )

    replace_exact(
        "studio/economy/metrics_daemon.py",
        '        # Министерство\n'
        '        _report_to_ministry(client_id, platform, real_score, entry["project_id"])',
        '        # Министерство (Спринт 44: REAL-валюта, честные ключи)\n'
        '        _report_to_ministry(client_id, platform, real_score,\n'
        '                            entry["project_id"], entry=entry)',
        "daemon: вызов с entry",
    )

    replace_exact(
        "studio/economy/metrics_daemon.py",
        'def _report_to_ministry(client_id: str, platform: str,\n'
        '                         real_score: float, project_id: str) -> None:\n'
        '    try:\n'
        '        sys.path.insert(0, str(Path(__file__).parents[2]))\n'
        '        from studio.economy import ministry\n'
        '        ministry.record_outcome("A06",      f"{platform}_fal", real_score, cost_usd=0.0)\n'
        '        ministry.record_outcome("pipeline", "social_mix",      real_score, cost_usd=0.0)\n'
        '        print(f"[DAEMON] Ministry обновлён: {project_id} → score={real_score}")\n'
        '    except Exception as e:\n'
        '        print(f"[DAEMON] ministry.record_outcome: {e}")',
        'def _report_to_ministry(client_id: str, platform: str,\n'
        '                         real_score: float, project_id: str,\n'
        '                         entry: dict | None = None) -> None:\n'
        '    """REAL-валюта · Спринт 44: Демон — единственный источник score > 6.0.\n'
        '\n'
        '    Пишет real-исход каждому агенту цеха под честными ключами\n'
        '    Axx::slot_id. Старый хардкод ("A06", "{platform}_fal") и\n'
        '    ("pipeline", "social_mix") плодил фантомные ключи в ministry.json.\n'
        '    """\n'
        '    try:\n'
        '        sys.path.insert(0, str(Path(__file__).parents[2]))\n'
        '        from studio.economy import ministry\n'
        '        slot_id = (entry or {}).get("slot_id") or "social_mix"\n'
        '        agents  = (entry or {}).get("agents") or [\n'
        '            "A01", "A02", "A03", "A04", "A05",\n'
        '            "A06", "A07", "A08", "A09", "A10", "A11", "A12",\n'
        '        ]\n'
        '        for aid in agents:\n'
        '            try:\n'
        '                ministry.record_outcome(aid, slot_id, real_score,\n'
        '                                        cost_usd=0.0, source="real")\n'
        '            except TypeError:\n'
        '                ministry.record_outcome(aid, slot_id, real_score, cost_usd=0.0)\n'
        '        print(f"[DAEMON] Ministry(real): {project_id} → score={real_score} "\n'
        '              f"({len(agents)} агентов, slot={slot_id})")\n'
        '    except Exception as e:\n'
        '        print(f"[DAEMON] ministry.record_outcome: {e}")',
        "daemon: real-валюта под честными ключами",
    )

    replace_exact(
        "studio/economy/metrics_daemon.py",
        'def _fetch_telegram(post_id: str, channel_id: str, token: str) -> dict:\n'
        '    if not token or not channel_id:\n'
        '        return {}',
        'def _fetch_telegram(post_id: str, channel_id: str, token: str) -> dict:\n'
        '    # ⚠ Спринт 44: Bot API НЕ отдаёт просмотры/реакции сообщений —\n'
        '    # метода getMessages в нём нет, вызов ниже всегда вернёт {}.\n'
        '    # Для TG-метрик нужен MTProto (telethon) или TGStat. См. README.\n'
        '    print("[DAEMON] ⚠ Telegram Bot API не отдаёт метрики постов — нужен telethon/TGStat")\n'
        '    if not token or not channel_id:\n'
        '        return {}',
        "daemon: честное предупреждение про Telegram",
    )


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

def main():
    print("═" * 66)
    print("ПАТЧ · СПРИНТ 44 — «ЗАКОН ДВУХ ВАЛЮТ»")
    print(f"Корень проекта: {ROOT.resolve()}")
    print("═" * 66)

    print("\n── ШАГ 1 · ministry.py v2: две валюты ──")
    write_full("studio/economy/ministry.py", MINISTRY_V2,
               "ministry v2 (две валюты)", "«Закон двух валют»")

    patch_billing_ledger()
    patch_agent_feedback()
    patch_pipeline()
    patch_cartridge()
    patch_turbo()
    patch_video_long()
    patch_video_shorts()
    patch_social_mix()
    patch_strategy_registry()
    migrate_registry_json()

    print("\n── ШАГ 12 · cost_intuition.py v2: ROI-ощущение ──")
    write_full("studio/economy/cost_intuition.py", COST_INTUITION_V2,
               "cost_intuition v2 (ROI)", "ROI-ощущение")

    patch_metrics_daemon()

    print("\n" + "═" * 66)
    print(f"ИТОГ: применено {len(APPLIED)} · пропущено {len(SKIPPED)} · ошибок {len(FAILED)}")
    if FAILED:
        print("\n❌ ОШИБКИ (файлы отличаются от ожидаемых — сообщи Брату):")
        for f in FAILED:
            print(f"   • {f}")
    if APPLIED:
        print("\n✅ Применено:")
        for a in APPLIED:
            print(f"   • {a}")
    print("\nБэкапы: *.bak_" + STAMP)
    print("Дальше: перезапусти main.py и прогони любой ран до финализатора —")
    print("в консоли должны появиться строки chain_score=… → ledger.")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
