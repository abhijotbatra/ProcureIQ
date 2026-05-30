
/* ProcureIQ Dashboard — Complete JavaScript */
'use strict';

// ═══ STATE ═══════════════════════════════════════════════════════
const State = { page:'command', engineRunning:false, logCount:0, allSuppliers:[], mobOpen:false };
const PAGES = ['command','signals','positions','demand','engine','suppliers','trades','costs','news','perf'];
const AGENT_NAMES = [
  {n:'Risk Monitor',  task:'Scanning news + supplier feeds…', c:'var(--rd)'},
  {n:'Demand Forecast',task:'Loading 12-week demand data…',   c:'var(--bl)'},
  {n:'Inv Analyst',  task:'Scanning warehouse DB…',          c:'var(--am)'},
  {n:'Sup Scorer',   task:'Running KPI scorecard…',          c:'var(--gr)'},
  {n:'Cost Optimizer',task:'Querying pricing APIs…',         c:'var(--pu)'},
];
const FC_WEEKS  = ['W17','W18','W19','W20','W21','W22','W23','W24','W25','W26','W27','W28'];
const FC_ACT    = [820,910,875,960,1040,null,null,null,null,null,null,null];
const FC_PRJ    = [null,null,null,null,1040,1090,1180,1250,1310,1200,1150,1280];
const MOCK_LOGS = [
  {t:'',a:'Orchestrator',m:'Dispatch to 5 agents complete',c:'color:var(--gr)'},
  {t:'',a:'Risk Monitor',m:'Shanghai port delay confirmed via Flexport API',c:'color:var(--rd)'},
  {t:'',a:'Inv Analyst', m:'9 SKUs below critical threshold — flag raised',c:'color:var(--am)'},
  {t:'',a:'Cost Optimizer',m:'PackagePro quote $0.12/unit vs VendorX $0.19',c:'color:var(--pu)'},
  {t:'',a:'Sup Scorer',  m:'VendorX credit downgrade detected (S&P feed)',c:'color:var(--rd)'},
  {t:'',a:'Dem Forecast', m:'Q3 model retrained — accuracy 91.2%',c:'color:var(--gr)'},
];

// ═══ NAVIGATION ══════════════════════════════════════════════════
function goto(page){
  PAGES.forEach(p=>{
    const pg=document.getElementById('page-'+p);
    const nv=document.getElementById('nav-'+p);
    if(pg) pg.classList.toggle('active',p===page);
    if(nv) nv.classList.toggle('active',p===page);
  });
  State.page=page;
  document.getElementById('main').scrollTop=0;
  closeMobile();
  loadPage(page);
}

function loadPage(page){
  if(page==='command')   loadCommand();
  if(page==='signals')   loadSignals();
  if(page==='positions') loadPositions();
  if(page==='demand')    loadDemand();
  if(page==='engine')    loadEngine();
  if(page==='suppliers') loadSuppliers();
  if(page==='trades')    loadTrades();
  if(page==='costs')     loadCosts();
  if(page==='news')      loadNews();
  if(page==='perf')      loadPerf();
}

// ═══ SIDEBAR ═════════════════════════════════════════════════════
function toggleSidebar(){
  const sb=document.getElementById('sidebar');
  if(window.innerWidth<=700){ toggleMobile(); return; }
  sb.classList.toggle('collapsed');
}
function toggleMobile(){
  State.mobOpen=!State.mobOpen;
  document.getElementById('sidebar').classList.toggle('mob-open',State.mobOpen);
}
function closeMobile(){
  State.mobOpen=false;
  document.getElementById('sidebar').classList.remove('mob-open');
}

// ═══ TABS ════════════════════════════════════════════════════════
function switchTab(el){
  const p=el.closest('.card')||el.closest('.content');
  p.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
}

// ═══ API HELPERS ═════════════════════════════════════════════════
async function api(url){ try{ const r=await fetch(url); return await r.json(); }catch(e){ console.warn(url,e); return {}; } }
async function post(url,body={}){ try{ const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); return await r.json(); }catch(e){ console.warn(url,e); return {}; } }

