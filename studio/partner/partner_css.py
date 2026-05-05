# studio/partner/partner_css.py — Стили Панели Партнёра

PARTNER_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; width: 100%; overflow: hidden; }

.partner-page { 
    background: #0a0c12; 
    height: 100vh;
    width: 100%;
    font-family: 'Inter', 'JetBrains Mono', monospace; 
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: auto;
}
.partner-grid { 
    display: flex; 
    flex-direction: column; 
    height: 100vh; 
    width: 100%;
}
.partner-header { 
    background: linear-gradient(135deg, #0a0c12 0%, #121520 100%);
    border-bottom: 1px solid rgba(212, 175, 55, 0.2);
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
}
.partner-brand { 
    font-size: 0.85rem; 
    font-family: 'JetBrains Mono', monospace;
    background: linear-gradient(135deg, #d4af37 0%, #ffd700 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.partner-btn {
    background: #121520;
    border: 1px solid rgba(212, 175, 55, 0.2);
    color: rgba(212, 175, 55, 0.8);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
}
.partner-left, .partner-right { background: #08090e; overflow-y: auto; }
.partner-panel-title { 
    color: rgba(212, 175, 55, 0.5); 
    font-size: 0.7rem; 
    margin-bottom: 8px; 
    text-transform: uppercase; 
    letter-spacing: 1px; 
    font-family: 'JetBrains Mono', monospace;
}
.partner-row { flex: 1; display: flex; min-height: 0; }
.partner-missing {
    opacity: 0.5;
    background: #0f1117;
    border: 1px solid rgba(212, 175, 55, 0.1);
}
.partner-installed {
    background: #0f1117;
    border: 1px solid rgba(212, 175, 55, 0.2);
}
.partner-buy-btn {
    background: rgba(212, 175, 55, 0.1);
    border: 1px solid rgba(212, 175, 55, 0.3);
    color: #d4af37;
    font-size: 0.55rem;
    padding: 4px 10px;
    border-radius: 12px;
    cursor: pointer;
    margin-top: 6px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
}
.partner-buy-btn:hover { background: rgba(212, 175, 55, 0.2); }

/* ===== МЕТРИКИ ПРАВОЙ ПАНЕЛИ ===== */
.partner-metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(212, 175, 55, 0.5);
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.partner-metric-value {
    font-family: 'Inter', 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: bold;
    color: #d4af37;
}
.partner-metric-small {
    font-size: 0.65rem;
    color: rgba(212, 175, 55, 0.7);
}

/* ===== КАРТОЧКИ ЛЕВОЙ ПАНЕЛИ ===== */
.partner-installed, .partner-missing {
    margin-bottom: 8px;
    border-radius: 8px;
    padding: 10px;
}
.partner-cartridge-row {
    display: flex;
    align-items: center;
    gap: 8px;
}
.partner-cartridge-icon {
    font-size: 1.2rem;
}
.partner-cartridge-name {
    font-size: 0.75rem;
    font-weight: bold;
    color: #d4af37;
}
.partner-cartridge-status {
    font-size: 0.7rem;
    margin-left: auto;
}
.partner-status-active {
    color: #50fa7b;
}
.partner-cartridge-metrics {
    font-size: 0.6rem;
    color: rgba(220, 225, 240, 0.7);
}
.partner-metric-positive {
    color: #50fa7b;
}
.partner-cartridge-missing-text {
    font-size: 0.5rem;
    color: rgba(212, 175, 55, 0.3);
}

/* ===== КАРТОЧКИ ПРАВОЙ ПАНЕЛИ ===== */
.partner-card {
    background: #0f1117;
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
}
.partner-buy-fuel-btn {
    width: 100%;
    margin-top: 12px;
    background: #d4af37;
    color: #0a0c12;
    font-weight: bold;
    padding: 10px;
    border-radius: 8px;
    cursor: pointer;
    text-align: center;
}

/* ===== ЦЕНТР ===== */
.partner-center {
    flex: 1;
    background: #06080c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 0;
}
.partner-map-icon {
    font-size: 5rem;
}
.partner-map-title {
    color: rgba(212, 175, 55, 0.5);
    font-family: monospace;
    text-align: center;
}
.partner-map-subtitle {
    color: rgba(212, 175, 55, 0.3);
    font-size: 0.6rem;
    margin-top: 8px;
    text-align: center;
}
</style>
"""