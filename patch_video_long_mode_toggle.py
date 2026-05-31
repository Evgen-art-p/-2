"""
patch_video_long_mode_toggle.py  v3
====================================
Запуск из корня репо:
  python patch_video_long_mode_toggle.py
"""

from pathlib import Path
import shutil

TARGET = Path("studio/workshop/ui.py")
BACKUP = Path("_patch_backups/ui.py.bak_video_long_toggle_v3")

assert TARGET.exists(), f"Не найден: {TARGET}"

src = TARGET.read_text(encoding="utf-8")
BACKUP.parent.mkdir(exist_ok=True)
shutil.copy(TARGET, BACKUP)
print(f"[BACKUP] {BACKUP}")

# ══════════════════════════════════════════════════════════════
# 1. PIPELINE_MODES — bible и episode (если ещё нет)
# ══════════════════════════════════════════════════════════════
if '"bible"' not in src:
    OLD_MODES = '''    "full": {
        "label": "🚀 Полный цикл",
        "stop_after": None,
        "checkpoint_at": [3],
        "description": "Все агенты, checkpoint после A03 (сценарий)"
    },'''

    NEW_MODES = '''    "full": {
        "label": "🚀 Полный цикл",
        "stop_after": None,
        "checkpoint_at": [3],
        "description": "Все агенты, checkpoint после A03 (сценарий)"
    },
    "bible": {
        "label": "📖 Библия",
        "stop_after": None,
        "description": "Создание вселенной: мир, персонажи, стиль, план сезона (A01-A04 + хард-стоп)"
    },
    "episode": {
        "label": "🎬 Эпизод",
        "stop_after": None,
        "description": "Экранизация серии по готовой Библии (history_dna обязателен)"
    },'''

    assert OLD_MODES in src, "PIPELINE_MODES: якорь не найден!"
    src = src.replace(OLD_MODES, NEW_MODES, 1)
    print("[OK] 1. PIPELINE_MODES — bible и episode добавлены")
else:
    print("[SKIP] 1. PIPELINE_MODES — bible/episode уже есть")

# ══════════════════════════════════════════════════════════════
# 2. DEPT_TO_RUNTYPE — video_long → episode (если ещё "full")
# ══════════════════════════════════════════════════════════════
if '"video_long":   "full",' in src:
    src = src.replace('"video_long":   "full",', '"video_long":   "episode",', 1)
    print("[OK] 2. DEPT_TO_RUNTYPE — video_long → episode")
else:
    print("[SKIP] 2. DEPT_TO_RUNTYPE — уже episode")

# ══════════════════════════════════════════════════════════════
# 3. Хедер — убираем старый переключатель social_mix из squad-deck
# ══════════════════════════════════════════════════════════════
OLD_HEADER_TOGGLE = '''                # Тоггл режима — только для цеха соцсетей
                if dept == 'social_mix':
                    mode_refs = {}
                    with ui.element('div').style(
                        'display:flex; align-items:center; gap:6px; '
                        'background:rgba(255,255,255,0.05); border-radius:20px; '
                        'padding:4px 8px; flex-shrink:0;'
                    ):
                        ui.html('<span style="font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                'letter-spacing:0.12em; margin-right:4px;">РЕЖИМ</span>')

                        def _set_plan():
                            state['run_type'] = 'content_plan'
                            mode_refs['plan'].style('background:rgba(99,179,237,0.3); color:#63b3ed;')
                            mode_refs['post'].style('background:transparent; color:rgba(255,255,255,0.35);')
                            ui.notify('📝 Контент-план (A01–A04)', type='info', timeout=2000)

                        def _set_post():
                            state['run_type'] = 'social'
                            mode_refs['post'].style('background:rgba(72,187,120,0.3); color:#68d391;')
                            mode_refs['plan'].style('background:transparent; color:rgba(255,255,255,0.35);')
                            ui.notify('📱 Производство поста (все агенты)', type='info', timeout=2000)

                        _plan_active = state['run_type'] == 'content_plan'
                        _btn_s = 'border:none; border-radius:14px; padding:3px 12px; font-size:0.7rem; font-weight:700; letter-spacing:0.05em; cursor:pointer; transition:all 0.2s;'

                        mode_refs['plan'] = ui.button('📝 ПЛАН', on_click=_set_plan).props('flat no-caps').style(
                            _btn_s + ('background:rgba(99,179,237,0.3); color:#63b3ed;' if _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                        )
                        mode_refs['post'] = ui.button('📱 ПОСТ', on_click=_set_post).props('flat no-caps').style(
                                _btn_s + ('background:rgba(72,187,120,0.3); color:#68d391;' if not _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                            )'''