// ═══ OVERLAY ═════════════════════════════════════════════════════
function showOverlay(){
  const ov=document.getElementById('overlay');
  document.getElementById('ov-agents').innerHTML=AGENT_NAMES.map(a=>`
    <div class="orow"><div class="spin" style="border-top-color:${a.c}"></div>
    <div><div class="on">${a.n}</div><div class="os">${a.task}</div></div></div>`).join('');
  ov.classList.add('show');
  const pf=document.getElementById('pf'); pf.style.width='0';
  let p=0; const iv=setInterval(()=>{ p=Math.min(p+2.5,100); pf.style.width=p+'%'; if(p>=100)clearInterval(iv); },70);
}
function hideOverlay(){ document.getElementById('overlay').classList.remove('show'); }

// ═══ TOAST ═══════════════════════════════════════════════════════
let toastTimer;
function toast(title,msg){
  document.getElementById('tt').textContent=title;
  document.getElementById('tm').textContent=msg;
  const t=document.getElementById('toast'); t.classList.add('show');
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>t.classList.remove('show'),3200);
}

// ═══ RUN ANALYSIS ════════════════════════════════════════════════
async function runAnalysis(){
  const q=document.getElementById('gq')?.value||'Which suppliers are at risk and what should I reorder?';
  showOverlay();
  const result=await post('/api/analyze',{query:q});
  hideOverlay();
  if(result.action_plan){
    showRAG(result);
    updateMetrics(result);
    toast('Analysis complete',`${result.critical_count||0} critical · $${((result.total_savings_found||0)/1000).toFixed(0)}K savings found`);
  } else {
    toast('Analysis','Running — check logs');
  }
  loadPage(State.page);
}

function showRAG(result){
  const card=document.getElementById('rag-card');
  if(!card) return;
  card.style.display='block';
  const ts=document.getElementById('rag-ts');
  const body=document.getElementById('rag-body');
  if(ts) ts.textContent='Generated '+new Date().toLocaleTimeString()+' · '+((result.processing_time_seconds||0).toFixed(1))+'s';
  if(body) body.innerHTML=result.action_plan?.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')||'';
  card.scrollIntoView({behavior:'smooth',block:'nearest'});
}

function updateMetrics(result){
  const savings=result.total_savings_found||84000;
  const critical=result.critical_count||3;
  setEl('m-crit',critical);
  setEl('m-sav','$'+fmtK(savings));
  setEl('sig-crit',critical);
  setEl('critical-badge',critical+' CRITICAL');
  setEl('nc-sig',critical);
  setEl('nc-inv',result.inventory_alerts?.length||9);
  setEl('cost-total','$'+fmtK(savings));
  setEl('cost-count',(result.cost_opportunities||[]).length);
  setEl('cost-badge','$'+fmtK(savings)+' SAVINGS');
}

function fmtK(v){ return v>=1000?(v/1000).toFixed(0)+'K':v.toFixed(0); }
function setEl(id,v){ const e=document.getElementById(id); if(e) e.textContent=v; }

// ═══ ENGINE CONTROL ══════════════════════════════════════════════
async function toggleEngine(){
  if(State.engineRunning){
    await post('/api/engine/stop');
    State.engineRunning=false;
    setEl('engine-badge','ENGINE OFF');
    setEl('eng-btn','▶ Start Engine');
    setEl('eng-status','STOPPED');
    setEl('sbst','engine stopped');
    toast('Engine stopped','ProcureIQ engine halted');
  } else {
    await post('/api/engine/start');
    State.engineRunning=true;
    setEl('engine-badge','ENGINE ON');
    setEl('eng-btn','■ Stop Engine');
    setEl('eng-status','RUNNING');
    setEl('sbst','5 agents running');
    toast('Engine started','ProcureIQ engine running');
  }
  const btn=document.getElementById('eng-btn');
  if(btn) btn.className=State.engineRunning?'bs':'bp';
}

async function exportData(){
  window.open('/api/export','_blank');
  toast('Export started','Download will begin shortly');
}

// ═══ PAGE LOADERS ════════════════════════════════════════════════

