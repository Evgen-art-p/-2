"""
patch_cleanup_vl_header.py
===========================
Убирает дублирующий переключатель video_long из хедера (squad-deck).
Оставляет только тот что в тулбаре (после 🔌).

Запуск из корня репо:
  python patch_cleanup_vl_header.py
"""

from pathlib import Path
import shutil

TARGET = Path("studio/workshop/ui.py")
BACKUP = Path("_patch_backups/ui.py.bak_cleanup_vl_header")

assert TARGET.exists(), f"Не найден: {TARGET}"

src = TARGET.read_text(encoding="utf-8")
BACKUP.parent.mkdir(exist_ok=True)
shutil.copy(TARGET, BACKUP)
print(f"[BACKUP] {BACKUP}")

OLD = """


                # ── Тоггл режима — video_long: BIBLE / EPISODE ──
                if dept == 'video_long':
                    vl_mode_refs = {}
                    with ui.element('div').style(
                        'display:flex; align-items:center; gap:6px; '
                        'background:rgba(255,255,255,0.05); border-radius:20px; '
                        'padding:4px 8px; flex-shrink:0;'
                    ):
                        ui.html('<span style=\"font-size:0.6rem; color:rgba(255,255,255,0.35); '
                                'letter-spacing:0.12em; margin-right:4px;\">РЕЖИМ</span>')

                        def _set_bible():
                            state['run_type'] = 'bible'
                            vl_mode_refs['bible'].style(
                                'background:rgba(139,92,246,0.3); color:#a78bfa;')
                            vl_mode_refs['episode'].style(
                                'background:transparent; color:rgba(255,255,255,0.35);')
                            ui.notify('📖 Библия — создание вселенной (A01–A04)', type='info', timeout=2000)

                        def _set_episode():
                            state['run_type'] = 'episode'
                            vl_mode_refs['episode'].style(
                                'background:rgba(52,211,153,0.3); color:#34d399;')
                            vl_mode_refs['bible'].style(
                                'background:transparent; color:rgba(255,255,255,0.35);')
                            ui.notify('🎬 Эпизод — экранизация по Библии (все агенты)', type='info', timeout=2000)

                        _vl_btn_s = (
                            'border:none; border-radius:14px; padding:3px 12px; '
                            'font-size:0.7rem; font-weight:700; letter-spacing:0.05em; '
                            'cursor:pointer; transition:all 0.2s;'
                        )
                        _bible_active = state['run_type'] == 'bible'

                        vl_mode_refs['bible'] = ui.button(
                            '📖 BIBLE', on_click=_set_bible
                        ).props('flat no-caps').style(
                            _vl_btn_s + (
                                'background:rgba(139,92,246,0.3); color:#a78bfa;'
                                if _bible_active else
                                'background:transparent; color:rgba(255,255,255,0.35);'
                            )
                        )
                        vl_mode_refs['episode'] = ui.button(
                            '🎬 EPISODE', on_click=_set_episode
                        ).props('flat no-caps').style(
                            _vl_btn_s + (
                                'background:rgba(52,211,153,0.3); color:#34d399;'
                                if not _bible_active else
                                'background:transparent; color:rgba(255,255,255,0.35);'
                            )
                        )"""

assert OLD in src, "Якорь не найден — возможно уже удалён"
src = src.replace(OLD, "", 1)

TARGET.write_text(src, encoding="utf-8")
print("[OK] Дублирующий переключатель video_long удалён из хедера")
print(f"\n✅ Готово → {TARGET}")
print(f"   Бэкап: {BACKUP}")
