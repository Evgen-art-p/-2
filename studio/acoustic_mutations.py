# studio/acoustic_mutations.py
"""
🎧 ЛАВОЧКА АРТЕФАКТОВ — Акустические мутации Грондхейма

Два уровня хранения:
  LOCAL  → runs/{client}/{run_id}/acoustic_mutations/
           Личный след проекта. Черновики художника.
           Умирают локально — не всё обязано становиться культурой.

  GLOBAL → studio/acoustic_mutations/
           Чердак студии. Коллективное акустическое бессознательное.
           Попадает через акт признания — не автоматически.

Каждая мутация = самостоятельная сущность с биографией:
  mut_{id}/
    audio.mp3         ← сам файл (или .wav/.ogg)
    metadata.json     ← traits, origin, cultural_weight
    events.jsonl      ← immutable event log (created, reflected, rejected, promoted, reused)

Promotion — событие, не флаг.
Conflict Sam vs Arthur — записывается в events.jsonl и становится историей.
Чердак намеренно хаотичен — это не sterile asset database.

Спринт 26 · Брат (Claude) + Лока
"""

import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════
# ПУТИ
# ═══════════════════════════════════════════════════════

GLOBAL_MUTATIONS_DIR = Path("studio/acoustic_mutations")
RUNS_DIR             = Path("runs")

# Признанные акустические трейты для индексации
KNOWN_TRAITS = [
    "wet", "unstable", "clipped", "broken_loop", "ghost_voice",
    "metallic_resonance", "tape_hiss", "overdriven", "dark_ambient",
    "industrial", "glitch", "hollow", "reversed", "compressed",
    "lo_fi", "saturated", "pitch_drift", "echo_artifact", "noise_floor",
]

# Мифология — накапливается автоматически из событий
MYTHOLOGY_THRESHOLDS = {
    "legendary":  14,   # reuse_count >= 14
    "haunting":   7,    # reuse_count >= 7 + есть ghost_voice или echo_artifact
    "cursed":     3,    # promoted_anyway + arthur_says_reject несколько раз
    "forgotten":  0,    # не использован > 90 дней
    "rediscovered": 0,  # reuse после 60+ дней тишины
}


# ═══════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ ID
# ═══════════════════════════════════════════════════════

def _gen_mut_id() -> str:
    """Генерирует уникальный ID мутации: mut_{4hex}_{timestamp}."""
    ts = datetime.now().strftime("%y%m%d%H%M")
    rnd = uuid.uuid4().hex[:4]
    return f"mut_{rnd}_{ts}"


# ═══════════════════════════════════════════════════════
# ЗАПИСЬ СОБЫТИЯ (immutable log)
# ═══════════════════════════════════════════════════════

def _append_event(events_path: Path, event: dict):
    """Добавляет событие в events.jsonl — только append, никогда не перезаписываем."""
    events_path.parent.mkdir(parents=True, exist_ok=True)
    event["ts"] = datetime.now().isoformat()
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_events(events_path: Path) -> list[dict]:
    """Читает все события из events.jsonl."""
    if not events_path.exists():
        return []
    events = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


# ═══════════════════════════════════════════════════════
# МИФОЛОГИЯ — автоматическое накопление
# ═══════════════════════════════════════════════════════

def _compute_mythology(metadata: dict, events: list[dict]) -> list[str]:
    """
    Вычисляет мифологические теги мутации на основе истории.
    Не хардкод — живое накопление из событий.
    """
    tags = []
    traits = metadata.get("traits", [])
    reuse_count = metadata.get("reuse_count", 0)

    # Legendary — много раз переиспользовали
    if reuse_count >= MYTHOLOGY_THRESHOLDS["legendary"]:
        tags.append("legendary")
    elif reuse_count >= MYTHOLOGY_THRESHOLDS["haunting"]:
        if "ghost_voice" in traits or "echo_artifact" in traits:
            tags.append("haunting")

    # Cursed — Сэм продвигал вопреки Артуру несколько раз
    conflicts = [e for e in events
                 if e.get("type") == "promoted_to_global"
                 and e.get("arthur_rejected") is True]
    if len(conflicts) >= 2:
        tags.append("cursed")

    # Forgotten — не использован давно
    last_reuse = metadata.get("last_reuse_ts")
    if last_reuse:
        try:
            delta = (datetime.now() - datetime.fromisoformat(last_reuse)).days
            if delta > 90:
                tags.append("forgotten")
        except ValueError:
            pass
    elif reuse_count == 0:
        created_ts = metadata.get("created_ts")
        if created_ts:
            try:
                delta = (datetime.now() - datetime.fromisoformat(created_ts)).days
                if delta > 90:
                    tags.append("forgotten")
            except ValueError:
                pass

    # Rediscovered — reuse после долгого перерыва
    reuse_events = [e for e in events if e.get("type") == "reused"]
    if len(reuse_events) >= 2:
        prev_ts = reuse_events[-2].get("ts", "")
        last_ts = reuse_events[-1].get("ts", "")
        if prev_ts and last_ts:
            try:
                gap = (datetime.fromisoformat(last_ts) -
                       datetime.fromisoformat(prev_ts)).days
                if gap > 60:
                    tags.append("rediscovered")
            except ValueError:
                pass

    return tags


