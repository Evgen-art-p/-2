# studio/workshop/cabinet_css.py — Стили Кабинета v2.1
# Обновлённый layout: [Агенты 300px] [Чат 1fr] [Правая панель 320px]
# Изменения v2.1:
#   - Шире боковые колонки (300 / 320)
#   - Крупнее и светлее текст везде
#   - Двухзонная левая колонка: резиденты (фикс) + аккордеон цехов
#   - Стили аккордеона
#   - Поиск агентов

CABINET_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ═══ PAGE ═══ */
.cabinet-page {
  width: 100vw; height: 100vh; overflow: hidden;
  background: #08090e;
  font-family: 'IBM Plex Sans', sans-serif;
  color: rgba(220,225,240,0.92);
}
.cabinet-page::before {
  content: '';
  position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(108,140,255,0.012) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108,140,255,0.012) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none; z-index: 0;
}

/* ═══ GRID — 3 колонки (ШИРЕ) ═══ */
.cab-grid {
  position: relative; z-index: 1;
  display: grid;
  grid-template-columns: 320px 1fr 480px;
  grid-template-rows: 48px 1fr;
  height: 100vh;
}

/* ═══ HEADER ═══ */
.cab-header {
  grid-column: 1 / -1;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px;
  background: #0e1018;
  border-bottom: 1px solid rgba(99,130,255,0.08);
}
.cab-brand {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 400;
  letter-spacing: 0.1em;
  color: rgba(180,190,220,0.6);
}
.cab-brand b { color: #6c8cff; font-weight: 500; }
.cab-controls { display: flex; gap: 5px; align-items: center; }
.cab-btn {
  background: #141722;
  border: 1px solid rgba(99,130,255,0.08);
  color: rgba(180,190,220,0.6);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; padding: 5px 11px;
  border-radius: 6px; cursor: pointer;
  transition: all 0.2s;
}
.cab-btn:hover { color: rgba(220,225,240,0.92); border-color: rgba(99,130,255,0.18); }
.cab-btn.active { color: #6c8cff; border-color: rgba(108,140,255,0.25); background: rgba(108,140,255,0.12); }

/* ═══ LEFT: AGENTS — ДВУХЗОННАЯ КОЛОНКА ═══ */
.cab-left {
  background: #0e1018;
  border-right: 1px solid rgba(99,130,255,0.08);
  display: flex; flex-direction: column; overflow: hidden;
}
.cab-panel-title {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(99,130,255,0.08);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500; letter-spacing: 0.06em;
  display: flex; justify-content: space-between; align-items: center;
  color: rgba(200,210,240,0.7);
}
.cab-badge {
  font-size: 0.56rem; color: #6c8cff;
  background: rgba(108,140,255,0.12);
  padding: 2px 8px; border-radius: 10px;
}
.cab-panel-title-right {
  display: flex; align-items: center; gap: 6px;
}

/* Мини-кнопка загрузки файлов в хедере левой колонки */
.cab-upload-mini {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  color: rgba(140,150,180,0.45);
  background: rgba(108,140,255,0.04);
  border: 1px solid rgba(99,130,255,0.1);
  border-radius: 5px;
  padding: 2px 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.cab-upload-mini:hover {
  color: #6c8cff;
  border-color: rgba(108,140,255,0.25);
  background: rgba(108,140,255,0.08);
}
/* Скрытие дефолтного NiceGUI upload внутри мини-обёртки */
.cab-upload-hidden .q-uploader { display: none !important; }
.cab-upload-hidden .q-btn { 
  all: unset; cursor: pointer;
}

/* ── Поиск агентов ── */
.cab-search-wrap {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(99,130,255,0.06);
}
.cab-search-input {
  width: 100%; box-sizing: border-box;
  background: #08090e;
  border: 1px solid rgba(99,130,255,0.08);
  border-radius: 6px;
  padding: 6px 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: rgba(220,225,240,0.85);
  outline: none;
  transition: border-color 0.15s;
}
.cab-search-input::placeholder {
  color: rgba(140,150,180,0.3);
}
.cab-search-input:focus {
  border-color: rgba(108,140,255,0.25);
}

/* ── Зона резидентов (фиксированная, не скроллится) ── */
.cab-residents-zone {
  padding: 8px 10px 6px;
  border-bottom: 1px solid rgba(201,168,76,0.1);
  flex-shrink: 0;
}
.cab-residents-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem; font-weight: 500;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: rgba(201,168,76,0.5);
  margin-bottom: 6px;
  padding-left: 2px;
}
.cab-residents-list {
  display: flex; flex-direction: column; gap: 3px;
}

/* Резидент — компактная карточка */
.cab-resident-card {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px;
  background: rgba(201,168,76,0.02);
  border: 1px solid rgba(201,168,76,0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.cab-resident-card:hover {
  background: rgba(201,168,76,0.05);
  border-color: rgba(201,168,76,0.22);
}
.cab-resident-card.active {
  background: rgba(201,168,76,0.06);
  border-color: rgba(201,168,76,0.35);
}
.cab-resident-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: #141722; background-size: cover; background-position: center top;
  border: 1.5px solid rgba(201,168,76,0.15);
  flex-shrink: 0;
}
.cab-resident-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 500;
  color: rgba(220,225,240,0.92);
  flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cab-resident-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem; padding: 1px 6px;
  border-radius: 8px; flex-shrink: 0;
}
.cab-status-resident {
  background: rgba(201,168,76,0.12); color: #c9a84c;
}

/* ── Зона города (скроллируемая, аккордеон) ── */
.cab-city-zone {
  flex: 1; overflow-y: auto; padding: 4px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(99,130,255,0.08) transparent;
}

/* Аккордеон — секция цеха */
.cab-dept-section {
  margin: 0 6px 2px;
}
.cab-dept-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px;
  background: rgba(108,140,255,0.03);
  border: 1px solid rgba(99,130,255,0.06);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.cab-dept-header:hover {
  background: rgba(108,140,255,0.06);
  border-color: rgba(99,130,255,0.12);
}
.cab-dept-header.open {
  background: rgba(108,140,255,0.06);
  border-color: rgba(108,140,255,0.15);
  border-radius: 6px 6px 0 0;
  margin-bottom: 0;
}
.cab-dept-header-left {
  display: flex; align-items: center; gap: 6px;
}
.cab-dept-arrow {
  font-size: 0.5rem;
  color: rgba(140,150,180,0.4);
  transition: transform 0.2s;
  display: inline-block;
}
.cab-dept-header.open .cab-dept-arrow {
  transform: rotate(90deg);
}
.cab-dept-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 500;
  color: rgba(200,210,240,0.7);
  letter-spacing: 0.04em;
}
.cab-dept-header.open .cab-dept-name {
  color: #6c8cff;
}
.cab-dept-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: rgba(140,150,180,0.35);
  background: rgba(99,130,255,0.06);
  padding: 1px 7px; border-radius: 8px;
}

