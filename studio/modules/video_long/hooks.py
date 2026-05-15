# studio/modules/video_long/hooks.py — Хуки VIDEO_LONG v3.1
# Студия «Шесть Пальцев» · 2026
#
# v3.1 — BIBLE: A06 Ева генерит эталонные картинки в клиентский каталог.
#        EPISODE: A06 Ева генерит кадры по раскадровке Лукаса.
#                 A11 Трейси генерит обложки.
#                 A12 Боб собирает deliverables с путями.

import json
import re
from pathlib import Path
from studio.fal_client import generate_with_refs, generate_image, add_to_catalog, load_catalog


OUTPUT_DIR = Path("output/generated")
CLIENTS_DIR = Path("clients")


def on_before_agent(state: dict, worker_id: str, context: str) -> str:
    """Контекст без изменений."""
    return context


def on_after_agent(state: dict, worker_id: str, human_text: str, meta: dict) -> dict:
    """
    BIBLE: A06 Ева — эталонные картинки в клиентский каталог.
    EPISODE: A06 Ева — генерация кадров по раскадровке Лукаса.
    EPISODE: A11 Трейси — генерация обложек.
    EPISODE: A12 Боб — сборка deliverables с путями.
    """

    mode = state.get("mode", state.get("run_type", "episode"))

    # ── BIBLE: A06 Ева — эталонные картинки ─────────────────
    if mode == "bible" and worker_id == "A06":
        _bible_eva_generate_references(state, human_text)

    # ── EPISODE: A06 Ева — кадры по раскадровке Лукаса ─────
    elif mode == "episode" and worker_id == "A06":
        _episode_eva_generate_frames(state, human_text)

    # ── EPISODE: A11 Трейси — обложки ───────────────────────
    elif mode == "episode" and worker_id == "A11":
        _episode_tracy_generate_thumbnails(state, human_text)

    # ── EPISODE: A12 Боб — сборка deliverables ──────────────
    elif mode == "episode" and worker_id == "A12":
        _episode_bob_assemble(state, human_text)

    return {}


# ═══════════════════════════════════════════════════════════════
# BIBLE: ЕВА — ЭТАЛОННЫЕ КАРТИНКИ
# ═══════════════════════════════════════════════════════════════