# ═══════════════════════════════════════════════════════
# LOCAL — создание мутации в проекте клиента
# ═══════════════════════════════════════════════════════

def save_local_mutation(
    audio_file: Path,
    client_slug: str,
    run_id: str,
    traits: list[str],
    intent: str = "",
    agent_id: str = "A10",
    self_reflection: dict | None = None,
) -> dict:
    """
    Сохраняет мутацию в локальный архив проекта.

    audio_file:      путь к аудиофайлу (mp3/wav/ogg)
    client_slug:     идентификатор клиента
    run_id:          идентификатор рана
    traits:          акустические трейты ["clipped", "metallic_resonance", ...]
    intent:          изначальный замысел ("industrial horror ambience")
    agent_id:        кто создал (обычно A10 Сэм)
    self_reflection: dict из chain_data Сэма (mood_match, would_reuse_fragment, ...)

    Возвращает metadata dict созданной мутации.
    """
    mut_id = _gen_mut_id()
    local_dir = RUNS_DIR / client_slug / run_id / "acoustic_mutations" / mut_id
    local_dir.mkdir(parents=True, exist_ok=True)

    # Копируем аудио
    import shutil
    dest_audio = local_dir / audio_file.name
    if audio_file.exists():
        shutil.copy2(audio_file, dest_audio)
    else:
        dest_audio = None

    # Валидируем трейты
    valid_traits = [t for t in traits if t in KNOWN_TRAITS]
    unknown = [t for t in traits if t not in KNOWN_TRAITS]
    if unknown:
        print(f"[МУТАЦИИ] ⚠ Неизвестные трейты (добавлены как есть): {unknown}")
        valid_traits.extend(unknown)  # не теряем — чердак принимает всё

    now = datetime.now().isoformat()
    metadata = {
        "mut_id":          mut_id,
        "scope":           "local",
        "audio_file":      audio_file.name if dest_audio else None,
        "traits":          valid_traits,
        "intent":          intent,
        "created_by":      agent_id,
        "created_ts":      now,
        "origin": {
            "client":      client_slug,
            "run_id":      run_id,
            "local_path":  str(local_dir / audio_file.name) if dest_audio else "",
        },
        "reuse_count":     0,
        "reused_in":       [],
        "promoted_global": False,
        "cultural_weight": 0.0,
        "mythology_tags":  [],
        "last_reuse_ts":   None,
    }

    # Сохраняем metadata
    (local_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Первое событие
    events_path = local_dir / "events.jsonl"
    _append_event(events_path, {
        "type":       "created",
        "by":         agent_id,
        "local_path": str(dest_audio) if dest_audio else "",
        "intent":     intent,
        "traits":     valid_traits,
    })

    # Self-reflection Сэма
    if self_reflection:
        _append_event(events_path, {
            "type":            "self_reflection",
            "by":              agent_id,
            **self_reflection,
        })

    print(f"[МУТАЦИИ] 🎧 Создана локальная мутация {mut_id}: {valid_traits}")
    return metadata


# ═══════════════════════════════════════════════════════
# QA ОЦЕНКА — внешний слух Артура
# ═══════════════════════════════════════════════════════

def record_qa_judgment(
    mut_id: str,
    client_slug: str,
    run_id: str,
    qa_agent_id: str,
    qa_score: float,
    qa_comment: str,
    rejected: bool,
    scope: str = "local",
) -> dict:
    """
    Записывает оценку QA-агента (Артура) в events.jsonl мутации.

    Возвращает расхождение между self_reflection Сэма и QA.
    Это золото для Character Drift.
    """
    mut_dir = _find_mut_dir(mut_id, client_slug, run_id, scope)
    if not mut_dir:
        print(f"[МУТАЦИИ] ⚠ Мутация {mut_id} не найдена")
        return {}

    events_path = mut_dir / "events.jsonl"
    events = _read_events(events_path)

    # Находим self_reflection Сэма если есть
    sam_ref = next((e for e in events if e.get("type") == "self_reflection"), None)
    sam_mood_match = sam_ref.get("mood_match", None) if sam_ref else None

    # Drift signal — расхождение оценок
    drift = {}
    if sam_mood_match is not None:
        gap = abs(sam_mood_match - qa_score / 10.0)
        drift = {
            "sam_said":  round(sam_mood_match, 2),
            "arthur_said": round(qa_score / 10.0, 2),
            "gap":       round(gap, 2),
            "pattern":   "Сэм переоценивает" if sam_mood_match > qa_score / 10.0 + 0.2
                         else "Сэм недооценивает" if sam_mood_match < qa_score / 10.0 - 0.2
                         else "близко",
        }

    event = {
        "type":       "qa_judgment",
        "by":         qa_agent_id,
        "qa_score":   qa_score,
        "qa_comment": qa_comment,
        "rejected":   rejected,
    }
    if drift:
        event["drift_signal"] = drift

    _append_event(events_path, event)

    # Обновляем metadata
    meta_path = mut_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["last_qa_score"] = qa_score
        meta["last_qa_rejected"] = rejected
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if rejected:
        print(f"[МУТАЦИИ] 🗡 {mut_id}: Артур отклонил (score={qa_score}), {drift.get('pattern','')}")
    else:
        print(f"[МУТАЦИИ] ✅ {mut_id}: Артур принял (score={qa_score})")

    return drift


# ═══════════════════════════════════════════════════════
# PROMOTION — акт признания, не флаг
# ═══════════════════════════════════════════════════════

def promote_to_global(
    mut_id: str,
    client_slug: str,
    run_id: str,
    promoted_by: str,
    reason: str,
    rarity_score: float = 0.5,
    override_arthur: bool = False,
) -> dict | None:
    """
    Промоутит мутацию с локального уровня на Чердак студии.

    promoted_by:     ID агента (A10=Сэм, A12=Артур, или оба независимо)
    reason:          почему — обязательно, это история
    rarity_score:    0.0–1.0, субъективная редкость
    override_arthur: Сэм продвигает вопреки отклонению Артура

    Промоушн — событие, не флаг. Оба могут промоутить независимо.
    Конфликт "sam_wants но arthur_rejected" сохраняется в events.jsonl.
    """
    local_dir = _find_mut_dir(mut_id, client_slug, run_id, scope="local")
    if not local_dir:
        print(f"[МУТАЦИИ] ⚠ Промоушн: {mut_id} не найдена локально")
        return None

    meta_path = local_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # Читаем события — был ли rejection от Артура
    events = _read_events(local_dir / "events.jsonl")
    arthur_rejected = any(
        e.get("type") == "qa_judgment" and e.get("rejected") is True
        for e in events
    )

    # Создаём директорию на чердаке
    GLOBAL_MUTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    global_dir = GLOBAL_MUTATIONS_DIR / mut_id
    global_dir.mkdir(parents=True, exist_ok=True)

    # Копируем аудио если есть
    import shutil
    audio_name = meta.get("audio_file")
    if audio_name:
        local_audio = local_dir / audio_name
        if local_audio.exists():
            shutil.copy2(local_audio, global_dir / "audio.mp3")

    # Обновляем metadata для глобального
    global_meta = dict(meta)
    global_meta["scope"]           = "global"
    global_meta["promoted_global"] = True
    global_meta["promoted_by"]     = promoted_by
    global_meta["promoted_ts"]     = datetime.now().isoformat()
    global_meta["promotion_reason"]= reason
    global_meta["rarity_score"]    = round(rarity_score, 2)
    global_meta["promoted_anyway"] = override_arthur and arthur_rejected
    global_meta["cultural_weight"] = round(rarity_score * 0.5, 3)  # начальный вес

    # Мифология при создании
    global_meta["mythology_tags"]  = _compute_mythology(global_meta, events)

    (global_dir / "metadata.json").write_text(
        json.dumps(global_meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Копируем events.jsonl с локального + добавляем событие promotion
    local_events_path = local_dir / "events.jsonl"
    global_events_path = global_dir / "events.jsonl"
    if local_events_path.exists():
        shutil.copy2(local_events_path, global_events_path)

    _append_event(global_events_path, {
        "type":            "promoted_to_global",
        "by":              promoted_by,
        "reason":          reason,
        "rarity_score":    rarity_score,
        "arthur_rejected": arthur_rejected,
        "promoted_anyway": override_arthur and arthur_rejected,
    })

    # Обновляем локальный флаг
    meta["promoted_global"] = True
    meta["global_mut_id"]   = mut_id
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_event(local_dir / "events.jsonl", {
        "type":   "promoted_to_global",
        "by":     promoted_by,
        "reason": reason,
    })

    conflict_note = " (вопреки Артуру!)" if override_arthur and arthur_rejected else ""
    print(f"[МУТАЦИИ] 🏚 {mut_id} → ЧЕРДАК{conflict_note}: {reason[:60]}")
    return global_meta


# ═══════════════════════════════════════════════════════
# ПЕРЕИСПОЛЬЗОВАНИЕ
# ═══════════════════════════════════════════════════════

def record_reuse(
    mut_id: str,
    by_agent: str,
    project: str,
    outcome: str = "unknown",
    scope: str = "global",
) -> None:
    """
    Записывает факт переиспользования мутации.
    Обновляет reuse_count, cultural_weight, last_reuse_ts.
    Пересчитывает мифологию.
    """
    mut_dir = _find_mut_dir(mut_id, scope=scope)
    if not mut_dir:
        print(f"[МУТАЦИИ] ⚠ record_reuse: {mut_id} не найдена")
        return

    events_path = mut_dir / "events.jsonl"
    _append_event(events_path, {
        "type":    "reused",
        "by":      by_agent,
        "project": project,
        "outcome": outcome,
    })

    meta_path = mut_dir / "metadata.json"
    if not meta_path.exists():
        return

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["reuse_count"]   = meta.get("reuse_count", 0) + 1
    meta["last_reuse_ts"] = datetime.now().isoformat()
    meta.setdefault("reused_in", []).append({
        "project": project,
        "by":      by_agent,
        "outcome": outcome,
        "ts":      datetime.now().isoformat(),
    })

    # Cultural weight растёт с каждым use, но медленно
    meta["cultural_weight"] = round(
        min(1.0, meta.get("cultural_weight", 0) + 0.07), 3
    )

    # Пересчёт мифологии
    events = _read_events(events_path)
    meta["mythology_tags"] = _compute_mythology(meta, events)

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[МУТАЦИИ] ♻️ {mut_id} переиспользован ({meta['reuse_count']}x) → {outcome}")


# ═══════════════════════════════════════════════════════
# ПОИСК НА ЧЕРДАКЕ
# ═══════════════════════════════════════════════════════

def search_mutations(
    traits: list[str] | None = None,
    mythology: list[str] | None = None,
    min_cultural_weight: float = 0.0,
    scope: str = "global",
    limit: int = 10,
) -> list[dict]:
    """
    Ищет мутации по трейтам или мифологии.

    Агент Сэм ищет: search_mutations(traits=["unstable", "metallic_resonance"])
    Агент Феликс ищет: search_mutations(mythology=["legendary"])

    scope="global" → только Чердак
    scope="local"  → нужно передать client_slug и run_id (не реализовано здесь)

    Возвращает отсортированный список по cultural_weight (desc).
    """
    search_dir = GLOBAL_MUTATIONS_DIR if scope == "global" else GLOBAL_MUTATIONS_DIR
    if not search_dir.exists():
        return []

    results = []
    for mut_dir in search_dir.iterdir():
        if not mut_dir.is_dir():
            continue
        meta_path = mut_dir / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            continue

        # Фильтрация
        if traits:
            if not any(t in meta.get("traits", []) for t in traits):
                continue
        if mythology:
            if not any(m in meta.get("mythology_tags", []) for m in mythology):
                continue
        if meta.get("cultural_weight", 0.0) < min_cultural_weight:
            continue

        results.append(meta)

    # Сортировка: cultural_weight desc, rarity_score desc
    results.sort(
        key=lambda m: (m.get("cultural_weight", 0), m.get("rarity_score", 0)),
        reverse=True,
    )
    return results[:limit]


def format_mutations_for_agent(
    results: list[dict],
    agent_name: str = "Агент",
) -> str:
    """
    Форматирует найденные мутации для промпта агента.
    Вызывается когда агент приходит на Чердак.
    """
    if not results:
        return "На чердаке тихо сегодня — подходящих мутаций не нашлось."

    lines = [
        f"=== 🏚 ЧЕРДАК СТУДИИ · Лавочка Артефактов ===",
        f"Для тебя, {agent_name}, найдено {len(results)} акустических мутаций:\n",
    ]

    for m in results:
        mut_id    = m.get("mut_id", "?")
        traits    = ", ".join(m.get("traits", [])[:4])
        intent    = m.get("intent", "")
        reuse     = m.get("reuse_count", 0)
        weight    = m.get("cultural_weight", 0)
        myth      = m.get("mythology_tags", [])
        rarity    = m.get("rarity_score", 0)
        promoted_anyway = m.get("promoted_anyway", False)

        line = f"🎧 {mut_id}"
        if myth:
            line += f" [{', '.join(myth)}]"
        lines.append(line)
        lines.append(f"   Трейты: {traits}")
        if intent:
            lines.append(f"   Замысел: {intent[:80]}")
        lines.append(f"   Использован: {reuse}x · Культурный вес: {weight:.2f} · Редкость: {rarity:.2f}")
        if promoted_anyway:
            lines.append(f"   ⚡ Продвинут вопреки отклонению QA — спорный артефакт")
        audio = m.get("audio_file") or "audio.mp3"
        lines.append(f"   Файл: studio/acoustic_mutations/{mut_id}/{audio}")
        lines.append("")

    lines.append("Используй mut_id при переиспользовании — система запомнит.")
    lines.append("=== КОНЕЦ ЧЕРДАКА ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# HELPER — найти директорию мутации
# ═══════════════════════════════════════════════════════

def _find_mut_dir(
    mut_id: str,
    client_slug: str = "",
    run_id: str = "",
    scope: str = "global",
) -> Path | None:
    """Находит директорию мутации по scope и ID."""
    if scope == "global":
        p = GLOBAL_MUTATIONS_DIR / mut_id
        return p if p.is_dir() else None
    elif scope == "local" and client_slug and run_id:
        p = RUNS_DIR / client_slug / run_id / "acoustic_mutations" / mut_id
        return p if p.is_dir() else None
    # Ищем по всем клиентам (медленно, только для поиска)
    if scope == "local":
        for client_dir in RUNS_DIR.iterdir():
            if not client_dir.is_dir():
                continue
            for run_dir in client_dir.iterdir():
                p = run_dir / "acoustic_mutations" / mut_id
                if p.is_dir():
                    return p
    return None


# ═══════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С CITY_WALKER — посещение Чердака
# ═══════════════════════════════════════════════════════

def attic_visit(
    agent_name: str,
    agent_traits_interest: list[str] | None = None,
    top_n: int = 5,
) -> str:
    """
    Агент приходит на Чердак во время прогулки.
    Возвращает контекст найденных мутаций для sensory_memory.

    Вызывается из city_walker.py когда chosen_type == "workshop".
    """
    if not GLOBAL_MUTATIONS_DIR.exists():
        return f"{agent_name} зашёл на Чердак — пока пусто, мутаций ещё нет."

    # Если нет конкретных интересов — берём самые культурные
    if agent_traits_interest:
        results = search_mutations(traits=agent_traits_interest, limit=top_n)
        if not results:
            results = search_mutations(limit=top_n)
    else:
        results = search_mutations(limit=top_n)

    # Легендарные всегда показываем
    legendary = search_mutations(mythology=["legendary"], limit=2)
    for leg in legendary:
        if leg not in results:
            results.insert(0, leg)
    results = results[:top_n]

    if not results:
        return (
            f"{agent_name} бродил по Чердаку — нашёл старые коробки и запах озона. "
            f"Ещё нет артефактов. Но место уже живёт своей историей."
        )

    return format_mutations_for_agent(results, agent_name)


# ═══════════════════════════════════════════════════════
# СТАТИСТИКА ЧЕРДАКА
# ═══════════════════════════════════════════════════════

def get_attic_stats() -> dict:
    """Статистика Чердака для UI и хроник."""
    if not GLOBAL_MUTATIONS_DIR.exists():
        return {"total": 0, "legendary": 0, "avg_cultural_weight": 0.0}

    all_meta = []
    for mut_dir in GLOBAL_MUTATIONS_DIR.iterdir():
        if not mut_dir.is_dir():
            continue
        meta_path = mut_dir / "metadata.json"
        if meta_path.exists():
            try:
                all_meta.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, IOError):
                pass

    if not all_meta:
        return {"total": 0, "legendary": 0, "avg_cultural_weight": 0.0}

    legendary_count = sum(1 for m in all_meta if "legendary" in m.get("mythology_tags", []))
    avg_weight = sum(m.get("cultural_weight", 0) for m in all_meta) / len(all_meta)
    total_reuses = sum(m.get("reuse_count", 0) for m in all_meta)

    # Самые популярные трейты на Чердаке
    trait_counts: dict[str, int] = {}
    for m in all_meta:
        for t in m.get("traits", []):
            trait_counts[t] = trait_counts.get(t, 0) + 1
    top_traits = sorted(trait_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total":              len(all_meta),
        "legendary":          legendary_count,
        "avg_cultural_weight": round(avg_weight, 3),
        "total_reuses":       total_reuses,
        "top_traits":         [{"trait": t, "count": c} for t, c in top_traits],
    }
