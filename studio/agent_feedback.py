# studio/agent_feedback.py
"""
Agent Feedback Loop — оценки от Артура передаются агентам в следующий ран.

Цикл:
  1. Артур (A12) ставит оценки каждому агенту в my_output.blocks
  2. После рана — save_feedback() парсит оценки и сохраняет в feedback.json
  3. При следующем запуске — get_feedback() возвращает текст для промпта агента

Использование в pipeline.py:
  from studio.agent_feedback import get_feedback, save_feedback
  
  # В build_agent_context:
  feedback = get_feedback(client_slug, worker_id)
  if feedback:
      context += feedback
  
  # В конце рана (после A12):
  save_feedback(client_slug, arthur_raw_result)
"""

import json
from pathlib import Path
from datetime import datetime

CLIENTS_DIR = Path("clients")
GLOBAL_FEEDBACK_PATH = Path("studio") / "global_feedback.json"


def _feedback_path(client_slug: str) -> Path:
    """Путь к файлу обратной связи."""
    return CLIENTS_DIR / client_slug / "feedback.json"


def _load_global() -> dict:
    """Загружает глобальный feedback."""
    if GLOBAL_FEEDBACK_PATH.exists():
        try:
            return json.loads(GLOBAL_FEEDBACK_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"agents": {}, "total_runs": 0}


def _save_global(data: dict):
    """Сохраняет глобальный feedback."""
    GLOBAL_FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_FEEDBACK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_score(my_output: dict) -> float:
    """
    Универсальный парсер score из my_output любого QA-агента.
    Поддерживает: blocks (A12), otk_checklist (A16), status, прямой score.
    """
    # Прямой score
    if "score" in my_output:
        try:
            return _apply_score_ceiling(float(my_output["score"]))
        except (ValueError, TypeError):
            pass

    # OTK чеклист: "12/12" → 10.0, "10/12" → 8.3
    checklist = my_output.get("otk_checklist", "")
    if checklist and "/" in str(checklist):
        try:
            parts = str(checklist).split("/")
            return _apply_score_ceiling(round(10.0 * int(parts[0]) / int(parts[1]), 1))
        except (ValueError, ZeroDivisionError):
            pass

    # Статус
    status = my_output.get("status", "").upper()
    status_map = {"READY": 9.0, "OK": 8.0, "INCOMPLETE": 5.0,
                  "PARTIAL": 5.0, "FAIL": 2.0, "ERROR": 2.0}
    if status in status_map:
        return _apply_score_ceiling(status_map[status])

    # Blocks (формат A12) — считаем средний по всем блокам
    blocks = my_output.get("blocks", {})
    if blocks:
        scores = []
        for bd in blocks.values():
            if isinstance(bd, dict):
                checks = bd.get("checks", 0)
                passed = bd.get("pass", 0)
                if checks > 0:
                    scores.append(10 * passed / checks)
        if scores:
            return _apply_score_ceiling(round(sum(scores) / len(scores), 1))

    return 5.0  # нейтральный дефолт


def _apply_score_ceiling(score: float) -> float:
    """
    Потолок детерминированного score: максимум 6.0.

    Физика мира: скрипт не может поставить выше 6.0.
    6.0 = «выжил, сделал по ТЗ» — это честный максимум без живого взгляда.
    Выше 6.0 — только Metrics Daemon (реальный зритель) или субъективный QA.

    Не трогает:
      - real_viral_score Демона (считается отдельно в metrics_daemon.py)
      - Виктора (он ставит вердикт, не цифру)
    """
    return round(min(6.0, score), 2)


