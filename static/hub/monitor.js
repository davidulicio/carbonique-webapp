export function createMonitor(ctx) {
  const {S,esc,button,empty,header,time,api,render,toast,store}=ctx;
  const M={towers:[],selected:null,busy:false,error:"",updated:null,detail:null,staleAfter:300,minInterval:30};
  const names={healthy:"No issues detected",warning:"Needs attention",fault:"Fault detected",stale:"Measurements are stale",unreachable:"Connection unavailable",not_configured:"Not configured",configuration_error:"Configuration needs attention",invalid_response:"Response not understood",not_checked:"Not checked",no_data:"No measurements"};
  const badge=t=>`<span class="monitor-badge ${esc(t.status)}">${esc(names[t.status]||t.status)}</span>`;
  const fresh=t=>!t.stale&&t.observed_at&&Date.now()-new Date(t.observed_at).getTime()<M.staleAfter*1000;
  const metric=(data,tag)=>data?.metrics?.find(m=>m.tag===tag);
  function value(m){return m?`${Number(m.value).toLocaleString("en-CA",{maximumFractionDigits:3})} <small>${esc(m.unit)}</small>`:"<span class=\"muted\">Not reported</span>";}
  async function load(refresh=false,site=null) {
    if(M.busy)return;
    M.busy=true;M.error="";if(S.view==="monitor")render();
    try{
      if(!navigator.onLine){const cached=await store.get("meta",`${S.me.id}:monitor`);if(cached)M.towers=cached.towers;throw new Error("Offline: showing the last saved checks. Measurements are not live.");}
      const response=await api(`/api/monitor/?${site?`site=${site}&`:""}${refresh?"refresh=1":""}`);
      if(site){M.detail=response.towers[0];const index=M.towers.findIndex(t=>t.site===Number(site));if(index>=0)M.towers[index]=M.detail;else M.towers.push(M.detail);}
      else {M.towers=response.towers;await store.put("meta",`${S.me.id}:monitor`,response);}
      M.updated=response.server_time;M.staleAfter=response.stale_after_seconds;M.minInterval=response.min_interval_seconds;
    }catch(e){M.error=e.message;}
    finally{M.busy=false;if(S.view==="monitor")render();}
  }
  function tile(t) {
    const data=t.data||{},preferred=["CO2MF","CO2D","MeasFlowRate","AvgSS"].filter(tag=>metric(data,tag)).slice(0,3);
    return `<button type="button" class="panel tower-card" data-action="monitor-detail" data-id="${t.site}"><span class="eyebrow">${esc(t.code)}</span><h2>${esc(t.name)}</h2>${badge(t)}<p class="small muted">Checked ${t.checked_at?time(t.checked_at):"never"}</p>${t.issues?.[0]?`<p class="monitor-headline">${esc(t.issues[0].title)}</p>`:""}${data.metrics?.length?`<div class="monitor-mini-values">${preferred.map(tag=>`<div><span>${esc(metric(data,tag).label)}</span><strong>${value(metric(data,tag))}</strong></div>`).join("")}</div><p class="small ${fresh(t)?"muted":"monitor-stale"}">${fresh(t)?"Measurement snapshot":"Earlier / last known snapshot"} · ${time(t.observed_at)}</p>`:""}<span class="small">View tower details →</span></button>`;
  }
  function trend(history,tag) {
    const points=history.filter(h=>Number.isFinite(h.metrics?.[tag]));
    if(points.length<2)return "";
    const samples=points.map(p=>p.metrics[tag]),min=Math.min(...samples),range=Math.max(...samples)-min||1;
    return `<svg viewBox="0 0 480 100" role="img" aria-label="${esc(tag)} trend over ${points.length} recent checks"><polyline fill="none" stroke="#1c7fa3" stroke-width="2.5" points="${samples.map((v,i)=>`${10+i/(samples.length-1)*460},${90-(v-min)/range*80}`).join(" ")}"/></svg><p class="small muted">${time(points[0].at)} → ${time(points.at(-1).at)} · ${samples.length} checks</p>`;
  }
  function details(t) {
    const data=t.data||{},metrics=data.metrics||[],groups=[...new Set(metrics.map(m=>m.group))],history=t.history||[];
    return header(esc(t.code)+" · Tower status",esc(t.name),button("All towers","monitor-network")+button(M.busy?"Checking…":"Check this tower","monitor-refresh",t.site,"primary"))+`<div class="panel"><div class="panel-title">${badge(t)}<span class="pill">Read only</span></div><p class="small">Last check: ${t.checked_at?time(t.checked_at):"never"} · Last measurement: ${t.observed_at?time(t.observed_at):"not received"}</p>${!fresh(t)&&metrics.length?'<div class="notice">These are earlier measurements. A failed or stale check does not show a healthy live state.</div>':""}<p class="small muted">${esc(data.model||"Instrument identity not reported")}${data.serial?` · ${esc(data.serial)}`:""}${data.firmware?` · Firmware ${esc(data.firmware)}`:""}</p></div><div class="monitor-detail-grid"><section><div class="panel"><h2>Checks</h2>${(t.issues||[]).map(i=>`<div class="monitor-issue ${esc(i.severity)}"><strong>${esc(i.title)}</strong><p>${esc(i.detail)}</p></div>`).join("")||empty("No issues detected in this snapshot","These checks use EC-Monitor thresholds and do not replace instrument maintenance.")}</div>${data.flags?.length?`<div class="panel"><h2>Instrument diagnostics</h2>${data.flags.map(f=>`<div class="metadata-row"><span>${esc(f.label)}</span><span>${f.ok===true?"OK":f.ok===false?"Fault":"Not reported"}</span></div>`).join("")}${data.diagnostic_word!==null&&data.diagnostic_word!==undefined?`<p class="small muted">Diagnostic word: ${data.diagnostic_word} · ${data.diagnostic_word.toString(2).padStart(13,"0")}</p>`:""}</div>`:""}</section><section>${groups.map(g=>`<div class="panel"><h2>${esc(g)}</h2><div class="monitor-metrics">${metrics.filter(m=>m.group===g).map(m=>`<div><span class="small muted">${esc(m.label)}</span><strong>${value(m)}</strong></div>`).join("")}</div></div>`).join("")}${data.usb?`<div class="panel"><h2>Logging & SmartFlux</h2><div class="metadata-row"><span>Logging drive</span><span>${({0:"Absent",1:"Logging",2:"Idle",3:"Error"})[data.usb.State]||"Not reported"}</span></div><div class="metadata-row"><span>Drive free space</span><span>${data.usb.Free??"Not reported"} MB</span></div><div class="metadata-row"><span>SmartFlux</span><span>${esc(data.smartflux?.model||"Not reported")}</span></div><div class="metadata-row"><span>Processing status</span><span>${esc(data.smartflux?.run_status||"Not reported")}</span></div><div class="metadata-row"><span>Latest reported flux file</span><span>${esc(data.smartflux?.last_file||"Not reported")}</span></div>${data.smartflux?.file_age_minutes!=null?`<p class="small muted">File age at check: ${data.smartflux.file_age_minutes} minutes</p>`:""}</div>`:""}</section></div>${history.length>1?`<div class="panel"><h2>Recent measurement snapshots</h2><p class="small muted">Up to 24 hours. These are diagnostic snapshots, not a continuous scientific data product.</p>${["CO2MF","MeasFlowRate","AvgSS"].filter(tag=>history.some(h=>h.metrics[tag]!==undefined)).map(tag=>`<h3>${esc(metric(data,tag)?.label||tag)}</h3>${trend(history,tag)}`).join("")}</div>`:""}${data.calibrations?`<details class="panel"><summary>Reported calibration dates</summary>${Object.entries(data.calibrations).map(([k,v])=>`<div class="metadata-row"><span>${esc(k)}</span><span>${esc(v||"Not reported")}</span></div>`).join("")}</details>`:""}`;
  }
  function view() {
    const towers=M.towers.map(t=>({...t,stale:!navigator.onLine||t.stale||!fresh(t)}));
    const selected=M.selected&&(M.detail?.site===M.selected?M.detail:towers.find(t=>t.site===M.selected));
    const notice=`<div class="notice">Visualization only. The Hub sends a fixed set of read-only status queries; calibration, logging and instrument settings cannot be changed here.</div>${M.error?`<div class="error" role="status">${esc(M.error)}</div>`:""}`;
    if(selected)return notice+details({...selected,stale:!navigator.onLine||selected.stale||!fresh(selected)});
    return header("Tower status","Check the network, then open a tower for measurements and diagnostics.",button(M.busy?"Checking towers…":"Check all towers","monitor-refresh","","primary"))+notice+`<div class="stats">${[["Towers",towers.length],["No issues detected",towers.filter(t=>t.status==="healthy"&&fresh(t)).length],["Need attention",towers.filter(t=>["warning","fault","unreachable"].includes(t.status)).length],["Not configured",towers.filter(t=>t.status==="not_configured").length]].map(([label,count])=>`<div class="stat"><span class="label">${label}</span><strong>${count}</strong></div>`).join("")}</div><div class="site-grid">${towers.map(tile).join("")||empty(M.busy?"Checking the tower network…":"No checks loaded yet","Use Check all towers to request the current status.")}</div><p class="small muted">${M.updated?`Status retrieved ${time(M.updated)}. `:""}Checks are limited to one per tower every ${M.minInterval} seconds. Tower connections are configured privately on the VM.</p>`;
  }
  async function action(action,id) {
    if(!action.startsWith("monitor-"))return false;
    if(action==="monitor-detail"){M.selected=Number(id);M.detail=null;await load(false,M.selected);}
    if(action==="monitor-site"){M.selected=S.siteId;M.detail=null;S.view="monitor";location.hash="monitor";await load(true,S.siteId);}
    if(action==="monitor-network"){M.selected=null;M.detail=null;render();await load(false);}
    if(action==="monitor-refresh")await load(true,id?Number(id):null);
    return true;
  }
  return {view,load,action,network:()=>{M.selected=null;M.detail=null;},auto:async()=>{if(!M.busy&&(!M.updated||Date.now()-new Date(M.updated).getTime()>60000))await load(true,M.selected);}};
}
