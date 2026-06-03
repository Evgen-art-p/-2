"""
patch_ref_level.py — три уровня референсов в диалоге загрузки ассетов

Уровни (STUDIO_CONTEXT §15а):
  🔒 truth       — бренд клиента, нельзя менять
  🧭 orientation — рефы от заказчика
  ✨ inspiration — внутренние эталоны студии (дефолт)

Файлы: studio/workshop/assets.py, studio/workshop/ui.py
Запуск из корня проекта: python patch_ref_level.py
"""

import sys
from pathlib import Path

ROOT      = Path(".")
ASSETS_PY = ROOT / "studio" / "workshop" / "assets.py"
UI_PY     = ROOT / "studio" / "workshop" / "ui.py"
errors    = []


def patch(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        errors.append(f"MISS [{label}] в {path.name}")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  ✅ {label}")
    return True


# ──────────────────────────────────────────────────────
# PATCH 1  assets.py — подпись register_uploaded_asset
# ──────────────────────────────────────────────────────
P1_OLD = (
    'def register_uploaded_asset(\n'
    '    filepath: Path,\n'
    '    category: str = "reference",\n'
    '    name: str = "",\n'
    '    visual_anchor: str = "",\n'
    '    mood: str = "",\n'
    '    client_slug: str = "",\n'
    '    move_to_subfolder: bool = True,\n'
    ') -> dict | None:'
)
P1_NEW = (
    'def register_uploaded_asset(\n'
    '    filepath: Path,\n'
    '    category: str = "reference",\n'
    '    name: str = "",\n'
    '    visual_anchor: str = "",\n'
    '    mood: str = "",\n'
    '    client_slug: str = "",\n'
    '    move_to_subfolder: bool = True,\n'
    '    ref_level: str = "inspiration",\n'
    ') -> dict | None:'
)

# ──────────────────────────────────────────────────────
# PATCH 2  assets.py — поле ref_level в new_asset
# ──────────────────────────────────────────────────────
P2_OLD = (
    '            "source": "upload",\n'
    '            "client": client_slug or "_sandbox",\n'
    '        }'
)
P2_NEW = (
    '            "source": "upload",\n'
    '            "client": client_slug or "_sandbox",\n'
    '            "ref_level": ref_level or "inspiration",\n'
    '        }'
)

# ──────────────────────────────────────────────────────
# PATCH 3  assets.py — иконка уровня в строке каталога
# ──────────────────────────────────────────────────────
P3_OLD = (
    "                lines.append(\n"
    "                    f\"{asset.get('id','?')} | {asset.get('name','?')} | \"\n"
    "                    f\"{asset.get('category','?')} | {anchor_short} | {mood}\"\n"
    "                )"
)
P3_NEW = (
    "                _rl = asset.get('ref_level', '')\n"
    "                _ri = {'truth': '🔒', 'orientation': '🧭', 'inspiration': '✨'}.get(_rl, '')\n"
    "                _rp = f'{_ri} ' if _ri else ''\n"
    "                lines.append(\n"
    "                    f\"{_rp}{asset.get('id','?')} | {asset.get('name','?')} | \"\n"
    "                    f\"{asset.get('category','?')} | {anchor_short} | {mood}\"\n"
    "                )"
)

# ──────────────────────────────────────────────────────
# PATCH 4  ui.py — кнопки уровня в show_upload_category_dialog
# вставляем ПЕРЕД строкой name_input
# ──────────────────────────────────────────────────────
P4_OLD = (
    "            name_input = ui.input('Имя ассета', value=suggested_name).style(\n"
    "                'width: 100%; margin-bottom: 12px;'\n"
    "            ).props('dark dense')"
)
P4_NEW = (
    "            ui.label('Уровень референса').style(\n"
    "                'font-size: 11px; color: rgba(255,255,255,0.4); '\n"
    "                'letter-spacing: 0.08em; margin-bottom: 6px;'\n"
    "            )\n"
    "            _ref_selected = {'level': 'inspiration'}\n"
    "            _ref_btns = {}\n"
    "            _REF_LEVELS = {\n"
    "                'truth':       ('🔒', 'Truth',       '#ff6ec7', 'бренд клиента — нельзя менять'),\n"
    "                'orientation': ('🧭', 'Orientation', '#00d4ff', 'рефы от заказчика'),\n"
    "                'inspiration': ('✨', 'Inspiration', '#ffa500', 'внутренние эталоны студии'),\n"
    "            }\n"
    "            with ui.element('div').style(\n"
    "                'display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 14px;'\n"
    "            ):\n"
    "                def _make_ref_click(rid):\n"
    "                    def _on():\n"
    "                        _ref_selected['level'] = rid\n"
    "                        for _bid, _rb in _ref_btns.items():\n"
    "                            _ic, _lb, _co, _ = _REF_LEVELS[_bid]\n"
    "                            if _bid == rid:\n"
    "                                _rb.style(\n"
    "                                    f'background: {_co}22; color: {_co}; '\n"
    "                                    f'border: 2px solid {_co}; border-radius: 8px; '\n"
    "                                    f'padding: 8px 6px; font-weight: 700; font-size: 12px; cursor: pointer;'\n"
    "                                )\n"
    "                            else:\n"
    "                                _rb.style(\n"
    "                                    'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.45); '\n"
    "                                    'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '\n"
    "                                    'padding: 8px 6px; font-size: 12px; cursor: pointer;'\n"
    "                                )\n"
    "                    return _on\n"
    "                for _rid, (_ic, _lb, _co, _hint) in _REF_LEVELS.items():\n"
    "                    _active = (_rid == 'inspiration')\n"
    "                    _style = (\n"
    "                        f'background: {_co}22; color: {_co}; '\n"
    "                        f'border: 2px solid {_co}; border-radius: 8px; '\n"
    "                        f'padding: 8px 6px; font-weight: 700; font-size: 12px; cursor: pointer;'\n"
    "                        if _active else\n"
    "                        'background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.45); '\n"
    "                        'border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; '\n"
    "                        'padding: 8px 6px; font-size: 12px; cursor: pointer;'\n"
    "                    )\n"
    "                    _rb = ui.button(f'{_ic} {_lb}', on_click=_make_ref_click(_rid)).props(\n"
    "                        'flat unelevated'\n"
    "                    ).style(_style).tooltip(_hint)\n"
    "                    _ref_btns[_rid] = _rb\n"
    "\n"
    "            name_input = ui.input('Имя ассета', value=suggested_name).style(\n"
    "                'width: 100%; margin-bottom: 12px;'\n"
    "            ).props('dark dense')"
)

# ──────────────────────────────────────────────────────
# PATCH 5  ui.py — передаём ref_level в register_uploaded_asset
# ──────────────────────────────────────────────────────
P5_OLD = (
    '                    registered = register_uploaded_asset(\n'
    '                        filepath=filepath,\n'
    '                        category=cat,\n'
    '                        name=asset_name,\n'
    '                        client_slug=state.get("current_client", "_sandbox"),\n'
    '                        move_to_subfolder=True,\n'
    '                    )'
)
P5_NEW = (
    '                    registered = register_uploaded_asset(\n'
    '                        filepath=filepath,\n'
    '                        category=cat,\n'
    '                        name=asset_name,\n'
    '                        client_slug=state.get("current_client", "_sandbox"),\n'
    '                        move_to_subfolder=True,\n'
    '                        ref_level=_ref_selected["level"],\n'
    '                    )'
)

# ══════════════════════════════════════════════════════
print("=== patch_ref_level.py ===\n")
print("studio/workshop/assets.py:")
patch(ASSETS_PY, P1_OLD, P1_NEW, "параметр ref_level в register_uploaded_asset")
patch(ASSETS_PY, P2_OLD, P2_NEW, "поле ref_level в new_asset dict")
patch(ASSETS_PY, P3_OLD, P3_NEW, "иконка ref_level в _load_asset_catalog")

print("\nstudio/workshop/ui.py:")
patch(UI_PY, P4_OLD, P4_NEW, "кнопки 🔒🧭✨ в show_upload_category_dialog")
patch(UI_PY, P5_OLD, P5_NEW, "ref_level передаётся в register_uploaded_asset")

print()
if errors:
    print("ОШИБКИ (строки не найдены):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("Готово. 5/5 патчей применены.")
print()
print("Что изменилось:")
print("  • Диалог загрузки: блок кнопок 🔒 Truth / 🧭 Orientation / ✨ Inspiration")
print("  • Дефолт: ✨ Inspiration")
print("  • assets_catalog.json: каждый ассет получает поле ref_level")
print("  • Каталог агентов: строки с иконкой уровня")
print("  • Работает для всех цехов — каталог один, читается везде")
print()
print("Commit:")
print("  feat: ref_level (truth/orientation/inspiration) в диалоге загрузки ассетов")