def _build_block_map(agent_ids: list) -> dict:
    """
    Строит маппинг блоков QA-агента на агентов цеха.

    Возвращает: {block_name: [agent_ids]}

    Работает для всех цехов без хардкода:
      turbo        A01..A05 — QA A05, chain_check 7 пунктов
      video_long   A01..A12 — QA A12 Боб, named blocks
      video_shorts A01..A12 — QA A12 Тамб Том, named blocks
      social_mix   A01..A12 — QA A12 Клавдия, named blocks

    Стратегия:
    1. Каждый агент получает block = его ID (A01, A02 ...) — всегда работает.
    2. Именованные блоки из контрактов маппятся на реальных агентов цеха.
       Если агента нет в agent_ids (например A06 в turbo) — берётся ближайший.
    3. chain_check пункты turbo маппятся с fallback: A06->A03, A10->A02.
    """
    if not agent_ids:
        return {}

    result = {}

    # Схема 1: block_name = agent_id (универсально для всех цехов)
    for aid in agent_ids:
        result[aid] = [aid]
        result[aid.lower()] = [aid]

    # Схема 2: именованные блоки с fallback для коротких цехов (turbo = A01..A05)
    # Порядок в списке = приоритет. Берётся первый who in agent_set.
    _named = {
        # визуал / кадры
        "visual":       ["A06", "A03"],
        "visuals":      ["A06", "A03"],
        "frames":       ["A06", "A03"],
        "image":        ["A06", "A03"],
        # видео / клипы
        "video":        ["A08", "A03"],
        "vfx":          ["A08", "A03"],
        "clips":        ["A08", "A03"],
        # звук / аудио
        "sound":        ["A10", "A02"],
        "audio":        ["A10", "A02"],
        "music":        ["A10", "A02"],
        # монтаж
        "motion":       ["A09", "A04"],
        "edit":         ["A09", "A04"],
        "montage":      ["A09", "A04"],
        # шрифты / субтитры
        "typography":   ["A07", "A04"],
        "captions":     ["A07", "A04"],
        "subtitles":    ["A07", "A04"],
        # раскадровка
        "storyboard":   ["A05", "A03"],
        "storyboards":  ["A05", "A03"],
        # стратегия / сценарий
        "strategy":     ["A01"],
        "concept":      ["A01"],
        "hook":         ["A02", "A01"],
        "script":       ["A03", "A02"],
        "narrative":    ["A03", "A02"],
        # thumbnail / smm / seo
        "thumbnail":    ["A11", "A04"],
        "smm":          ["A11", "A04"],
        "seo":          ["A04"],
        # turbo chain_check пункты (с fallback для 5-агентного цеха)
        "frames_have_path":      ["A06", "A03"],
        "frames_self_review":    ["A06", "A03"],
        "clips_have_video_path": ["A08", "A03"],
        "clips_clip_review":     ["A08", "A03"],
        "audio_has_path":        ["A10", "A02"],
        "audio_review":          ["A10", "A02"],
        "timings_match":         ["A04", "A09"],
        # social_mix специфичные
        "layout":        ["A05"],
        "engagement":    ["A09", "A04"],
        "analytics":     ["A10", "A04"],
        "inspection":    ["A11", "A04"],
    }

    agent_set = set(agent_ids)
    for block_name, priority_agents in _named.items():
        # Берём первого кто есть в agent_set
        valid = [a for a in priority_agents if a in agent_set]
        if valid:
            result[block_name] = [valid[0]]

    return result