async function loadCommand(){
  const [port,inv]=await Promise.all([api('/api/portfolio'),api('/api/inventory')]);
  // metrics
  setEl('m-sup',port.suppliers_tracked||142);
  setEl('m-crit',port.critical_alerts||3);
  setEl('m-sav','$'+fmtK(port.savings_found||84000));
  setEl('m-sto',port.stockout_risk_14d||9);
  setEl('engine-badge',port.engine_running?'ENGINE ON':'ENGINE OFF');
  State.engineRunning=!!port.engine_running;
  if(port.action_plan){
    const card=document.getElementById('rag-card');
    if(card){ card.style.display='block';
      const body=document.getElementById('rag-body');
      if(body) body.innerHTML=port.action_plan.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>');
      const ts=document.getElementById('rag-ts'); if(ts) ts.textContent='Last analysis: '+(port.last_analysis?new Date(port.last_analysis).toLocaleTimeString():'—'); }
  }
  // signals
  const sigs=await api('/api/signals');
  buildAlerts('cmd-sigs',(sigs.signals||[]).slice(0,4));
  // agents
  buildCmdAgents();
  // inv chart
  buildInvChart('cmd-inv-chart',[8,7,12,28,45,62,77,8,14,55,23,38]);
  // supplier scorecard
  const sd=await api('/api/suppliers');
  buildSupScore('cmd-sup',(sd.scores||[]).slice(0,4));
}

async function loadSignals(){
  const d=await api('/api/signals');
  const sigs=d.signals||[];
  buildAlerts('all-sigs',sigs,true);
  setEl('sig-crit',sigs.filter(s=>s.severity==='critical').length);
  setEl('sig-badge',sigs.filter(s=>s.severity==='critical').length+' CRITICAL');
  const sd=await api('/api/suppliers');
  buildFullSupTable('full-sup',sd.scores||sd.suppliers||[]);
}

async function loadPositions(){
  const d=await api('/api/inventory');
  setEl('inv-tot',d.total_skus||847);
  setEl('inv-c',d.critical_count||9);
  setEl('inv-l',d.low_count||23);
  setEl('inv-o',d.overstock_count||14);
  setEl('inv-badge',(d.critical_count||9)+' CRITICAL');
  buildInvTable('inv-tbl',d.chart_data||[]);
}

async function loadDemand(){
  const d=await api('/api/demand');
  buildFCChart(d.weekly_demand||[]);
  buildDemandDrivers();
  buildFcstTable('fcst-tbl',d.forecasts||[]);
}

async function loadEngine(){
  const d=await api('/api/engine/status');
  setEl('eng-runs',d.agent_runs_today||0);
  setEl('eng-status',d.running?'RUNNING':'IDLE');
  setEl('eng-last',d.last_analysis?new Date(d.last_analysis).toLocaleTimeString():'—');
  if(!document.getElementById('log-wrap').children.length) buildMockLogs();
  buildAgentHealth();
  buildAgentBars();
}

async function loadSuppliers(){
  const d=await api('/api/suppliers');
  State.allSuppliers=d.suppliers||[];
  renderSupAll(State.allSuppliers);
}

async function loadTrades(){
  const d=await api('/api/trades');
  buildTradesTable('trades-tbl',d.trades||[]);
}

async function loadCosts(){
  const d=await api('/api/costs');
  const opps=d.opportunities||[];
  setEl('cost-total','$'+fmtK(d.total_savings||84000));
  setEl('cost-count',opps.length);
  setEl('cost-badge','$'+fmtK(d.total_savings||84000)+' SAVINGS');
  buildCostList(opps);
}

async function loadNews(){
  const d=await api('/api/news');
  buildNewsList(d.articles||[]);
}

async function loadPerf(){
  const d=await api('/api/performance');
  setEl('perf-runs',d.total_runs||0);
  setEl('perf-time',(d.avg_processing_secs||0).toFixed(1)+'s');
  setEl('perf-sav','$'+fmtK(d.total_savings_found||0));
  setEl('perf-crit',(d.avg_critical_per_run||0).toFixed(1));
  buildPerfTable('perf-tbl',d.run_history||[]);
}

// ═══ BUILDERS ════════════════════════════════════════════════════

