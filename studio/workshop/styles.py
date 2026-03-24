# studio/ui_workshop_styles.py — CSS стили студии
# Вынесено из ui_workshop.py (строки 1419-1809)

IDENTITY_BUREAU_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root{
  --bg: #050510;
  --text: #ffffff;
  --muted: #8899a6;
  --glass: rgba(13, 17, 23, 0.60);
  --stroke: rgba(255,255,255,0.10);
  --g: #00ff88;
  --b: #00ccff;
  --p: #bd00ff;
  --orange: #ff9500;
}

html, body { height: 100%; margin: 0; }
body{
  width:100vw;
  height:100vh;
  overflow:hidden !important;
  background: transparent !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

#bg{
  position: fixed;
  inset: 0;
  z-index: -1;
  background-image: url('/images/bg_main.jpg');
  background-size: cover;
  background-position: center;
}
#bg::after{
  content:'';
  position:absolute;
  inset:0;
  background: radial-gradient(1000px 700px at 20% 10%, rgba(189,0,255,0.12), transparent 60%),
              radial-gradient(900px 650px at 80% 25%, rgba(0,204,255,0.10), transparent 55%),
              rgba(0,0,0,0.40);
  backdrop-filter: blur(10px);
}

.app-container{
  position: fixed;
  inset: 0;
  display: grid;
  width: 100vw;
  height: 100vh;
  grid-template-columns: 300px 1fr 260px;
  grid-template-rows: 80px 1fr;
  grid-template-areas:
    "header header header"
    "left   stage  right";
  gap: 20px;
  padding: 20px;
  box-sizing: border-box;
}

.area-header{ grid-area: header; }
.area-left{ grid-area: left; min-height:0; }
.area-stage{ grid-area: stage; min-height:0; position: relative; overflow: hidden; }
.area-right{ grid-area: right; min-height:0; }

.glass{
  background: var(--glass);
  border: 1px solid var(--stroke);
  border-radius: 20px;
  backdrop-filter: blur(16px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.45);
  min-height: 0;
}

.squad-deck{
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 16px;
  gap: 15px;
  overflow-x: auto;
}