def _bible_eva_generate_references(state: dict, human_text: str):
    """
    Парсит JSON Евы (BIBLE).
    Генерит эталонные картинки персонажей и локаций.
    Сохраняет в clients/{slug}/assets/images/.
    Добавляет записи в clients/{slug}/assets/catalog.json.
    """

    data = _parse_json(human_text)
    if not data:
        print("[BIBLE A06] JSON не найден — пропускаю генерацию эталонов")
        return

    my_output = data.get("my_output", data)

    # Определяем client_slug
    client_slug = _get_client_slug(state)

    # Загружаем клиентский каталог
    if client_slug:
        load_catalog(client_slug=client_slug)
        assets_dir = CLIENTS_DIR / client_slug / "assets" / "images"
        assets_dir.mkdir(parents=True, exist_ok=True)
    else:
        assets_dir = OUTPUT_DIR / (state.get("project_id", "bible_unknown"))
        assets_dir.mkdir(parents=True, exist_ok=True)
        print("[BIBLE A06] client_slug не найден — сохраняю в output/generated")

    slot_id = state.get("_slot_id", "video_long")

    # ── Генерация персонажей ────────────────────────────────
    characters = my_output.get("character_prompts", [])
    for i, char in enumerate(characters):
        prompt = char.get("banana_prompt") or char.get("prompt", "")
        char_name = char.get("name", f"character_{i+1}")
        char_id = _slugify(char_name)
        ref_id = f"char_{char_id}"

        if not prompt:
            print(f"[BIBLE A06] Персонаж {char_name}: нет промпта — пропускаю")
            char["ref_id"] = ref_id
            char["path"] = None
            continue

        filename = f"{ref_id}.png"
        print(f"[BIBLE A06] Генерирую персонажа: {char_name} ({ref_id})")

        try:
            path = generate_image(
                prompt=prompt,
                format="16:9",
                filename=filename,
                agent_id="A06",
                slot_id=slot_id,
            )

            final_path = assets_dir / filename
            Path(path).replace(final_path)
            char["path"] = str(final_path)
            char["ref_id"] = ref_id

            if client_slug:
                try:
                    add_to_catalog(
                        source_path=str(final_path),
                        name=char_name,
                        category="character",
                        tags=char.get("tags", []),
                        visual_anchor=char.get("visual_anchor", char.get("appearance", "")),
                    )
                    print(f"[BIBLE A06] ✅ {ref_id} → каталог клиента {client_slug}")
                except Exception as e:
                    print(f"[BIBLE A06] ⚠️ Ошибка каталога: {e}")
            else:
                print(f"[BIBLE A06] ✅ {ref_id}: {final_path}")

        except Exception as e:
            print(f"[BIBLE A06] ❌ Ошибка генерации {char_name}: {e}")
            char["path"] = None
            char["ref_id"] = ref_id
            char["error"] = str(e)

    # ── Генерация локаций ───────────────────────────────────
    locations = my_output.get("location_prompts", [])
    for i, loc in enumerate(locations):
        prompt = loc.get("banana_prompt") or loc.get("prompt", "")
        loc_name = loc.get("name", f"location_{i+1}")
        loc_id = _slugify(loc_name)
        ref_id = f"loc_{loc_id}"

        if not prompt:
            print(f"[BIBLE A06] Локация {loc_name}: нет промпта — пропускаю")
            loc["ref_id"] = ref_id
            loc["path"] = None
            continue

        filename = f"{ref_id}.png"
        print(f"[BIBLE A06] Генерирую локацию: {loc_name} ({ref_id})")

        try:
            path = generate_image(
                prompt=prompt,
                format="16:9",
                filename=filename,
                agent_id="A06",
                slot_id=slot_id,
            )

            final_path = assets_dir / filename
            Path(path).replace(final_path)
            loc["path"] = str(final_path)
            loc["ref_id"] = ref_id

            if client_slug:
                try:
                    add_to_catalog(
                        source_path=str(final_path),
                        name=loc_name,
                        category="location",
                        tags=loc.get("tags", []),
                        visual_anchor=loc.get("description", ""),
                    )
                    print(f"[BIBLE A06] ✅ {ref_id} → каталог клиента {client_slug}")
                except Exception as e:
                    print(f"[BIBLE A06] ⚠️ Ошибка каталога: {e}")
            else:
                print(f"[BIBLE A06] ✅ {ref_id}: {final_path}")

        except Exception as e:
            print(f"[BIBLE A06] ❌ Ошибка генерации {loc_name}: {e}")
            loc["path"] = None
            loc["ref_id"] = ref_id
            loc["error"] = str(e)

    my_output["character_prompts"] = characters
    my_output["location_prompts"] = locations
    if "my_output" in data:
        data["my_output"] = my_output

    gen_chars = sum(1 for c in characters if c.get("path"))
    gen_locs = sum(1 for l in locations if l.get("path"))
    print(f"[BIBLE A06] Готово: {gen_chars} персонажей, {gen_locs} локаций")
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════
# EPISODE: ЕВА — КАДРЫ ПО РАСКАДРОВКЕ ЛУКАСА
# ═══════════════════════════════════════════════════════════════