function buildAlerts(id, items, showBadge=false){
  const el=document.getElementById(id); if(!el) return;
  if(!items.length){ el.innerHTML='<div style="padding:12px;font-size:11px;font-family:var(--mono);color:var(--mu)">No active signals — run analysis to fetch latest</div>'; return; }
  const sevMap={critical:'alr',warning:'ala',ok:'alg',positive:'alg'};
  const iconMap={critical:'🔴',warning:'🟡',ok:'🟢',positive:'🟢',port_delay:'🚢',financial:'💳',price_spike:'📈',weather:'🌧',geopolitical:'🌐',none:'📰'};
  el.innerHTML='<div class="alerts">'+items.map(s=>{
    const cls=sevMap[s.severity]||'ala';
    const icon=iconMap[s.risk_type]||iconMap[s.severity]||'⚠';
    const badge=showBadge?`<span class="badge ${s.severity==='critical'?'br':'ba'}" style="margin-left:auto;flex-shrink:0">${(s.severity||'').toUpperCase()}</span>`:'';
    return `<div class="alert ${cls}" onclick="toast('${s.supplier_name||'Alert'}','${(s.recommended_action||'').slice(0,60)}')">
      <div class="ai">${icon}</div>
      <div style="flex:1"><div class="at">${s.supplier_name||''}: ${s.description||s.headline||''}</div>
      <div class="ad">${s.recommended_action||s.source||''}</div></div>${badge}</div>`;
  }).join('')+'</div>';
}

function buildCmdAgents(){
  const el=document.getElementById('cmd-agents'); if(!el) return;
  const agents=[
    {n:'Risk Monitor',k:'3 disruptions found',c:'var(--rd)',b:'br',bl:'HOT'},
    {n:'Demand Forecast',k:'Q3 model updated',c:'var(--gr)',b:'bg',bl:'OK'},
    {n:'Inventory Analyst',k:'9 SKUs critical',c:'var(--am)',b:'ba',bl:'WARN'},
    {n:'Supplier Scorer',k:'Weekly KPI done',c:'var(--gr)',b:'bg',bl:'OK'},
    {n:'Cost Optimizer',k:'$84K savings found',c:'var(--pu)',b:'bp',bl:'$84K'},
  ];
  el.innerHTML='<div class="agrid">'+agents.map((a,i)=>`
    <div class="apill" ${i===4?'style="grid-column:span 2"':''} onclick="goto('engine')">
      <div class="adot" style="background:${a.c}"></div>
      <div style="flex:1;min-width:0"><div class="an">${a.n}</div><div class="ak">${a.k}</div></div>
      <span class="badge ${a.b}">${a.bl}</span></div>`).join('')+'</div>';
}

function buildInvChart(id, vals){
  const el=document.getElementById(id); if(!el) return;
  el.innerHTML='';
  vals.forEach(v=>{
    const b=document.createElement('div'); b.className='bcbar';
    b.style.height=(v*.95)+'%';
    b.style.background=v<15?'var(--rd)':v<35?'var(--am)':'var(--gr)';
    b.style.opacity='.82';
    b.onclick=()=>goto('positions');
    el.appendChild(b);
  });
}

function buildSupScore(id, scores){
  const el=document.getElementById(id); if(!el) return;
  const fallback=[
    {supplier_name:'AsiaTech Co.',overall_score:94,recommended_action:'renew'},
    {supplier_name:'EuroMaterials',overall_score:81,recommended_action:'monitor'},
    {supplier_name:'VendorX Ltd.',overall_score:58,recommended_action:'qualify_backup'},
    {supplier_name:'PacificSource',overall_score:41,recommended_action:'replace'},
  ];
  const data=scores.length?scores:fallback;
  const badgeMap={renew:'bg',monitor:'bb',qualify_backup:'ba',replace:'br'};
  el.innerHTML=data.slice(0,5).map(s=>{
    const sc=s.overall_score||s.computed_score||0;
    const col=sc>=80?'var(--gr)':sc>=60?'var(--bl)':sc>=50?'var(--am)':'var(--rd)';
    const bl=badgeMap[s.recommended_action]||'bm';
    return `<tr onclick="toast('${s.supplier_name}','Score: ${sc} · Action: ${s.recommended_action||''}')">
      <td><div class="tn">${s.supplier_name}</div><div class="ts">${s.category||''}</div></td>
      <td style="font-family:var(--mono);color:${col}">${sc}</td>
      <td><div class="sbar"><div class="sfill" style="width:${sc}%;background:${col}"></div></div></td>
      <td><span class="badge ${bl}">${(s.recommended_action||'').toUpperCase()}</span></td></tr>`;
  }).join('');
}