.avatar{
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: 2px solid rgba(255,255,255,0.14);
  background: radial-gradient(circle at 30% 20%, rgba(255,255,255,0.16), rgba(255,255,255,0.04));
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: rgba(255,255,255,0.92);
  font-weight: 800;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.avatar:hover{ border-color: rgba(0,204,255,0.40); transform: scale(1.05); }
.avatar.active{
  border-color: rgba(0,204,255,0.75);
  box-shadow: 0 0 0 2px rgba(0,204,255,0.25) inset, 0 0 30px rgba(0,204,255,0.35);
}
.avatar.working{
  border-color: rgba(255,149,0,0.75);
  animation: pulse 1.5s ease-in-out infinite;
}
.avatar.done{
  border-color: rgba(0,255,136,0.75);
  box-shadow: 0 0 0 2px rgba(0,255,136,0.25) inset, 0 0 30px rgba(0,255,136,0.35);
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

.left-col{ height: 100%; display: flex; flex-direction: column; gap: 12px; min-height: 0; }

.client-panel{ flex-shrink: 0; overflow: hidden; }
.asset-bay{ height: 120px; flex-shrink: 0; overflow: hidden; }
.settings-panel{ flex-grow: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }

.panel-title{
  padding: 12px 16px;
  color: rgba(255,255,255,0.92);
  font-weight: 900;
  letter-spacing: .12em;
  text-transform: uppercase;
  font-size: 11px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.panel-body{ padding: 12px 16px; min-height: 0; overflow: auto; }

.setting-row{ margin-bottom: 14px; }
.setting-label{
  color: rgba(255,255,255,0.70);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.file-list{ padding: 8px 12px; max-height: 50px; overflow-y: auto; font-family: monospace; font-size: 11px; }

.right-col{ height: 100%; display: flex; flex-direction: column; justify-content: flex-end; gap: 12px; }
.right-top-slot{
  flex-shrink: 0;
  height: 240px;
  border-radius: 20px;
  border: 1px dashed rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.04);
  display: grid;
  place-items: center;
  color: rgba(255,255,255,0.55);
  font-size: 11px;
  padding: 12px;
  text-align: center;
  overflow: hidden;
}

.runs-panel{
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.runs-list{
  padding: 8px 12px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.run-item{
  padding: 8px 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.run-item:hover{
  background: rgba(0,204,255,0.08);
  border-color: rgba(0,204,255,0.25);
}
.run-item-name{
  font-size: 10px;
  color: rgba(255,255,255,0.75);
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.run-item-delete{
  font-size: 12px;
  cursor: pointer;
  color: rgba(255,255,255,0.3);
  transition: color 0.2s;
  flex-shrink: 0;
}
.run-item-delete:hover{
  color: rgba(255,80,80,0.9);
}

.neon-btn{
  height: 56px;
  width: 100%;
  border-radius: 18px;
  background: transparent;
  color: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,255,255,0.10);
  font-weight: 900;
  letter-spacing: .10em;
  cursor: pointer;
  transition: all 0.3s ease;
}
.neon-btn:disabled{ opacity: 0.4; cursor: not-allowed; }

.neon-btn.g{
  border-color: rgba(0,255,136,0.35);
  background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10));
}
.neon-btn.g:hover:not(:disabled){ background: linear-gradient(135deg, rgba(0,255,136,0.25), rgba(0,204,255,0.15)); }

.neon-btn.b{
  border-color: rgba(0,204,255,0.35);
  background: linear-gradient(135deg, rgba(0,204,255,0.15), rgba(189,0,255,0.10));
}
.neon-btn.b:hover:not(:disabled){ background: linear-gradient(135deg, rgba(0,204,255,0.25), rgba(189,0,255,0.15)); }

.neon-btn.p{
  border-color: rgba(189,0,255,0.35);
  background: linear-gradient(135deg, rgba(189,0,255,0.15), rgba(0,204,255,0.10));
}
.neon-btn.p:hover:not(:disabled){ background: linear-gradient(135deg, rgba(189,0,255,0.25), rgba(0,204,255,0.15)); }

.stage-monitor{ height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.stage-toolbar{
  height: 60px;
  display: grid;
  grid-template-columns: 200px 1fr 200px;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
  background: rgba(13, 17, 23, 0.95);
  backdrop-filter: blur(16px);
  z-index: 10;
}

.monitor-utils{ display:flex; gap: 12px; }
.stage-content{
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 18px;
  padding-bottom: 130px;
}

.split-view{ height: 100%; display: flex; gap: 18px; min-height: 0; overflow: hidden; }
.chat-log, .viewer{
  flex: 1;
  min-height: 0;
  min-width: 0;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 14px;
  font-family: monospace;
  font-size: 13px;
  color: rgba(255,255,255,0.86);
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
}
.viewer{ border-color: rgba(0,204,255,0.30); }

.floating-console{
  position: absolute;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  width: min(820px, calc(100% - 80px));
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 50px;
  background: rgba(13, 17, 23, 0.85);
  border: 1px solid rgba(255,255,255,0.15);
  backdrop-filter: blur(20px);
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

.floating-console input{
  width: 100%;
  border-radius: 40px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.06);
  padding: 12px 16px;
  color: rgba(255,255,255,0.92);
  outline: none;
  font-family: monospace;
}

.send-button{
  border-radius: 40px !important;
  border: 2px solid rgba(0,204,255,0.55) !important;
  background: linear-gradient(135deg, rgba(0,204,255,0.30), rgba(189,0,255,0.25)) !important;
  color: rgba(255,255,255,0.98) !important;
  font-weight: 900 !important;
  padding: 12px 24px !important;
  cursor: pointer !important;
}

.util-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  background: rgba(189, 0, 255, 0.15);
  border: 1px solid rgba(189, 0, 255, 0.5);
  color: rgba(189, 0, 255, 1);
  transition: all 0.2s;
}
.util-btn:hover {
  background: rgba(189, 0, 255, 0.25);
}

.chat-msg-user {
  background: rgba(0, 204, 255, 0.1);
  border-left: 3px solid rgba(0, 204, 255, 0.6);
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 0 8px 8px 0;
}
.chat-msg-assistant {
  background: rgba(0, 255, 136, 0.08);
  border-left: 3px solid rgba(0, 255, 136, 0.6);
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 0 8px 8px 0;
}
.chat-msg-system {
  color: rgba(255,255,255,0.5);
  font-style: italic;
  padding: 4px 0;
}

.uploaded-file {
  padding: 6px 10px;
  background: rgba(189,0,255,0.15);
  border: 1px solid rgba(189,0,255,0.3);
  border-radius: 6px;
  margin: 3px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.uploaded-file img {
  max-width: 40px;
  max-height: 40px;
  border-radius: 4px;
  margin-right: 8px;
}

.client-badge{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0,204,255,0.12);
  border: 1px solid rgba(0,204,255,0.30);
  border-radius: 6px;
  font-size: 10px;
  color: rgba(0,204,255,0.90);
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-top: 6px;
}

/* Белый текст в селектах и инпутах */
.q-field__native,
.q-field__input,
.q-select__dropdown-icon {
  color: rgba(255,255,255,0.9) !important;
}

/* ═══ NUCLEAR ANTI-STRETCH ═══
   NiceGUI/Quasar вставляет wrapper div-ы между элементами.
   Эти правила ловят ВСЕ div-ы внутри stage и не дают им растянуться.
*/
.area-stage { overflow: hidden !important; }
.area-stage > * { overflow: hidden !important; min-height: 0 !important; max-height: 100% !important; }

.stage-monitor { overflow: hidden !important; height: 100% !important; }
.stage-monitor > * { min-height: 0 !important; }

.stage-toolbar { flex-shrink: 0 !important; overflow: hidden !important; }

.stage-content { flex: 1 1 0 !important; min-height: 0 !important; overflow: hidden !important; max-height: calc(100% - 60px) !important; }
.stage-content > * { min-height: 0 !important; max-height: 100% !important; overflow: hidden !important; }

.split-view { height: 100% !important; min-height: 0 !important; overflow: hidden !important; }
.split-view > * { min-height: 0 !important; overflow: hidden !important; }

.chat-log, .viewer {
  flex: 1 1 0 !important;
  min-height: 0 !important;
  max-height: 100% !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

/* NiceGUI nicegui-content wrapper */
.nicegui-content { overflow: hidden !important; height: 100% !important; }
"""