def _episode_eva_generate_frames(state: dict, human_text: str):
    """
    Парсит JSON Евы (EPISODE).
    Генерит ключевые кадры по раскадровке Лукаса.
    Использует эталоны из клиентского каталога как ref_ids.
    """

    data = _parse_json(human_text)
    if not data:
        print("[EPISODE A06] JSON не найден — пропускаю генерацию кадров")
        return

    my_output = data.get("my_output", data)
    frames = my_output.get("key_frames", [])
    if not frames:
        print("[EPISODE A06] key_frames пуст — пропускаю")
        return

    # Получаем раскадровку Лукаса для сверки
    chain = state.get("chain_data", {})
    storyboard = chain.get("lucas_storyboard", {})

    client_slug = _get_client_slug(state)
    project_id = state.get("project_id", "vl_episode_unknown")
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    if client_slug:
        load_catalog(client_slug=client_slug)

    slot_id = state.get("_slot_id", "video_long")
    generated = 0
    total = len(frames)

    # Собираем карту раскадровки для быстрого доступа
    storyboard_map = {}
    if isinstance(storyboard, dict):
        storyboard_scenes = storyboard.get("storyboard", [])
    elif isinstance(storyboard, list):
        storyboard_scenes = storyboard
    else:
        storyboard_scenes = []

    for scene in storyboard_scenes:
        for shot in scene.get("shots", []):
            shot_id = shot.get("shot_id", "")
            if shot_id:
                storyboard_map[shot_id] = {
                    "scene_id": scene.get("scene_id", ""),
                    "composition": shot.get("composition", ""),
                    "shot_size": shot.get("shot_size", ""),
                    "camera_movement": shot.get("camera_movement", ""),
                    "visual_hint": shot.get("visual_hint", ""),
                }

    for i, frame in enumerate(frames):
        prompt = frame.get("banana_prompt") or frame.get("prompt", "")
        if not prompt:
            print(f"[EPISODE A06] Кадр {i+1}: нет промпта — пропускаю")
            continue

        ref_ids = frame.get("ref_ids", [])
        if isinstance(ref_ids, str):
            ref_ids = [ref_ids]

        # Сверяем с раскадровкой Лукаса
        shot_id = frame.get("shot_id", f"shot_{i+1:02d}")
        sb_info = storyboard_map.get(shot_id, {})
        if sb_info:
            frame["composition"] = frame.get("composition") or sb_info.get("composition", "")
            frame["shot_size"] = frame.get("shot_size") or sb_info.get("shot_size", "")
            frame["camera_movement"] = frame.get("camera_movement") or sb_info.get("camera_movement", "")
            frame["visual_hint"] = frame.get("visual_hint") or sb_info.get("visual_hint", "")
            frame["scene_id"] = frame.get("scene_id") or sb_info.get("scene_id", "")

        scene_id = frame.get("scene_id", f"scene_{i+1}")
        safe_scene = _slugify(str(scene_id))[:20]
        safe_shot = _slugify(str(shot_id))[:15]
        filename = f"{safe_scene}_{safe_shot}.png"

        print(f"[EPISODE A06] Генерирую кадр {i+1}/{total}: {filename}")
        if ref_ids:
            print(f"[EPISODE A06]   Референсы: {ref_ids}")
        if sb_info:
            print(f"[EPISODE A06]   Раскадровка: {sb_info.get('shot_size', '?')}, {sb_info.get('composition', '?')}")

        try:
            if ref_ids:
                path = generate_with_refs(
                    prompt=prompt,
                    ref_ids=ref_ids,
                    format="16:9",
                    filename=filename,
                    agent_id="A06",
                    slot_id=slot_id,
                )
            else:
                path = generate_image(
                    prompt=prompt,
                    format="16:9",
                    filename=filename,
                    agent_id="A06",
                    slot_id=slot_id,
                )

            final_path = project_dir / filename
            Path(path).replace(final_path)
            frame["path"] = str(final_path)
            generated += 1
            print(f"[EPISODE A06] ✅ {filename}")

        except Exception as e:
            print(f"[EPISODE A06] ❌ Ошибка генерации {shot_id}: {e}")
            frame["path"] = None
            frame["error"] = str(e)

    my_output["key_frames"] = frames
    if "my_output" in data:
        data["my_output"] = my_output

    print(f"[EPISODE A06] Готово: {generated}/{total} кадров")
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════
# EPISODE: ТРЕЙСИ — ОБЛОЖКИ
# ═══════════════════════════════════════════════════════════════