function buildFullSupTable(id, scores){
  const el=document.getElementById(id); if(!el) return;
  const badgeMap={renew:'bg',monitor:'bb',qualify_backup:'ba',replace:'br'};
  el.innerHTML=scores.slice(0,10).map(s=>{
    const sc=s.overall_score||0;
    const col=sc>=80?'var(--gr)':sc>=60?'var(--bl)':sc>=50?'var(--am)':'var(--rd)';
    const bl=badgeMap[s.recommended_action]||'bm';
    return `<tr onclick="toast('${s.supplier_name}','Score: ${sc}')">
      <td><div class="tn">${s.supplier_name}</div></td>
      <td class="ts">${s.category||''}</td>
      <td style="font-family:var(--mono);color:${col}">${sc}</td>
      <td style="font-family:var(--mono)">${s.on_time_rate||'—'}%</td>
      <td style="font-family:var(--mono)">${s.quality_rate||'—'}%</td>
      <td style="font-family:var(--mono)">${s.financial_rating||'—'}</td>
      <td><span class="badge ${s.trend==='improving'?'bg':s.trend==='declining'?'br':'bb'}">${s.trend||'stable'}</span></td>
      <td><span class="badge ${bl}">${(s.recommended_action||'').toUpperCase()}</span></td></tr>`;
  }).join('');
}

function buildInvTable(id, items){
  const el=document.getElementById(id); if(!el) return;
  const fallback=[
    {sku_id:'SKU-009',product_name:'USB-C Hub 7-port',stock_pct:8,days_remaining:5},
    {sku_id:'SKU-015',product_name:'Mechanical Keyboard TKL',stock_pct:7,days_remaining:7},
    {sku_id:'SKU-021',product_name:'Monitor Stand Adj.',stock_pct:12,days_remaining:9},
    {sku_id:'SKU-030',product_name:'Laptop Stand Pro',stock_pct:28,days_remaining:18},
    {sku_id:'SKU-045',product_name:'Webcam 4K Ultra',stock_pct:14,days_remaining:11},
  ];
  const data=items.length?items:fallback;
  el.innerHTML=data.map(s=>{
    const col=s.stock_pct<15?'var(--rd)':s.stock_pct<35?'var(--am)':'var(--gr)';
    const days=s.days_remaining||0;
    const badge=s.stock_pct<15?'<span class="badge br">CRITICAL</span>':s.stock_pct<35?'<span class="badge ba">LOW</span>':'<span class="badge bg">OK</span>';
    return `<tr onclick="toast('${s.sku_id}','${s.product_name} — ${days} days remaining')">
      <td class="ts">${s.sku_id}</td>
      <td>${s.product_name}</td>
      <td style="font-family:var(--mono);color:${col}">${s.stock_pct}%</td>
      <td><div class="sbar"><div class="sfill" style="width:${s.stock_pct}%;background:${col}"></div></div></td>
      <td style="font-family:var(--mono);color:${days<10?'var(--rd)':days<20?'var(--am)':'var(--tx)'}">${days}d</td>
      <td>${badge}</td></tr>`;
  }).join('');
}

function buildFCChart(weekly){
  const chart=document.getElementById('fc-chart');
  const lbls=document.getElementById('fc-labels');
  if(!chart) return;
  chart.innerHTML=''; if(lbls) lbls.innerHTML='';
  const max=1400;
  FC_WEEKS.forEach((w,i)=>{
    const col=document.createElement('div'); col.className='fcol';
    const b=document.createElement('div'); b.className='fbar';
    if(FC_ACT[i]!=null){ b.style.height=(FC_ACT[i]/max*100)+'%'; b.style.background='var(--gr)'; b.style.opacity='.85'; }
    else{ b.classList.add('proj'); b.style.height=(FC_PRJ[i]/max*100)+'%'; }
    col.appendChild(b); chart.appendChild(col);
    if(lbls){ const l=document.createElement('span'); l.textContent=w; lbls.appendChild(l); }
  });
}

