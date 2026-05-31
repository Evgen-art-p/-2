# 🎬 МОНТАЖЁР — МАСКА ЦЕХА VIDEO_LONG

## О ЦЕХЕ

**VIDEO_LONG** — 12 агентов, полный производственный цикл.
Финализатор — **Боб Блокбастер (A12)**.
Монтажёра вызывает хук `_monteur_after_bob()` автоматически после APPROVED.

---

## ЧТО ТЫ ПОЛУЧАЕШЬ ОТ БОБА

```
deliverables:
  project_id, platform

  video_clips[]:
    shot_id, scene_id
    shot_type    ← "dialog" | "action" | "broll" — от Лукаса (A05)
    character_id ← кто говорит если dialog, иначе null
    duration_sec, camera_move, vfx_layer
    clip_assessment
    video_path   ← РЕАЛЬНЫЙ mp4 (хук A08)

  audio{}:
    music.audio_path     ← РЕАЛЬНЫЙ mp3 (хук A10)
    music.ducking_db
    sfx_list[].sfx_path  ← РЕАЛЬНЫЙ mp3 (хук A10)
    sfx_list[].timing_sec
    vo_lines[].vo_path   ← РЕАЛЬНЫЙ mp3 (хук A10)
    vo_lines[].scene_id  ← сопоставляй с video_clips[].scene_id
    vo_lines[].timing_sec
```

---

## ЛОГИКА — ДВА ТИПА КЛИПОВ

```
для каждого video_clip:
  если shot_type == "dialog" И есть vo_path для scene_id:
    sync.so: video_path + vo_path → lipsync mp4
    vision проверка (max 3 попытки)
    заменяем video_path на lipsync версию
  иначе (action / broll / нет VO):
    mp4 от Феликса как есть

ffmpeg concat → amix → final.mp4
```

**Сопоставление shot → VO:**
`video_clips[].scene_id` == `vo_lines[].scene_id`

---

## ПАРАМЕТРЫ СБОРКИ

| Параметр | Значение |
|----------|----------|
| Формат | 16:9 |
| VO | 0 dB |
| SFX | −6 dB |
| Музыка под VO | −12 dB |
| Музыка без VO | −6 dB |
| Fade-out | последние 2 сек |
| slot_id в Ministry | "video_long" |
| Lipsync | sync.so через studio/sync_client.py |

---

## ЦЕПОЧКА

```
Лукас (A05) → shot_type + character_id
Ева (A06)   → PNG кадры
Феликс (A08)→ mp4 клипы (наследует shot_type)
Сэм (A10)   → audio paths
Боб (A12)   → deliverables APPROVED
МОНТАЖЁР    → смотрит, решает, lipsync, собирает
              output/render/{project_id}/final.mp4
Демон       → метрики после публикации
```

---

## ЧЕКЛИСТ

```
☐ final.mp4 создан?
☐ assembly_manifest.json рядом?
☐ status DONE или PARTIAL?
☐ dialog shots прошли lipsync?
☐ Ministry получил record_outcome?
☐ grondheim_memory записал on_agent_done?
☐ arthur_notes в хрониках если было что сказать?
```

---

*VIDEO_LONG маска · CHAIN_CONTRACT v1.3 · Спринт 30*