def _episode_tracy_generate_thumbnails(state: dict, human_text: str):
    """
    Парсит JSON Трейси (EPISODE).
    Генерит обложки variant_a и variant_b через fal.ai.
    Использует референсы из клиентского каталога.
    """

    data = _parse_json(human_text)
    if not data:
        print("[EPISODE A11] JSON не найден — пропускаю генерацию обложек")
        return

    my_output = data.get("my_output", data)
    thumb = my_output.get("thumbnail", {})
    if not thumb:
        print("[EPISODE A11] thumbnail не найден — пропускаю")
        return

    client_slug = _get_client_slug(state)
    project_id = state.get("project_id", "vl_episode_unknown")
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    if client_slug:
        load_catalog(client_slug=client_slug)

    slot_id = state.get("_slot_id", "video_long")
    generated = 0

    for variant_name in ["variant_a", "variant_b"]:
        variant = thumb.get(variant_name, {})
        if not variant:
            continue

        prompt = variant.get("banana_prompt") or variant.get("prompt", "")
        if not prompt:
            print(f"[EPISODE A11] {variant_name}: нет промпта — пропускаю")
            continue

        ref_ids = variant.get("ref_ids", [])
        if isinstance(ref_ids, str):
            ref_ids = [ref_ids]

        filename = f"thumb_{variant_name}.png"

        print(f"[EPISODE A11] Генерирую обложку: {variant_name}")
        if ref_ids:
            print(f"[EPISODE A11]   Референсы: {ref_ids}")

        try:
            if ref_ids:
                path = generate_with_refs(
                    prompt=prompt,
                    ref_ids=ref_ids,
                    format="16:9",
                    filename=filename,
                    agent_id="A11",
                    slot_id=slot_id,
                )
            else:
                path = generate_image(
                    prompt=prompt,
                    format="16:9",
                    filename=filename,
                    agent_id="A11",
                    slot_id=slot_id,
                )

            final_path = project_dir / filename
            Path(path).replace(final_path)
            variant["path"] = str(final_path)
            generated += 1
            print(f"[EPISODE A11] ✅ {variant_name}: {final_path}")

        except Exception as e:
            print(f"[EPISODE A11] ❌ Ошибка генерации {variant_name}: {e}")
            variant["path"] = None
            variant["error"] = str(e)

    thumb["variant_a"] = thumb.get("variant_a", {})
    thumb["variant_b"] = thumb.get("variant_b", {})
    my_output["thumbnail"] = thumb

    if "my_output" in data:
        data["my_output"] = my_output

    print(f"[EPISODE A11] Готово: {generated}/2 обложек")
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════
# EPISODE: БОБ — СБОРКА DELIVERABLES
# ═══════════════════════════════════════════════════════════════