def save_feedback(client_slug: str, arthur_result: str | dict, slot_id: str = "", agent_ids: list = None):
    """
    Парсит результат Артура и сохраняет оценки агентов.
    
    Артур выдаёт blocks с checks/pass/warn/fail для каждого блока.
    Мы маппим блоки на агентов и сохраняем.
    """
    if client_slug == "_sandbox":
        return
    
    # Парсим данные Артура
    if isinstance(arthur_result, str):
        try:
            # Ищем JSON в тексте
            import re
            m = re.search(r'SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END', 
                         arthur_result, re.DOTALL)
            if m:
                raw = m.group(1).strip().strip('`').strip()
                if raw.startswith('json'):
                    raw = raw[4:].strip()
                data = json.loads(raw)
            else:
                return
        except (json.JSONDecodeError, Exception):
            return
    else:
        data = arthur_result
    
    my_output = data.get("my_output", {})
    blocks = my_output.get("blocks", {})
    overall = my_output.get("overall_status", "UNKNOWN")
    warnings = my_output.get("warnings", [])
    critical = my_output.get("critical_issues", [])

    # ══ Универсальный fallback: если нет blocks — распределяем общий score ══
    if not blocks and agent_ids:
        universal_score = _extract_score(my_output)
        feedback = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "overall_status": overall or ("READY" if universal_score >= 8 else "OK"),
            "agents": {
                aid: {"score": universal_score, "problems": [], "blocks_checked": ["universal"]}
                for aid in agent_ids
            },
        }
        fp = _feedback_path(client_slug)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
        _update_global(feedback, slot_id=slot_id)
        print(f"[FEEDBACK] Universal score={universal_score} → {len(agent_ids)} агентов")
        return
    
    # Динамический маппинг блоков → агенты
    # Строится из agent_ids если передан, иначе fallback на legacy-хардкод
    BLOCK_TO_AGENTS = _build_block_map(agent_ids or [])
    
    # Собираем оценки per agent
    agent_scores = {}
    
    for block_name, block_data in blocks.items():
        if not isinstance(block_data, dict):
            continue
        
        checks = block_data.get("checks", 0)
        passed = block_data.get("pass", 0)
        warn = block_data.get("warn", 0)
        fail = block_data.get("fail", 0)
        details = block_data.get("details", [])
        
        # Оценка блока: 10 * (pass / checks) если checks > 0
        score = round(10 * passed / checks, 1) if checks > 0 else 5.0
        
        # Проблемы из details
        problems = []
        for d in details:
            if isinstance(d, dict):
                status = d.get("status", "")
                desc = d.get("description", d.get("check", ""))
                if status in ("FAIL", "WARNING", "❌", "⚠️") and desc:
                    problems.append(desc)
            elif isinstance(d, str):
                problems.append(d)
        
        # Распределяем по агентам
        agents = BLOCK_TO_AGENTS.get(block_name, [])
        for agent_id in agents:
            if agent_id not in agent_scores:
                agent_scores[agent_id] = {
                    "score": [],
                    "problems": [],
                    "blocks": [],
                }
            agent_scores[agent_id]["score"].append(score)
            agent_scores[agent_id]["problems"].extend(problems[:3])  # max 3 per block
            agent_scores[agent_id]["blocks"].append(block_name)
    
    # Финализируем: средняя оценка per agent
    feedback = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overall_status": overall,
        "agents": {},
    }
    
    for agent_id, data in agent_scores.items():
        scores = data["score"]
        avg = round(sum(scores) / len(scores), 1) if scores else 5.0
        feedback["agents"][agent_id] = {
            "score": avg,
            "problems": data["problems"][:5],  # max 5 проблем
            "blocks_checked": data["blocks"],
        }
    
    # Добавляем глобальные проблемы
    if critical:
        for c in critical[:5]:
            desc = c.get("description", str(c)) if isinstance(c, dict) else str(c)
            # Пробуем определить виновного агента
            for agent_id in ["A04", "A05", "A10", "A11"]:
                if agent_id.lower() in desc.lower() or any(
                    name in desc.lower() 
                    for name in ["софи", "рина", "нова", "рэй", "лана", "оливер", "люми", "бруно"]
                ):
                    if agent_id not in feedback["agents"]:
                        feedback["agents"][agent_id] = {"score": 3.0, "problems": [], "blocks_checked": []}
                    feedback["agents"][agent_id]["problems"].append(f"CRITICAL: {desc}")
    
    # Сохраняем клиентский
    fp = _feedback_path(client_slug)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Обновляем глобальный (студийный) feedback
    _update_global(feedback, slot_id=slot_id)
    
    print(f"[FEEDBACK] Сохранено для {len(feedback['agents'])} агентов → {fp}")
    for aid, fd in feedback["agents"].items():
        emoji = "✅" if fd["score"] >= 8 else "⚠️" if fd["score"] >= 5 else "❌"
        print(f"  {emoji} {aid}: {fd['score']}/10 ({len(fd['problems'])} замечаний)")


