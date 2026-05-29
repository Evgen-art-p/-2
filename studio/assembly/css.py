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
.panel-title{
  padding: 8px 16px; color: rgba(255,255,255,0.92);
  font-weight: 900; letter-spacing: .12em; text-transform: uppercase; font-size: 11px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.panel-body{ padding: 8px 16px; min-height: 0; overflow-y: auto; }
.left-col{ height: 100%; display: flex; flex-direction: column; min-height: 0; }
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
"""

MONTEUR_CSS = r"""
/* ── Мастерская Монтажёра ── */
.mt-proj-card{
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:10px;padding:10px 12px;
  margin-bottom:6px;cursor:pointer;transition:all 0.2s;
}
.mt-proj-card:hover{
  border-color:rgba(0,204,255,0.3);
  background:rgba(0,204,255,0.04);
}
.mt-proj-card.active{
  border-color:rgba(0,255,136,0.4);
  background:rgba(0,255,136,0.04);
}
.mt-proj-card.done{ opacity:0.55; }
.mt-proj-id{
  font-family:JetBrains Mono;font-size:0.65rem;
  font-weight:700;color:rgba(220,225,240,0.9);margin-bottom:3px;
}
.mt-proj-meta{
  font-family:JetBrains Mono;font-size:0.55rem;
  color:rgba(140,150,180,0.5);margin-bottom:2px;
}
.mt-proj-stats{
  font-family:JetBrains Mono;font-size:0.58rem;
  color:rgba(180,190,220,0.55);
}
.mt-empty{
  font-family:JetBrains Mono;font-size:0.6rem;
  color:rgba(140,150,180,0.3);text-align:center;
  padding:16px;line-height:1.7;
}
.mt-not-assembled{
  font-family:JetBrains Mono;font-size:0.65rem;
  color:rgba(201,168,76,0.6);text-align:center;
  padding:24px;line-height:1.7;
  background:rgba(201,168,76,0.04);
  border:1px solid rgba(201,168,76,0.1);
  border-radius:10px;
}
.mt-sec{
  font-family:JetBrains Mono;font-size:0.58rem;
  font-weight:900;letter-spacing:0.12em;
  text-transform:uppercase;color:rgba(255,255,255,0.35);
  padding:3px 0 6px;border-bottom:1px solid rgba(255,255,255,0.05);
  margin-bottom:8px;
}
.mt-meta{
  display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px;
  font-family:JetBrains Mono;font-size:0.6rem;
  color:rgba(180,190,220,0.6);
}
.mt-desc{
  font-family:JetBrains Mono;font-size:0.65rem;
  color:rgba(220,225,240,0.8);line-height:1.5;
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.06);
  border-radius:8px;padding:10px 12px;margin-bottom:8px;
}
.mt-tags{
  font-family:JetBrains Mono;font-size:0.6rem;
  color:rgba(108,140,255,0.65);margin-bottom:6px;
}
.mt-posting{
  font-family:JetBrains Mono;font-size:0.58rem;
  color:rgba(201,168,76,0.55);
}
.mt-overlay{
  font-family:JetBrains Mono;font-size:0.52rem;
  color:rgba(220,225,240,0.45);text-align:center;margin-top:3px;
}
.mt-chat-body{
  display:flex;flex-direction:column;gap:6px;
}
.mt-msg{
  padding:7px 10px;border-radius:8px;
  font-family:JetBrains Mono;
}
.mt-msg-user{
  background:rgba(108,140,255,0.07);
  border:1px solid rgba(108,140,255,0.12);
  align-self:flex-end;max-width:85%;
}
.mt-msg-ai{
  background:rgba(0,255,136,0.04);
  border:1px solid rgba(0,255,136,0.08);
  align-self:flex-start;max-width:95%;
}
.mt-msg-role{
  font-size:0.48rem;color:rgba(140,150,180,0.4);
  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:2px;
}
.mt-msg-text{
  font-size:0.7rem;color:rgba(220,225,240,0.85);line-height:1.5;
}
.mt-right-sec{
  font-family:JetBrains Mono;font-size:0.52rem;
  font-weight:700;letter-spacing:0.1em;
  text-transform:uppercase;color:rgba(140,150,180,0.35);
  padding:3px 0 4px;margin-bottom:4px;
  border-bottom:1px solid rgba(255,255,255,0.04);
}
.mt-right-item{
  padding:5px 2px;
  border-bottom:1px solid rgba(255,255,255,0.03);
  margin-bottom:2px;
}
.mt-right-id{
  font-family:JetBrains Mono;font-size:0.6rem;
  color:rgba(220,225,240,0.75);font-weight:600;
}
.mt-right-meta{
  font-family:JetBrains Mono;font-size:0.54rem;
  color:rgba(140,150,180,0.45);margin-top:1px;
}
.mt-right-ts{
  font-family:JetBrains Mono;font-size:0.5rem;
  color:rgba(140,150,180,0.28);
}
"""