if OLD_HEADER_TOGGLE in src:
    src = src.replace(OLD_HEADER_TOGGLE, '', 1)
    print("[OK] 3. Хедер — старый переключатель social_mix убран")
else:
    print("[SKIP] 3. Хедер — переключатель уже убран")

# ══════════════════════════════════════════════════════════════
# 4. Тулбар — переключатели после 🔌 (если ещё нет)
# ══════════════════════════════════════════════════════════════
if "# ── Режимы: social_mix ──" in src:
    print("[SKIP] 4. Тулбар — переключатели уже добавлены")
else:
    OLD_TOOLBAR_CENTER = '''                    # ── ЦЕНТРАЛЬНАЯ ГРУППА: CONTINUE | 🏭 ────────────────
                    with ui.element('div').style('display:flex; gap:6px; align-items:center; justify-content:center;'):
                        ui.button('▶ CONTINUE', on_click=lambda: continue_cartridge_pipeline()).props('flat no-caps').style(
                            'padding:6px 14px; border-radius:8px; font-size:0.72rem; font-weight:700; '
                            'letter-spacing:0.06em; border:1px solid rgba(255,210,0,0.35); '
                            'color:rgba(255,210,0,0.85); background:rgba(255,210,0,0.07);'
                        )
                        ui.button('🏭', on_click=lambda: ui.navigate.to('/assembly', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(255,140,0,0.3); '
                            'color:rgba(255,140,0,0.8); background:rgba(255,140,0,0.07);'
                        ).tooltip('Сборочный цех')
                        ui.button('🔌', on_click=lambda: ui.navigate.to('/cartridges', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(140,108,255,0.3); '
                            'color:rgba(140,108,255,0.8); background:rgba(140,108,255,0.07);'
                        ).tooltip('Менеджер картриджей')'''

    NEW_TOOLBAR_CENTER = '''                    # ── ЦЕНТРАЛЬНАЯ ГРУППА: CONTINUE | 🏭 | 🔌 | РЕЖИМЫ ──
                    with ui.element('div').style('display:flex; gap:6px; align-items:center; justify-content:center;'):
                        ui.button('▶ CONTINUE', on_click=lambda: continue_cartridge_pipeline()).props('flat no-caps').style(
                            'padding:6px 14px; border-radius:8px; font-size:0.72rem; font-weight:700; '
                            'letter-spacing:0.06em; border:1px solid rgba(255,210,0,0.35); '
                            'color:rgba(255,210,0,0.85); background:rgba(255,210,0,0.07);'
                        )
                        ui.button('🏭', on_click=lambda: ui.navigate.to('/assembly', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(255,140,0,0.3); '
                            'color:rgba(255,140,0,0.8); background:rgba(255,140,0,0.07);'
                        ).tooltip('Сборочный цех')
                        ui.button('🔌', on_click=lambda: ui.navigate.to('/cartridges', new_tab=True)).props('flat').style(
                            'padding:6px 10px; border-radius:8px; font-size:1rem; '
                            'border:1px solid rgba(140,108,255,0.3); '
                            'color:rgba(140,108,255,0.8); background:rgba(140,108,255,0.07);'
                        ).tooltip('Менеджер картриджей')

                        # ── Режимы: social_mix ──
                        if dept == 'social_mix':
                            _sm_refs = {}
                            with ui.element('div').style(
                                'display:flex; align-items:center; gap:6px; '
                                'background:rgba(255,255,255,0.05); border-radius:20px; '
                                'padding:4px 8px; flex-shrink:0;'
                            ):
                                ui.html('<span style="font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                        'letter-spacing:0.12em; margin-right:4px;">РЕЖИМ</span>')

                                def _set_plan():
                                    state['run_type'] = 'content_plan'
                                    _sm_refs['plan'].style('background:rgba(99,179,237,0.3); color:#63b3ed;')
                                    _sm_refs['post'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📝 Контент-план (A01–A04)', type='info', timeout=2000)

                                def _set_post():
                                    state['run_type'] = 'social'
                                    _sm_refs['post'].style('background:rgba(72,187,120,0.3); color:#68d391;')
                                    _sm_refs['plan'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📱 Производство поста (все агенты)', type='info', timeout=2000)

                                _plan_active = state['run_type'] == 'content_plan'
                                _btn_s = ('border:none; border-radius:14px; padding:3px 12px; '
                                          'font-size:0.7rem; font-weight:700; letter-spacing:0.05em; '
                                          'cursor:pointer; transition:all 0.2s;')

                                _sm_refs['plan'] = ui.button('📝 ПЛАН', on_click=_set_plan).props('flat no-caps').style(
                                    _btn_s + ('background:rgba(99,179,237,0.3); color:#63b3ed;'
                                              if _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )
                                _sm_refs['post'] = ui.button('📱 ПОСТ', on_click=_set_post).props('flat no-caps').style(
                                    _btn_s + ('background:rgba(72,187,120,0.3); color:#68d391;'
                                              if not _plan_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )

                        # ── Режимы: video_long ──
                        if dept == 'video_long':
                            _vl_refs = {}
                            with ui.element('div').style(
                                'display:flex; align-items:center; gap:6px; '
                                'background:rgba(255,255,255,0.05); border-radius:20px; '
                                'padding:4px 8px; flex-shrink:0;'
                            ):
                                ui.html('<span style="font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                        'letter-spacing:0.12em; margin-right:4px;">РЕЖИМ</span>')

                                def _set_bible():
                                    state['run_type'] = 'bible'
                                    _vl_refs['bible'].style('background:rgba(139,92,246,0.3); color:#a78bfa;')
                                    _vl_refs['episode'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('📖 Библия — создание вселенной (A01–A04)', type='info', timeout=2000)

                                def _set_episode():
                                    state['run_type'] = 'episode'
                                    _vl_refs['episode'].style('background:rgba(52,211,153,0.3); color:#34d399;')
                                    _vl_refs['bible'].style('background:transparent; color:rgba(255,255,255,0.35);')
                                    ui.notify('🎬 Эпизод — экранизация по Библии', type='info', timeout=2000)

                                _bible_active = state['run_type'] == 'bible'
                                _vl_btn_s = ('border:none; border-radius:14px; padding:3px 12px; '
                                             'font-size:0.7rem; font-weight:700; letter-spacing:0.05em; '
                                             'cursor:pointer; transition:all 0.2s;')

                                _vl_refs['bible'] = ui.button('📖 BIBLE', on_click=_set_bible).props('flat no-caps').style(
                                    _vl_btn_s + ('background:rgba(139,92,246,0.3); color:#a78bfa;'
                                                 if _bible_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )
                                _vl_refs['episode'] = ui.button('🎬 EPISODE', on_click=_set_episode).props('flat no-caps').style(
                                    _vl_btn_s + ('background:rgba(52,211,153,0.3); color:#34d399;'
                                                 if not _bible_active else 'background:transparent; color:rgba(255,255,255,0.35);')
                                )'''

    assert OLD_TOOLBAR_CENTER in src, "Тулбар центральная группа: якорь не найден!"
    src = src.replace(OLD_TOOLBAR_CENTER, NEW_TOOLBAR_CENTER, 1)
    print("[OK] 4. Тулбар — переключатели social_mix и video_long добавлены после 🔌")

# ══════════════════════════════════════════════════════════════
# Запись
# ══════════════════════════════════════════════════════════════
TARGET.write_text(src, encoding="utf-8")
print(f"\n✅ Патч v3 применён → {TARGET}")
print(f"   Бэкап: {BACKUP}")
print("\nРезультат:")
print("  CONTINUE → 🏭 → 🔌 → [📝 ПЛАН / 📱 ПОСТ]    (social_mix)")
print("  CONTINUE → 🏭 → 🔌 → [📖 BIBLE / 🎬 EPISODE]  (video_long)")