function buildDemandDrivers(){
  const el=document.getElementById('demand-drv'); if(!el) return;
  const drivers=[
    {cls:'alg',icon:'📈',t:'Back-to-school season (Aug)',d:'Electronics +28% projected'},
    {cls:'ala',icon:'⚡',t:'Competitor stockout spill-over',d:'Estimated +12% demand lift'},
    {cls:'alg',icon:'🎯',t:'Marketing campaign Jul 15',d:'Expected +15% lift for 3 weeks'},
    {cls:'alr',icon:'⚠',t:'Shanghai delay risk',d:'May cause −8% supply miss'},
  ];
  el.innerHTML='<div class="alerts">'+drivers.map(d=>`
    <div class="alert ${d.cls}" style="cursor:default">
      <div class="ai">${d.icon}</div>
      <div><div class="at">${d.t}</div><div class="ad">${d.d}</div></div></div>`).join('')+'</div>';
}

function buildFcstTable(id, forecasts){
  const el=document.getElementById(id); if(!el) return;
  const fallback=[
    {sku_id:'SKU-001',product_name:'Wireless Headset Pro',forecasted_demand_q3:4200,pct_change_vs_q2:34},
    {sku_id:'SKU-009',product_name:'USB-C Hub 7-port',forecasted_demand_q3:3800,pct_change_vs_q2:28},
    {sku_id:'SKU-015',product_name:'Mechanical Keyboard TKL',forecasted_demand_q3:2900,pct_change_vs_q2:19},
    {sku_id:'SKU-021',product_name:'Monitor Stand Adj.',forecasted_demand_q3:1600,pct_change_vs_q2:4},
  ];
  const data=forecasts.length?forecasts:fallback;
  el.innerHTML=data.map(f=>{
    const pct=f.pct_change_vs_q2||0;
    const col=pct>20?'var(--rd)':pct>5?'var(--am)':'var(--mu)';
    return `<tr onclick="toast('${f.sku_id}','Q3 forecast: ${(f.forecasted_demand_q3||0).toLocaleString()} units')">
      <td class="ts">${f.sku_id}</td><td>${f.product_name}</td>
      <td style="font-family:var(--mono)">${(f.forecasted_demand_q3||0).toLocaleString()}u</td>
      <td style="font-family:var(--mono);color:${col}">${pct>0?'+':''}${pct}%</td></tr>`;
  }).join('');
}

function buildMockLogs(){
  const el=document.getElementById('log-wrap'); if(!el) return;
  const now=new Date();
  MOCK_LOGS.forEach((l,i)=>{
    const row=document.createElement('div'); row.className='logr';
    const t=new Date(now-i*45000).toTimeString().slice(0,8);
    row.innerHTML=`<span class="lt">${t}</span><span class="la2" style="${l.c}">${l.a}</span><span class="lm">${l.m}</span>`;
    el.appendChild(row);
  });
}

function addMockLog(){
  const el=document.getElementById('log-wrap'); if(!el) return;
  const entries=[
    {a:'Orchestrator',m:'Manual trigger — dispatching all agents',c:'color:var(--gr)'},
    {a:'Risk Monitor',m:'Scanning 14 news + shipping sources…',c:'color:var(--am)'},
    {a:'Inv Analyst',m:'Warehouse DB queried — 847 SKUs checked',c:'color:var(--gr)'},
    {a:'Cost Optimizer',m:'PriceAPI returned 3 cheaper alternatives',c:'color:var(--pu)'},
  ];
  const e=entries[State.logCount%entries.length]; State.logCount++;
  const row=document.createElement('div'); row.className='logr';
  row.innerHTML=`<span class="lt">${new Date().toTimeString().slice(0,8)}</span><span class="la2" style="${e.c}">${e.a}</span><span class="lm">${e.m}</span>`;
  el.insertBefore(row,el.firstChild);
  const rc=document.getElementById('eng-runs');
  if(rc) rc.textContent=parseInt(rc.textContent||'0')+1;
}