/* Содержимое аккордеона (список агентов внутри цеха) */
.cab-dept-body {
  display: none;
  padding: 4px 4px 6px;
  border: 1px solid rgba(99,130,255,0.06);
  border-top: none;
  border-radius: 0 0 6px 6px;
  background: rgba(108,140,255,0.01);
}
.cab-dept-body.open {
  display: block;
}

/* OLD dept selector — DEPRECATED, оставлен для совместимости */
.cab-dept-bar {
  display: none; /* скрыт — заменён аккордеоном */
}
.cab-dept-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.52rem; padding: 2px 7px;
  border-radius: 4px; cursor: pointer;
  transition: all 0.15s;
  background: #08090e; border: 1px solid rgba(99,130,255,0.08);
  color: rgba(140,150,180,0.28);
}
.cab-dept-tag:hover { color: rgba(180,190,220,0.55); border-color: rgba(99,130,255,0.18); }
.cab-dept-tag.active {
  background: rgba(108,140,255,0.1);
  color: #6c8cff;
  border-color: rgba(108,140,255,0.2);
}

/* Agent list (OLD flat scroll — kept for fallback) */
.cab-agents { flex: 1; overflow-y: auto; padding: 6px 8px; scrollbar-width: thin; }

/* ═══ Agent card (общий — внутри аккордеона) ═══ */
.cab-agent-card {
  padding: 8px 10px; margin-bottom: 3px;
  background: #08090e;
  border: 1px solid rgba(99,130,255,0.08);
  border-radius: 6px; cursor: pointer;
  transition: all 0.15s;
}
.cab-agent-card:hover { border-color: rgba(99,130,255,0.18); background: #141722; }
.cab-agent-card.active { border-color: rgba(108,140,255,0.3); background: rgba(108,140,255,0.06); }
.cab-agent-card.stress { border-color: rgba(248,113,113,0.25); }
.cab-agent-card.block { border-color: rgba(251,191,36,0.25); }

/* Agent card — resident accent (legacy, для карточек внутри списка) */
.cab-agent-card.resident {
  border-color: rgba(201,168,76,0.2);
}
.cab-agent-card.resident:hover { border-color: rgba(201,168,76,0.35); }
.cab-agent-card.resident.active {
  border-color: rgba(201,168,76,0.4);
  background: rgba(201,168,76,0.04);
}

.cab-agent-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.cab-agent-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: #141722; background-size: cover; background-position: center top;
  border: 1.5px solid rgba(99,130,255,0.12);
  flex-shrink: 0;
}
.cab-agent-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 500;
  color: rgba(220,225,240,0.92); flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cab-agent-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem; padding: 2px 7px;
  border-radius: 8px; flex-shrink: 0;
}
.cab-status-idle { background: rgba(74,222,128,0.1); color: #4ade80; }
.cab-status-work { background: rgba(108,140,255,0.12); color: #6c8cff; }
.cab-status-stress { background: rgba(248,113,113,0.12); color: #f87171; }
.cab-status-block { background: rgba(251,191,36,0.12); color: #fbbf24; }
.cab-status-silence { background: rgba(140,150,180,0.08); color: rgba(140,150,180,0.4); }

/* Mini bars */
.cab-bars { display: flex; gap: 3px; margin-top: 4px; }
.cab-bar-group { flex: 1; }
.cab-bar-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.44rem; color: rgba(140,150,180,0.35); margin-bottom: 1px;
}
.cab-bar-track { height: 3px; background: rgba(99,130,255,0.06); border-radius: 2px; overflow: hidden; }
.cab-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }

.cab-agent-meta {
  display: flex; gap: 4px; margin-top: 3px; align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.52rem; color: rgba(140,150,180,0.35);
}

/* ═══ CENTER: CHAT ═══ */
.cab-center {
  display: flex; flex-direction: column; overflow: hidden;
  background: #08090e;
  position: relative;
}

/* ═══ CITY MAP ═══ */
.cab-map-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  transition: opacity 0.2s ease;
}
.cab-map-wrap.hidden { display: none !important; }

.cab-map-header {
  padding: 8px 16px;
  border-bottom: 1px solid rgba(99,130,255,0.08);
  background: #0e1018;
  display: flex; align-items: center; justify-content: space-between;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem; color: rgba(180,190,220,0.6);
  flex-shrink: 0;
}
.cab-map-title { color: #6c8cff; font-weight: 500; }
.cab-map-weather { color: rgba(201,168,76,0.7); }
.cab-map-btn {
  background: rgba(108,140,255,0.08);
  border: 1px solid rgba(108,140,255,0.15);
  color: #6c8cff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem; padding: 3px 10px;
  border-radius: 5px; cursor: pointer;
  transition: all 0.15s;
}
.cab-map-btn:hover { background: rgba(108,140,255,0.15); }
.cab-map-btn.walk { color: rgba(201,168,76,0.9); border-color: rgba(201,168,76,0.2); background: rgba(201,168,76,0.06); }
.cab-map-btn.walk:hover { background: rgba(201,168,76,0.12); }

.cab-map-viewport {
  flex: 1; overflow: hidden;
  cursor: grab; user-select: none; touch-action: none;
  position: relative;
}
.cab-map-viewport:active { cursor: grabbing; }

.cab-map-canvas {
  position: absolute; top: 0; left: 0;
  width: 2760px; height: 1504px;
  transform-origin: 0 0;
  background-color: #050508;
  background-image:
    radial-gradient(circle, rgba(0,242,255,0.08) 1px, transparent 1px);
  background-size: 40px 40px;
}
.cab-map-canvas.has-bg {
  background-image:
    radial-gradient(circle, rgba(0,242,255,0.08) 1px, transparent 1px),
    url('/static/GRONDHEM.png');
  background-size: 40px 40px, 2760px 1504px;
  background-position: 0 0, center;
  background-repeat: repeat, no-repeat;
}

/* Сектора */
.cab-map-sector {
  position: absolute; border-radius: 8px;
  border: 2px solid rgba(0,180,200,0.85);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 8px 14px;
  pointer-events: none;
  background: transparent;
  color: rgba(220,255,255,0.98);
  text-shadow:
    0 0 6px rgba(0,200,220,0.9),
    0 0 14px rgba(0,180,200,0.6),
    0 1px 3px rgba(0,0,0,0.95);
}

/* Агент на карте — точка 10px */
.cab-map-agent {
  position: absolute;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: rgba(80,250,123,0.8);
  border: 1px solid rgba(80,250,123,0.4);
  display: flex; align-items: center; justify-content: center;
  font-size: 0;  /* скрыть эмодзи */
  cursor: pointer;
  transition: all 0.15s;
  z-index: 10;
}
.cab-map-agent:hover {
  width: 14px; height: 14px;
  border-color: rgba(220,225,240,0.9);
  background: rgba(108,140,255,0.9);
  z-index: 30;
}
.cab-map-agent.selected {
  width: 14px; height: 14px;
  background: rgba(108,140,255,0.9);
  border: 2px solid #6c8cff;
  box-shadow: 0 0 12px rgba(108,140,255,0.6);
  z-index: 20;
}
.cab-map-agent.stressed {
  background: rgba(255,80,80,0.8);
  border-color: rgba(255,60,60,0.6);
  animation: pulse-stress 2s infinite;
}
.cab-map-agent.walking {
  background: rgba(201,168,76,0.8);
  border-color: rgba(201,168,76,0.5);
  animation: pulse-walk 1.5s infinite;
}
@keyframes pulse-stress {
  0%,100% { box-shadow: 0 0 0 0 rgba(255,60,60,0.5); }
  50% { box-shadow: 0 0 0 6px rgba(255,60,60,0); }
}
@keyframes pulse-walk {
  0%,100% { box-shadow: 0 0 0 0 rgba(201,168,76,0.4); }
  50% { box-shadow: 0 0 0 6px rgba(201,168,76,0); }
}

/* Подпись агента — скрыта, появляется по hover */
.cab-map-agent-label {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 50%; transform: translateX(-50%);
  white-space: nowrap;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: rgba(220,225,240,0.95);
  background: rgba(8,9,14,0.92);
  padding: 2px 6px; border-radius: 3px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
}
.cab-map-agent:hover .cab-map-agent-label { opacity: 1; }
.cab-map-agent.selected .cab-map-agent-label { opacity: 1; }

/* Последняя локация — скрыта, появляется по hover */
.cab-map-agent-loc {
  position: absolute;
  top: calc(100% + 4px);
  left: 50%; transform: translateX(-50%);
  white-space: nowrap;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.42rem;
  color: rgba(201,168,76,0.7);
  background: rgba(8,9,14,0.85);
  padding: 1px 5px; border-radius: 3px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
}
.cab-map-agent:hover .cab-map-agent-loc { opacity: 1; }

/* Кнопка "назад к карте" */
.cab-back-to-map {
  display: none;
  padding: 6px 14px;
  border-bottom: 1px solid rgba(99,130,255,0.08);
  background: #0e1018;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; color: rgba(108,140,255,0.7);
  cursor: pointer; align-items: center; gap: 6px;
  flex-shrink: 0;
}
.cab-back-to-map.visible { display: flex; }
.cab-back-to-map:hover { color: #6c8cff; }
.cab-active-prompt {
  padding: 8px 16px;
  border-bottom: 1px solid rgba(99,130,255,0.08);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; color: #6c8cff;
  background: rgba(108,140,255,0.06);
  display: none; align-items: center; justify-content: space-between;
}
.cab-active-prompt.visible { display: flex; }
.cab-chat { flex: 1; overflow-y: auto; padding: 24px 32px; scrollbar-width: thin; }
.cab-msg { margin-bottom: 20px; max-width: 85%; animation: cabMsgIn 0.3s ease; }
@keyframes cabMsgIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; } }
.cab-msg-user { margin-left: auto; text-align: right; }
.cab-msg-role {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem; letter-spacing: 0.08em;
  margin-bottom: 5px; text-transform: uppercase; font-weight: 500;
}
.cab-msg-user .cab-msg-role { color: rgba(108,140,255,0.85); }
.cab-msg-ai .cab-msg-role { color: rgba(167,139,250,0.9); }
.cab-msg-text {
  font-size: 1.0rem; line-height: 1.8;
  white-space: pre-wrap; word-break: break-word;
}
.cab-msg-user .cab-msg-text { color: rgba(210,218,245,0.85); }
.cab-msg-ai .cab-msg-text { color: rgba(225,232,248,0.92); }
.cab-msg-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.52rem; color: rgba(140,150,180,0.3); margin-top: 5px;
}
.cab-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 8px;
}
.cab-empty-icon { font-size: 2rem; opacity: 0.12; }
.cab-empty-text { color: rgba(140,150,180,0.3); font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; }
.cab-typing { color: rgba(167,139,250,0.9); font-size: 0.9rem; opacity: 0.5; animation: cabPulse 1.2s ease-in-out infinite; }
@keyframes cabPulse { 0%,100% { opacity: 0.25; } 50% { opacity: 0.7; } }

