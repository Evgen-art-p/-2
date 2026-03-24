"""
Assembly — CSS styles (glass UI)
"""

ASSEMBLY_CSS = r"""
:root{
  --bg: #050510; --glass: rgba(13, 17, 23, 0.60);
  --stroke: rgba(255,255,255,0.10); --g: #00ff88; --b: #00ccff; --orange: #ff9500;
}
#bg-asm{
  position: fixed; inset: 0; z-index: -1;
  background-image: url('/images/bg_main.jpg');
  background-size: cover; background-position: center;
}
#bg-asm::after{
  content:''; position:absolute; inset:0;
  background: radial-gradient(1000px 700px at 20% 10%, rgba(189,0,255,0.12), transparent 60%),
              radial-gradient(900px 650px at 80% 25%, rgba(0,204,255,0.10), transparent 55%),
              rgba(0,0,0,0.40);
  backdrop-filter: blur(10px);
}
.asm-app{
  position: fixed; inset: 0; display: grid; width: 100vw; height: 100vh;
  grid-template-columns: 280px 1fr 280px; grid-template-rows: 72px 1fr;
  grid-template-areas: "header header header" "left stage right";
  gap: 16px; padding: 16px; box-sizing: border-box;
}
.area-header{ grid-area: header; }
.area-left{ grid-area: left; min-height:0; }
.area-stage{ grid-area: stage; min-height:0; }
.area-right{ grid-area: right; min-height:0; }
.glass{
  background: var(--glass); border: 1px solid var(--stroke);
  border-radius: 20px; backdrop-filter: blur(16px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.45); min-height: 0;
}
.squad-deck{
  height: 100%; display: flex; justify-content: space-between;
  align-items: center; padding: 0 20px;
}
.panel-title{
  padding: 8px 16px; color: rgba(255,255,255,0.92);
  font-weight: 900; letter-spacing: .12em; text-transform: uppercase; font-size: 11px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.panel-body{ padding: 8px 16px; min-height: 0; overflow-y: auto; }
.left-col{ height: 100%; display: flex; flex-direction: column; min-height: 0; }
.right-col{ height: 100%; display: grid; grid-template-rows: auto 50px auto 50px auto 1fr; min-height: 0; overflow: hidden; }
.prompt-area{
  padding: 8px 16px;
  height: calc(100vh - 440px) !important;
  min-height: 120px !important;
  max-height: calc(100vh - 440px) !important;
  overflow-y: auto !important;
}
.prompt-area > div{ height: 100%; }
.pub-area{
  padding: 8px 16px;
  overflow-y: auto !important;
  min-height: 0;
}
.pub-area .info-block{ max-height: none; height: auto; }
.info-placeholder{ color: rgba(255,255,255,0.25); font-size: 11px; font-style: italic; }
.info-block{
  padding:10px 14px; background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.06); border-radius:12px;
  color:rgba(255,255,255,0.65); font-size:11px; line-height:1.5;
  font-family:'JetBrains Mono', monospace; overflow-y:auto;
}
.stats-box{
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px; padding: 12px 16px;
}
.st-row{ display:flex; justify-content:space-between; margin-bottom:6px; }
.st-row:last-child{ margin-bottom:0; }
.st-l{ color:rgba(255,255,255,0.45); font-size:11px; }
.st-v{ color:white; font-weight:700; font-size:12px; }
.st-v.g{ color: #00ff88; }
.st-v.b{ color: #00ccff; }
.neon-btn{
  height: 42px; width: 100%; border-radius: 14px; background: transparent;
  color: rgba(255,255,255,0.92); border: 1px solid rgba(255,255,255,0.10);
  font-weight: 900; letter-spacing: .10em; cursor: pointer; transition: all 0.3s ease;
}
.neon-btn.g{ border-color: rgba(0,255,136,0.35); background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10)); }
.neon-btn.o{ border-color: rgba(255,149,0,0.35); background: linear-gradient(135deg, rgba(255,149,0,0.15), rgba(255,80,80,0.08)); }
.assets-grid{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px; padding: 4px;
}
.asset-card{
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; overflow: hidden; cursor: pointer; transition: all 0.3s; position: relative;
}
.asset-card:hover{ border-color: rgba(0,204,255,0.4); transform: translateY(-2px); }
.asset-card.selected{ border-color: rgba(0,255,136,0.6) !important; }
.asset-card.active-card{ border-color: rgba(0,204,255,0.6) !important; }
.asset-ph{
  width:100%; aspect-ratio:9/16; background: rgba(255,255,255,0.04);
  display:grid; place-items:center; color:rgba(255,255,255,0.2); font-size:2rem;
}
.asset-info{ padding: 8px 12px; }
.asset-lbl{ color:rgba(255,255,255,0.85); font-weight:700; font-size:11px; }
.asset-chk{
  position:absolute; top:8px; right:8px; width:24px; height:24px; border-radius:50%;
  background:rgba(0,255,136,0.85); display:grid; place-items:center;
  color:#000; font-weight:900; font-size:11px; opacity:0; transition:opacity 0.2s;
}
.asset-card.selected .asset-chk{ opacity:1; }
.sec-head{
  color: rgba(255,255,255,0.75); font-weight: 900; font-size: 11px;
  letter-spacing: 0.10em; text-transform: uppercase; padding: 8px 0; margin-top: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.editor-label{
  color: rgba(255,255,255,0.4); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;
}
.area-left textarea,
.area-left .q-field__native{
  color: white !important;
  -webkit-text-fill-color: white !important;
}
.prog-box{ padding:10px 14px; background:rgba(255,149,0,0.08); border:1px solid rgba(255,149,0,0.2); border-radius:12px; }
.prog-lbl{ color:rgba(255,149,0,0.9); font-size:11px; font-weight:700; margin-bottom:6px; }
.prog-track{ height:4px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden; }
.prog-fill{ height:100%; border-radius:3px; transition:width 0.5s; background:linear-gradient(90deg,#ff9500,#00ff88); }
"""