function buildAgentHealth(){
  const el=document.getElementById('agent-health'); if(!el) return;
  const agents=[
    {n:'Risk Monitor',k:'last: 4m ago',c:'var(--rd)',s:'UP'},
    {n:'Demand Forecast',k:'last: 12m ago',c:'var(--gr)',s:'UP'},
    {n:'Inv Analyst',k:'last: 2m ago',c:'var(--am)',s:'UP'},
    {n:'Sup Scorer',k:'last: 1h ago',c:'var(--gr)',s:'UP'},
    {n:'Cost Optimizer',k:'last: 30m ago',c:'var(--pu)',s:'UP'},
  ];
  el.innerHTML='<div class="agrid">'+agents.map((a,i)=>`
    <div class="apill" ${i===4?'style="grid-column:span 2"':''} onclick="toast('${a.n}','Status: ${a.s} · ${a.k}')">
      <div class="adot" style="background:${a.c}"></div>
      <div style="flex:1;min-width:0"><div class="an">${a.n}</div><div class="ak">${a.k}</div></div>
      <span class="badge bg">${a.s}</span></div>`).join('')+'</div>';
}

function buildAgentBars(){
  const el=document.getElementById('agent-bars'); if(!el) return;
  const data=[{n:'Risk Monitor',v:18,c:'var(--rd)'},{n:'Dem Forecast',v:6,c:'var(--bl)'},
              {n:'Inv Analyst',v:12,c:'var(--am)'},{n:'Sup Scorer',v:4,c:'var(--gr)'},{n:'Cost Optim',v:7,c:'var(--pu)'}];
  el.innerHTML=data.map(r=>`
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
      <span style="font-size:9px;font-family:var(--mono);width:80px;color:var(--mu);text-align:right;flex-shrink:0">${r.n}</span>
      <div style="flex:1;height:16px;background:var(--s3);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${r.v/20*100}%;background:${r.c};opacity:.85;display:flex;align-items:center;padding:0 6px">
          <span style="font-size:9px;font-family:var(--mono);color:#000;font-weight:700">${r.v}</span></div></div></div>`).join('');
}

function renderSupAll(sups){
  const el=document.getElementById('sup-all'); if(!el) return;
  el.innerHTML=sups.map(s=>{
    const sc=s.overall_score||0;
    const col=sc>=80?'var(--gr)':sc>=60?'var(--bl)':sc>=50?'var(--am)':'var(--rd)';
    return `<tr onclick="toast('${s.supplier_name}','Score: ${sc} · Country: ${s.country||'?'}')">
      <td class="ts">${s.supplier_id}</td>
      <td><div class="tn">${s.supplier_name}</div></td>
      <td class="ts">${s.category||''}</td>
      <td style="font-family:var(--mono);color:${col}">${sc}</td>
      <td style="font-family:var(--mono)">${s.on_time_rate||'—'}%</td>
      <td style="font-family:var(--mono)">${s.quality_rate||'—'}%</td>
      <td><span class="badge ${sc>=70?'bg':sc>=55?'ba':'br'}">${s.financial_rating||'—'}</span></td>
      <td class="ts">${s.country||'—'}</td></tr>`;
  }).join('');
}

function filterSup(){
  const q=(document.getElementById('sup-search')?.value||'').toLowerCase();
  const filtered=State.allSuppliers.filter(s=>
    (s.supplier_name||'').toLowerCase().includes(q)||
    (s.category||'').toLowerCase().includes(q)||
    (s.country||'').toLowerCase().includes(q));
  renderSupAll(filtered);
}

function buildTradesTable(id, runs){
  const el=document.getElementById(id); if(!el) return;
  if(!runs.length){ el.innerHTML='<tr><td colspan="7" style="padding:16px;font-size:11px;font-family:var(--mono);color:var(--mu)">No runs yet — click Run Analysis</td></tr>'; return; }
  el.innerHTML=runs.map(r=>`<tr onclick="toast('Run ${r.session_id||'?'}','${(r.action_plan||'').slice(0,60)}…')">
    <td class="ts">${r.created_at?new Date(r.created_at).toLocaleString():'—'}</td>
    <td style="font-size:11px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(r.query||'').slice(0,40)}</td>
    <td style="font-family:var(--mono);color:var(--rd)">${r.risks_found||0}</td>
    <td style="font-family:var(--mono);color:var(--am)">${r.alerts_found||0}</td>
    <td style="font-family:var(--mono);color:var(--gr)">$${fmtK(r.savings_found||0)}</td>
    <td style="font-family:var(--mono);color:var(--rd)">${r.critical_count||0}</td>
    <td style="font-family:var(--mono)">${(r.processing_time_secs||0).toFixed(1)}s</td></tr>`).join('');
}