/* Input */
.cab-input-area { padding: 14px 20px; border-top: 1px solid rgba(99,130,255,0.08); background: #0e1018; }

/* ═══ RIGHT: TABS PANEL ═══ */
.cab-right {
  background: #0e1018;
  border-left: 1px solid rgba(99,130,255,0.08);
  display: flex; flex-direction: column; overflow: hidden;
}
.cab-tabs { display: flex; border-bottom: 1px solid rgba(99,130,255,0.08); }
.cab-tab {
  flex: 1; background: none; border: none;
  color: rgba(140,150,180,0.4);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; letter-spacing: 0.06em; text-transform: uppercase;
  padding: 10px 4px; cursor: pointer; transition: all 0.2s;
  border-bottom: 2px solid transparent; text-align: center;
}
.cab-tab:hover { color: rgba(180,190,220,0.6); }
.cab-tab.active { color: #6c8cff; border-bottom-color: #6c8cff; }

.cab-tab-content { flex: 1; overflow-y: auto; padding: 10px 12px; scrollbar-width: thin; }

/* ═══ RIGHT TAB: AGENT DETAIL ═══ */
.cab-detail-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; color: rgba(140,150,180,0.45);
  letter-spacing: 0.06em; text-transform: uppercase;
  margin-bottom: 6px; padding-bottom: 4px;
  border-bottom: 1px solid rgba(99,130,255,0.08);
}
.cab-dna-row {
  display: flex; justify-content: space-between; align-items: center; padding: 3px 0;
}
.cab-dna-label { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: rgba(180,190,220,0.7); }
.cab-dna-val { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: #6c8cff; min-width: 28px; text-align: right; }
.cab-dna-bar { flex: 1; margin: 0 8px; height: 4px; background: rgba(99,130,255,0.06); border-radius: 2px; overflow: hidden; }
.cab-dna-fill { height: 100%; border-radius: 2px; }

.cab-anchor-tag {
  display: inline-block; font-family: 'JetBrains Mono', monospace;
  font-size: 0.52rem; padding: 2px 7px; margin: 2px;
  border-radius: 4px;
  background: rgba(167,139,250,0.1); color: rgba(167,139,250,0.85);
}
.cab-talk-btn {
  width: 100%; margin-top: 8px;
  background: rgba(167,139,250,0.08);
  border: 1px solid rgba(167,139,250,0.15);
  color: rgba(167,139,250,0.85);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; padding: 8px;
  border-radius: 6px; cursor: pointer; text-align: center;
  transition: all 0.15s;
}
.cab-talk-btn:hover { background: rgba(167,139,250,0.15); }

/* Detail avatar (large) */
.cab-detail-avatar {
  width: 220px; height: 220px; border-radius: 50%;
  background: #141722; background-size: cover; background-position: center top;
  border: 2px solid rgba(99,130,255,0.15);
  margin: 0 auto 6px;
}

/* ═══ RIGHT TAB: FILES ═══ */
.cab-file-item {
  padding: 7px 10px; margin-bottom: 3px;
  background: #08090e;
  border: 1px solid rgba(99,130,255,0.08);
  border-radius: 6px;
  display: flex; justify-content: space-between; align-items: center;
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
}
.cab-file-name { color: rgba(220,225,240,0.85); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.cab-file-size { color: rgba(140,150,180,0.35); margin: 0 8px; font-size: 0.52rem; }
.cab-file-del { color: rgba(140,150,180,0.35); cursor: pointer; transition: color 0.15s; }
.cab-file-del:hover { color: #f87171; }

/* ═══ RIGHT TAB: PROMPTS ═══ */
.cab-prompt-item {
  padding: 8px 12px; margin-bottom: 3px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; color: rgba(180,190,220,0.65);
  border-radius: 6px; cursor: pointer; transition: all 0.15s;
}
.cab-prompt-item:hover { background: #141722; color: rgba(220,225,240,0.92); }
.cab-prompt-item.active { background: rgba(108,140,255,0.12); color: #6c8cff; }

/* ═══ RIGHT TAB: ARCHIVE ═══ */
.cab-archive-item {
  padding: 8px 12px; margin-bottom: 4px;
  background: #08090e;
  border: 1px solid rgba(99,130,255,0.08);
  border-radius: 6px;
  display: flex; align-items: center; gap: 8px;
  transition: background 0.15s;
}
.cab-archive-item:hover { background: #141722; }

/* ═══ NiceGUI overrides ═══ */
.nicegui-content { overflow: hidden !important; height: 100% !important; padding: 0 !important; margin: 0 !important; }
.q-page { padding: 0 !important; }
.q-field__native, .q-field__input { color: rgba(220,225,240,0.92) !important; }

/* === REPORTS TAB === */
.rep-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 8px 6px;
}
.rep-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  color: rgba(180,190,220,0.45);
}
.rep-scroll {
  overflow-y: auto;
  max-height: calc(100vh - 160px);
  scrollbar-width: thin;
}
.rep-card {
  padding: 10px 12px; margin: 4px 6px;
  border-radius: 8px; cursor: pointer;
  transition: opacity 0.15s;
}
.rep-card:hover { opacity: 0.88; }
.rep-card-morning {
  background: rgba(255,180,50,0.04);
  border: 1px solid rgba(255,180,50,0.14);
}
.rep-card-night {
  background: rgba(108,80,200,0.04);
  border: 1px solid rgba(108,80,200,0.18);
}
.rep-card-head {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 5px;
}
.rep-card-title-morning {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(255,180,50,0.85);
}
.rep-card-title-night {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(160,130,240,0.85);
}
.rep-card-ts {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem;
  color: rgba(160,170,200,0.5);
}
.rep-summary {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.66rem; margin-bottom: 3px;
}
.rep-genius   { color: rgba(255,100,80,0.9); }
.rep-normal   { color: rgba(255,210,90,0.7); }
.rep-safe     { color: rgba(100,190,255,0.7); }
.rep-recovery { color: rgba(160,170,200,0.6); }
.rep-sleep    { color: rgba(160,170,200,0.55); }
.rep-restless { color: rgba(255,210,90,0.7); }
.rep-revolt   { color: rgba(255,100,80,0.95); }
.rep-details  {
  display: none; margin-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 6px;
}
.rep-detail-block {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem; line-height: 1.55; margin-top: 4px;
}
.rep-detail-morning   { color: rgba(190,200,225,0.65); }
.rep-detail-revolts   { color: rgba(255,120,80,0.9); }
.rep-detail-resentful { color: rgba(220,100,100,0.8); }
.rep-detail-restless  { color: rgba(210,190,90,0.7); }
.rep-detail-empty {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: rgba(180,190,220,0.5);
  text-align: center;
  padding: 8px 0 2px;
}
"""