def _update_global(run_feedback: dict, slot_id: str = ""):
    """Обновляет глобальный feedback — накапливает типичные проблемы из всех проектов."""
    gf = _load_global()
    gf["total_runs"] = gf.get("total_runs", 0) + 1
    
    for agent_id, run_data in run_feedback.get("agents", {}).items():
        if agent_id not in gf["agents"]:
            gf["agents"][agent_id] = {
                "runs": 0,
                "avg_score": 0.0,
                "total_score": 0.0,
                "recurring_problems": [],
                "last_problems": [],
                "streak": 0,        # положительный = серия побед, отрицательный = серия провалов
                "best_streak": 0,   # рекорд
                "stars": 0,         # звёзды (streak >= 3 = +1 звезда)
            }
        
        ga = gf["agents"][agent_id]
        ga["runs"] += 1
        ga["total_score"] += run_data.get("score", 5.0)
        ga["avg_score"] = round(ga["total_score"] / ga["runs"], 1)
        ga["last_problems"] = run_data.get("problems", [])[:3]
        
        # Streak logic
        score = run_data.get("score", 5.0)
        if score >= 8:
            # Победа
            if ga["streak"] >= 0:
                ga["streak"] += 1
            else:
                ga["streak"] = 1  # сброс серии провалов
            # Звезда за серию из 3 побед
            if ga["streak"] >= 3 and ga["streak"] % 3 == 0:
                ga["stars"] = ga.get("stars", 0) + 1
                print(f"  ⭐ {agent_id}: ЗВЕЗДА! (streak {ga['streak']}, всего {ga['stars']} звёзд)")
        elif score < 5:
            # Провал
            if ga["streak"] <= 0:
                ga["streak"] -= 1
            else:
                ga["streak"] = -1  # сброс серии побед
            # Теряем звезду за серию из 3 провалов
            if ga["streak"] <= -3 and ga["streak"] % 3 == 0 and ga.get("stars", 0) > 0:
                ga["stars"] = ga["stars"] - 1
                print(f"  💀 {agent_id}: звезда погасла! (streak {ga['streak']}, осталось {ga['stars']})")
        else:
            # Середина — streak не меняется, но и не растёт
            pass
        
        ga["best_streak"] = max(ga.get("best_streak", 0), ga["streak"])
        
        # Накапливаем recurring — если проблема повторяется 2+ раз
        for problem in run_data.get("problems", []):
            # Упрощаем текст для сравнения
            short = problem[:80].lower().strip()
            found = False
            for rp in ga["recurring_problems"]:
                if rp["text"][:60].lower() == short[:60]:
                    rp["count"] += 1
                    found = True
                    break
            if not found:
                ga["recurring_problems"].append({"text": problem[:120], "count": 1})
        
        # Оставляем только топ-5 recurring (сортируем по частоте)
        ga["recurring_problems"] = sorted(
            ga["recurring_problems"], key=lambda x: x["count"], reverse=True
        )[:5]
    
    # ══ slot_id binding: помним что происходило в каком цехе ══
    if slot_id:
        if "slots" not in gf:
            gf["slots"] = {}
        if slot_id not in gf["slots"]:
            gf["slots"][slot_id] = {"runs": 0, "agents": {}}
        gf["slots"][slot_id]["runs"] = gf["slots"][slot_id].get("runs", 0) + 1
        for _aid, _rdata in run_feedback.get("agents", {}).items():
            _sl_agents = gf["slots"][slot_id]["agents"]
            if _aid not in _sl_agents:
                _sl_agents[_aid] = {"runs": 0, "avg_score": 0.0, "total_score": 0.0, "last_problems": []}
            _sla = _sl_agents[_aid]
            _sla["runs"] += 1
            _sla["total_score"] = _sla.get("total_score", 0.0) + _rdata.get("score", 5.0)
            _sla["avg_score"] = round(_sla["total_score"] / _sla["runs"], 1)
            _sla["last_problems"] = _rdata.get("problems", [])[:3]
    # ══ end slot binding ══

    _save_global(gf)
    print(f"[FEEDBACK] Глобальный обновлён: {gf['total_runs']} ранов")