def _episode_bob_assemble(state: dict, human_text: str):
    """
    Парсит JSON Боба (EPISODE).
    Добавляет в deliverables пути к кадрам (от Евы) и обложкам (от Трейси).
    """

    data = _parse_json(human_text)
    if not data:
        print("[EPISODE A12] JSON не найден — пропускаю сборку")
        return

    chain = state.get("chain_data", {})

    # Пути к кадрам от Евы
    eva = chain.get("eva_visuals", {})
    if isinstance(eva, dict):
        eva_frames = eva.get("key_frames", [])
        storyboard = chain.get("lucas_storyboard", {})
        if isinstance(storyboard, dict):
            storyboard_scenes = storyboard.get("storyboard", [])
        elif isinstance(storyboard, list):
            storyboard_scenes = storyboard
        else:
            storyboard_scenes = []

        deliverables = data.get("deliverables", {})
        if not deliverables:
            deliverables = {}
            data["deliverables"] = deliverables

        deliverables["key_frames"] = []
        for f in eva_frames:
            deliverables["key_frames"].append({
                "shot_id": f.get("shot_id", ""),
                "scene_id": f.get("scene_id", ""),
                "shot_size": f.get("shot_size", ""),
                "composition": f.get("composition", ""),
                "camera_movement": f.get("camera_movement", ""),
                "visual_hint": f.get("visual_hint", ""),
                "prompt": f.get("banana_prompt", ""),
                "ref_ids": f.get("ref_ids", []),
                "format": "16:9",
                "path": f.get("path", None),
            })

        # Добавляем раскадровку Лукаса
        deliverables["storyboard"] = storyboard_scenes
        print(f"[EPISODE A12] key_frames: {len(deliverables['key_frames'])} кадров")

    # Пути к обложкам от Трейси
    tracy = chain.get("tracy_smm", {})
    if isinstance(tracy, dict):
        tracy_thumb = tracy.get("thumbnail", {})
        if tracy_thumb:
            deliverables = data.get("deliverables", {})
            if not deliverables:
                deliverables = {}
                data["deliverables"] = deliverables

            deliverables["thumbnail"] = {
                "variant_a": {
                    "concept": tracy_thumb.get("variant_a", {}).get("concept", ""),
                    "banana_prompt": tracy_thumb.get("variant_a", {}).get("banana_prompt", ""),
                    "text_overlay": tracy_thumb.get("variant_a", {}).get("text_overlay", ""),
                    "emotion": tracy_thumb.get("variant_a", {}).get("emotion", ""),
                    "ref_ids": tracy_thumb.get("variant_a", {}).get("ref_ids", []),
                    "path": tracy_thumb.get("variant_a", {}).get("path", None),
                },
                "variant_b": {
                    "concept": tracy_thumb.get("variant_b", {}).get("concept", ""),
                    "banana_prompt": tracy_thumb.get("variant_b", {}).get("banana_prompt", ""),
                    "text_overlay": tracy_thumb.get("variant_b", {}).get("text_overlay", ""),
                    "emotion": tracy_thumb.get("variant_b", {}).get("emotion", ""),
                    "ref_ids": tracy_thumb.get("variant_b", {}).get("ref_ids", []),
                    "path": tracy_thumb.get("variant_b", {}).get("path", None),
                },
            }
            print(f"[EPISODE A12] thumbnail: добавлен")

    # Добавляем veo3_prompts от Феликса
    felix = chain.get("felix_vfx", {})
    if isinstance(felix, dict):
        felix_frames = felix.get("key_frames", felix.get("veo3_prompts", []))
        if felix_frames:
            deliverables = data.get("deliverables", {})
            if not deliverables:
                deliverables = {}
                data["deliverables"] = deliverables

            deliverables["veo3_prompts"] = []
            for f in felix_frames:
                deliverables["veo3_prompts"].append({
                    "shot_id": f.get("shot_id", ""),
                    "camera": f.get("camera_movement", f.get("camera", "")),
                    "duration": f.get("duration_sec", 0),
                    "prompt": f.get("veo3_prompt", f.get("prompt", "")),
                    "ref_ids": f.get("ref_ids", []),
                })
            print(f"[EPISODE A12] veo3_prompts: {len(deliverables['veo3_prompts'])} клипов")

    # Копируем аудио, субтитры, монтаж из chain_data
    deliverables = data.get("deliverables", {})
    if not deliverables:
        deliverables = {}
        data["deliverables"] = deliverables

    sam = chain.get("sam_sound", {})
    if isinstance(sam, dict) and sam:
        deliverables["audio"] = sam

    alex = chain.get("alex_motion", {})
    if isinstance(alex, dict) and alex:
        deliverables["motion"] = alex

    tim = chain.get("tim_typography", {})
    if isinstance(tim, dict) and tim:
        deliverables["typography"] = tim

    print(f"[EPISODE A12] deliverables собраны")
    _update_state(state, data)


# ═══════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════

def _get_client_slug(state: dict) -> str | None:
    """Определяет client_slug из state или chain_data."""
    slug = state.get("client_slug", "")
    if slug:
        return slug

    chain = state.get("chain_data", {})
    adam = chain.get("adam_bible", chain.get("adam_episode", {}))
    if isinstance(adam, dict):
        slug = adam.get("client_slug", "")

    return slug or None


def _parse_json(text: str) -> dict | None:
    """Вытаскивает JSON из ответа агента."""
    pattern = r'SYSTEM_JSON_START[^\n]*\n(.*?)\n[^\n]*SYSTEM_JSON_END'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        fence = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if fence:
            raw = fence.group(1)
        else:
            print("[VIDEO_LONG] JSON не найден")
            return None

    raw = raw.strip().strip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[VIDEO_LONG] Ошибка парсинга JSON: {e}")
        return None


def _slugify(name: str) -> str:
    """Преобразует имя в slug для ref_id или имени файла."""
    slug = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ_-]', '_', str(name).lower().strip())
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug or "unknown"


def _update_state(state: dict, data: dict):
    """Записывает обновлённые данные в state."""
    state["_last_output"] = data

    chain = state.get("chain_data", {})
    if "my_output" in data:
        chain.update(data["my_output"])
    else:
        chain.update(data)
    state["chain_data"] = chain