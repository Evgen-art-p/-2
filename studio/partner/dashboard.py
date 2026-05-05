"""
dashboard.py — Панель Партнёра Грондхейма
"""

import json
from pathlib import Path
from nicegui import ui

from studio.partner.partner_css import PARTNER_CSS

# ============================================================================
# ДАННЫЕ И ФУНКЦИИ
# ============================================================================

def get_balance_from_catalog(partner_id: str) -> float:
    catalog_path = Path(__file__).parent.parent.parent / "00_REGISTRY_NFT" / "catalog.json"
    if not catalog_path.exists():
        return 0.0
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        for obj in catalog:
            if obj.get("ID_Object") == partner_id:
                balance = obj.get("Balance_GND", 0)
                return float(balance) if balance else 0.0
        return 0.0
    except Exception:
        return 0.0

ALL_CARTRIDGES = [
    {"id": "turbo", "name": "TURBO", "icon": "⚡"},
    {"id": "social_mix", "name": "SOCIAL MIX", "icon": "📱"},
    {"id": "video_long", "name": "VIDEO LONG", "icon": "🎬"},
    {"id": "video_shorts", "name": "VIDEO SHORTS", "icon": "📲"},
    {"id": "living_book", "name": "LIVING BOOK", "icon": "📖"},
    {"id": "web_story", "name": "WEB STORY", "icon": "🌐"},
    {"id": "advertising", "name": "ADVERTISING", "icon": "📢"},
    {"id": "clipmakers", "name": "CLIPMAKERS", "icon": "✂️"},
    {"id": "emo_card", "name": "EMO CARD", "icon": "🎭"},
    {"id": "logo_design", "name": "LOGO DESIGN", "icon": "🎨"},
    {"id": "market_hit", "name": "MARKET HIT", "icon": "📊"},
]

MODULES_PATH = Path("studio/modules")

def cartridge_exists(cartridge_id: str) -> bool:
    module_path = MODULES_PATH / cartridge_id
    if not module_path.exists():
        return False
    return (module_path / "manifest.json").exists()

def get_metrics(cartridge_id: str):
    return 0.0, 0

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def page_partner_dashboard():
    ui.add_head_html(PARTNER_CSS)
    
    partner_id = "P_0000000001"
    real_balance = get_balance_from_catalog(partner_id)
    real_fuel = 0.0
    
    with ui.element("div").classes("partner-page"):
        with ui.element("div").classes("partner-grid"):
            with ui.element("div").classes("partner-header"):
                ui.html('<div class="partner-brand">💰 ШЕСТЬ ПАЛЬЦЕВ / ПАРТНЁР</div>')
                with ui.element("div").classes("partner-controls"):
                    ui.button("🔄 обновить", on_click=lambda: ui.open("/partner")).props("flat dense").classes("partner-btn")
                    ui.button("🏛️ в кабинет", on_click=lambda: ui.open("/cabinet")).classes("partner-btn")
                    ui.button("🔌 управление", on_click=lambda: ui.open("/cartridges")).props("flat dense").classes("partner-btn")
            
            with ui.element("div").classes("partner-row"):
                
                # ========== ЛЕВАЯ ПАНЕЛЬ ==========
                with ui.column().classes("partner-left").style("width:300px;padding:16px;flex-shrink:0;"):
                    ui.label("⚡ МОИ ЦЕХА").classes("partner-panel-title")
                    
                    for c in ALL_CARTRIDGES:
                        exists = cartridge_exists(c["id"])
                        daily, roi = get_metrics(c["id"])
                        
                        if exists:
                            with ui.card().classes("partner-installed"):
                                with ui.row().classes("partner-cartridge-row"):
                                    ui.label(c["icon"]).classes("partner-cartridge-icon")
                                    ui.label(c["name"]).classes("partner-cartridge-name")
                                    ui.label("✅").classes("partner-cartridge-status partner-status-active")
                                ui.label(f'💰 {daily:.2f} GND/день').classes("partner-cartridge-metrics")
                                ui.label(f'📈 ROI: {roi}%').classes("partner-cartridge-metrics partner-metric-positive")
                        else:
                            with ui.card().classes("partner-missing"):
                                with ui.row().classes("partner-cartridge-row"):
                                    ui.label(c["icon"]).classes("partner-cartridge-icon-missing")
                                    ui.label(c["name"]).classes("partner-cartridge-name-missing")
                                    ui.label("❌").classes("partner-cartridge-status partner-status-missing")
                                ui.label("не установлен").classes("partner-cartridge-missing-text")
                                btn = ui.label("📦 установить").classes("partner-buy-btn")
                                btn.on("click", lambda m=c["id"]: ui.navigate.to("/cartridges"))
                
                # ========== ЦЕНТР ==========
                with ui.column().classes("partner-center"):
                    ui.label("🌍").classes("partner-map-icon")
                    ui.label("ГЛОБАЛЬНАЯ КАРТА ЭКСПАНСИИ").classes("partner-map-title")
                    ui.label("скоро здесь будут студии партнёров").classes("partner-map-subtitle")
                
                                # ========== ПРАВАЯ ПАНЕЛЬ ==========
                with ui.column().classes("partner-right").style("width:320px;padding:16px;flex-shrink:0;"):
                    with ui.card().classes("partner-card"):
                        ui.label("🌍 GLOBAL POOL").classes("partner-metric-label")
                        ui.label("1234.56 GND").classes("partner-metric-value")
                    
                    with ui.card().classes("partner-card"):
                        ui.label("💰 ТВОЙ БАЛАНС").classes("partner-metric-label")
                        ui.label(f"{real_balance:.2f} GND").classes("partner-metric-value")
                        ui.label(f"💡 {real_fuel:.0f} топлива").classes("partner-metric-small")
                    
                    ui.button("⛽ КУПИТЬ ТОПЛИВО", on_click=lambda: ui.notify("Покупка топлива (скоро)", type="info")).classes("partner-buy-fuel-btn")