def get_feedback(client_slug: str, worker_id: str) -> str:
    """
    Возвращает текст обратной связи для агента.
    Приоритет: клиентский feedback → глобальный (студийный).
    """
    parts = []
    
    # 1. Клиентский feedback (конкретный проект)
    if client_slug and client_slug != "_sandbox":
        fp = _feedback_path(client_slug)
        if fp.exists():
            try:
                feedback = json.loads(fp.read_text(encoding="utf-8"))
                agent_data = feedback.get("agents", {}).get(worker_id)
                if agent_data:
                    score = agent_data.get("score", 5.0)
                    problems = agent_data.get("problems", [])
                    date = feedback.get("date", "")
                    if score < 9 or problems:
                        parts.append(f"=== ⚠️ ОБРАТНАЯ СВЯЗЬ ОТ QA (прошлый ран {date}) ===")
                        parts.append(f"Твоя оценка: {score}/10")
                        if problems:
                            parts.append("Замечания:")
                            for i, p in enumerate(problems[:5], 1):
                                parts.append(f"  {i}. {p}")
                        if score < 5:
                            parts.append("⛔ Низкая оценка! Будь особенно внимателен.")
            except Exception:
                pass
    
    # 2. Глобальный feedback (уроки из всех проектов)
    gf = _load_global()
    ga = gf.get("agents", {}).get(worker_id)
    if ga and ga.get("runs", 0) > 0:
        avg = ga.get("avg_score", 5.0)
        streak = ga.get("streak", 0)
        stars = ga.get("stars", 0)
        recurring = [rp for rp in ga.get("recurring_problems", []) if rp.get("count", 0) >= 2]
        
        if not parts:
            parts.append("=== СТУДИЙНАЯ ОБРАТНАЯ СВЯЗЬ ===")
        else:
            parts.append("")
        
        parts.append(f"📊 Средний балл за {ga['runs']} проектов: {avg}/10")
        
        # Streak & Stars
        if stars > 0:
            stars_display = "⭐" * min(stars, 5)
            parts.append(f"🏆 Твои звёзды: {stars_display} ({stars})")
        
        if streak >= 3:
            parts.append(f"🔥 Серия побед: {streak} подряд! Держи планку — ты лучший в команде.")
        elif streak >= 1:
            parts.append(f"✅ Последний ран: хорошо. Продолжай в том же духе.")
        elif streak <= -3:
            parts.append(f"💀 Серия провалов: {abs(streak)} подряд. СРОЧНО исправься — следующий провал = потеря звезды.")
        elif streak <= -1:
            parts.append(f"⚠️ Последний ран: плохо. Внимательно прочитай замечания.")
        
        if recurring:
            parts.append("Повторяющиеся проблемы (ОБЯЗАТЕЛЬНО ИСПРАВЬ):")
            for rp in recurring[:3]:
                parts.append(f"  ⚠️ [{rp['count']}x] {rp['text']}")
    
    if parts:
        parts.append("=== КОНЕЦ ОБРАТНОЙ СВЯЗИ ===\n")
        return "\n".join(parts)
    
    return ""


def get_feedback_summary(client_slug: str) -> str:
    """Краткая сводка для ДЖема / логов."""
    lines = []
    
    # Клиентский
    if client_slug and client_slug != "_sandbox":
        fp = _feedback_path(client_slug)
        if fp.exists():
            try:
                feedback = json.loads(fp.read_text(encoding="utf-8"))
                agents = feedback.get("agents", {})
                if agents:
                    lines.append(f"📊 Feedback от {feedback.get('date', '?')}:")
                    for aid in sorted(agents):
                        fd = agents[aid]
                        emoji = "✅" if fd["score"] >= 8 else "⚠️" if fd["score"] >= 5 else "❌"
                        lines.append(f"  {emoji} {aid}: {fd['score']}/10")
            except Exception:
                pass
    
    # Глобальный — streak info
    gf = _load_global()
    if gf.get("total_runs", 0) > 0:
        lines.append(f"\n🏢 Студия: {gf['total_runs']} проектов")
        for aid in sorted(gf.get("agents", {})):
            ga = gf["agents"][aid]
            streak = ga.get("streak", 0)
            stars = ga.get("stars", 0)
            stars_str = "⭐" * min(stars, 5) if stars > 0 else ""
            streak_str = f"🔥{streak}" if streak >= 3 else f"💀{streak}" if streak <= -3 else ""
            if stars_str or streak_str:
                lines.append(f"  {aid}: {ga['avg_score']}/10 {stars_str} {streak_str}")
    
    return "\n".join(lines)