function buildCostList(opps){
  const el=document.getElementById('cost-list'); if(!el) return;
  const icons={supplier_swap:'📦',bulk_order:'🛒',freight_consolidation:'🚢',commodity_hedge:'📈'};
  const bgs  ={supplier_swap:'rgba(0,232,150,.1)',bulk_order:'rgba(245,158,11,.1)',freight_consolidation:'rgba(59,130,246,.1)',commodity_hedge:'rgba(129,140,248,.1)'};
  el.innerHTML=opps.map(o=>`
    <div class="crow" onclick="toast('Action initiated','${(o.action_required||'').slice(0,60)}')">
      <div class="cico" style="background:${bgs[o.opportunity_type]||'rgba(255,255,255,.05)'}">${icons[o.opportunity_type]||'💡'}</div>
      <div style="flex:1;min-width:0">
        <div class="cn">${o.description||o.opportunity_type||''}</div>
        <div class="cd">${o.opportunity_type||''} · deadline: ${o.deadline||'—'}</div>
        <div class="csb"><div class="csi" style="width:${Math.min(o.saving_pct||30,100)}%"></div></div></div>
      <div style="text-align:right;flex-shrink:0;margin-left:12px">
        <div class="csv">$${fmtK(o.saving_amount||0)}</div>
        <button class="bp" style="margin-top:6px;font-size:9px;padding:4px 10px"
          onclick="event.stopPropagation();toast('Action started','Processing ${o.opportunity_type||'opportunity'}')">ACT</button></div></div>`).join('');
}

function buildNewsList(articles){
  const el=document.getElementById('news-list'); if(!el) return;
  const sevMap={critical:'br',warning:'ba',ok:'bg',positive:'bg'};
  el.innerHTML=articles.map(a=>`
    <div class="nrow">
      <div class="nh">${a.headline||''}</div>
      <div class="nmeta">
        <span>${a.source||'Unknown'}</span>
        <span class="badge ${sevMap[a.severity]||'bm'}">${(a.severity||'ok').toUpperCase()}</span>
        ${a.risk_type&&a.risk_type!=='none'?`<span class="badge bb">${a.risk_type}</span>`:''}
        <span>${a.recommended_action||''}</span></div></div>`).join('');
  if(!articles.length) el.innerHTML='<div style="padding:20px;font-size:11px;font-family:var(--mono);color:var(--mu)">No news yet — run analysis to fetch headlines</div>';
}

function buildPerfTable(id, runs){
  const el=document.getElementById(id); if(!el) return;
  if(!runs.length){ el.innerHTML='<tr><td colspan="4" style="padding:16px;font-size:11px;font-family:var(--mono);color:var(--mu)">No runs recorded yet</td></tr>'; return; }
  el.innerHTML=runs.map(r=>`<tr>
    <td class="ts">${r.created_at?new Date(r.created_at).toLocaleString():'—'}</td>
    <td style="font-family:var(--mono);color:var(--gr)">$${fmtK(r.savings_found||0)}</td>
    <td style="font-family:var(--mono);color:var(--rd)">${r.critical_count||0}</td>
    <td style="font-family:var(--mono)">${(r.processing_time_secs||0).toFixed(1)}s</td></tr>`).join('');
}

// ═══ INIT ════════════════════════════════════════════════════════
window.addEventListener('DOMContentLoaded',()=>{
  loadCommand();
  buildFCChart([]);
  // Poll portfolio stats every 30s
  setInterval(async()=>{
    const d=await api('/api/portfolio');
    setEl('m-crit',d.critical_alerts||0);
    setEl('m-sav','$'+fmtK(d.savings_found||0));
    setEl('nc-sig',d.critical_alerts||0);
    setEl('engine-badge',d.engine_running?'ENGINE ON':'ENGINE OFF');
    State.engineRunning=!!d.engine_running;
    if(State.page==='engine') setEl('eng-runs',d.agent_runs_today||0);
  },30000);
  // Auto-simulate log entries if on engine page
  setInterval(()=>{ if(State.page==='engine') addMockLog(); },9000);
});
