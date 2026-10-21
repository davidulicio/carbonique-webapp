import * as store from "./storage.js";
import { createResources } from "./resources.js";
import { createMonitor } from "./monitor.js";
import { createProcessingFiles } from "./processing-files.js";
import { createRecordResources } from "./record-resources.js";

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const uuid = () => crypto.randomUUID();
const clone = value => JSON.parse(JSON.stringify(value));
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; };
const day = value => value ? new Date(`${value.slice(0,10)}T12:00:00`).toLocaleDateString("en-CA", {month:"short",day:"numeric",year:"numeric"}) : "Not recorded";
const time = value => value ? new Date(value).toLocaleString("en-CA", {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}) : "Not recorded";
const pill = value => `<span class="pill ${esc(value)}">${esc(value.replaceAll("_"," "))}</span>`;
const button = (label, action, id="", cls="secondary small") => `<button type="button" class="button ${cls}" data-action="${action}" data-id="${esc(id)}">${label}</button>`;
const empty = (title, text="") => `<div class="empty"><strong>${esc(title)}</strong>${esc(text)}</div>`;
const rich = text => {
  const tpl = document.createElement("template"); tpl.innerHTML = text || "";
  const allowed = new Set(["P","BR","STRONG","B","EM","I","UL","OL","LI","A","CODE","PRE","BLOCKQUOTE","H3","H4","TABLE","THEAD","TBODY","TR","TH","TD"]);
  for (const node of [...tpl.content.querySelectorAll("*")].reverse()) {
    if (!allowed.has(node.tagName)) { node.replaceWith(...node.childNodes); continue; }
    for (const attr of [...node.attributes]) if (!(node.tagName === "A" && ["href","title"].includes(attr.name))) node.removeAttribute(attr.name);
    if (node.tagName === "A") { const href=node.getAttribute("href") || ""; if (!/^(https?:|mailto:)/i.test(href)) node.removeAttribute("href"); node.setAttribute("rel","noopener noreferrer"); }
  }
  return tpl.innerHTML;
};
// Apply the preferred punctuation to displayed prose; keep file bytes and saved text intact.
function normalizeProse(root){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode;
    if(node.parentElement?.closest("script,style,code,pre,textarea"))continue;
    if(node.nodeValue.includes("\u2014"))node.nodeValue=node.nodeValue.replace(/\s*\u2014\s*/g," - ");
  }
  for(const element of root.querySelectorAll("[title],[aria-label]"))for(const key of ["title","aria-label"]){
    const value=element.getAttribute(key);if(value?.includes("\u2014"))element.setAttribute(key,value.replace(/\s*\u2014\s*/g," - "));
  }
}

const S = {protocols:[], me:null, sites:[], checklists:[], siteId:null, base:null, data:null, queue:[], view:location.hash.slice(1)||"overview", histMode:"visits", siteTab:"reference", mode:"offsite", filter:"", typeFilter:"all", visitId:null, online:navigator.onLine, syncing:false, blocked:null, csrf:$("meta[name=csrf-token]")?.content, overview:[], team:[], objectURLs:[], dialogURLs:[], prepared:false};
const write = () => ["member","researcher","manager","admin"].includes(S.me?.role);
const research = () => ["researcher","manager","admin"].includes(S.me?.role);
const admin = () => S.me?.role === "admin";
const currentSite = () => S.sites.find(s => s.id === S.siteId);
const selectedVisit = () => S.data?.visits.find(v => v.id === S.visitId && v.status === "open") || S.data?.visits.find(v => v.status === "open") || null;
let toastTimer;
function toast(text, error=false) { const el=$("#toast"); el.textContent=text; el.className=error?"error":""; el.style.display="block"; clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.style.display="none",5500); }
function errorMessage(value) { return typeof value === "string" ? value : JSON.stringify(value); }
async function api(path, {method="GET", data, form}={}) {
  const headers = {};
  if (method !== "GET") headers["X-CSRFToken"] = S.csrf;
  if (data !== undefined) headers["Content-Type"] = "application/json";
  let response;
  try { response = await fetch(path, {method, headers, credentials:"same-origin", cache:"no-store", body:form || (data!==undefined ? JSON.stringify(data) : undefined)}); }
  catch { S.online=false; updateConnection(); throw new Error("No connection. Your queued field records remain on this device."); }
  S.online=true; updateConnection();
  const body = await response.json().catch(()=>({detail:response.status===429?"Too many requests. Wait a moment and retry; queued records remain on this device.":"Unexpected server response."}));
  if (!response.ok) { const e=new Error(errorMessage(body)); e.status=response.status; e.body=body; throw e; }
  return body;
}
async function refreshCsrf() {
  const data = await api("/api/csrf/");
  S.csrf=data.csrfToken;
  if (!data.authenticated) { const error=new Error("Sign in again to upload the queued records. They remain saved on this device."); error.status=403; throw error; }
}
function updateConnection() {
  $("#connection-dot").className="dot" + (S.blocked?" error":S.online?"":" offline");
  $("#connection-label").textContent=S.blocked?"Sync needs review":S.syncing?"Synchronizing…":S.online?"Connected":"Working offline";
  $("#queue-count").textContent=S.queue.length;
  $("#queue-status").textContent=S.queue.length?" pending":"";
}
async function readQueue() { S.queue=(await store.all("outbox")).filter(q=>q.account===S.me.id).sort((a,b)=>a.order-b.order); S.blocked=S.queue.find(q=>q.error)||null; updateConnection(); }
function project() {
  if (!S.base) return;
  S.data=clone(S.base);
  S.data.calibrations ||= []; S.data.knowledge ||= [];
  for (const item of S.queue.filter(q=>q.siteId===S.siteId||(q.kind==="upload"&&q.fields.equipment&&S.data.equipment.some(e=>e.id===Number(q.fields.equipment))))) {
    if (item.kind === "upload") { S.data.attachments.push({id:item.id,visit:item.fields.visit||null,equipment:item.fields.equipment||null,caveat:item.fields.caveat||null,configuration:item.fields.configuration||null,task:item.fields.task||null,activity:item.fields.activity||null,observation:item.fields.observation||null,calibration:item.fields.calibration||null,filename:item.file.name,caption:item.fields.caption,content_type:item.file.type,url:"",pending:true}); continue; }
    const op=item.operation,p=op.payload,t=S.data.tasks.find(t=>t.id===op.entity_id),v=S.data.visits.find(v=>v.id===op.entity_id);
    const visitId=p.visit_id||null;
    if (op.kind === "visit.create") S.data.visits.unshift({id:op.entity_id,site:S.siteId,date:p.date,crew:p.crew,title:p.title,classification:p.classification||"routine",status:"open",started_at:op.occurred_at,version:1,reports:[],narrative:"",pending:true});
    else if (op.kind.startsWith("visit.") && v) { if (op.kind==="visit.close") {v.status="closed";v.ended_at=op.occurred_at;} else if(op.kind==="visit.reopen")v.status="open"; else if(op.kind==="visit.edit")Object.assign(v,p); v.version++;v.pending=true; }
    else if(op.kind==="observation.create") S.data.observations.push({id:op.entity_id,visit:visitId,text:p.text,author_name:S.me.name,occurred_at:op.occurred_at,pending:true});
    else if(op.kind==="task.create") { const newTask={id:op.entity_id,site:S.siteId,title:p.title,details:p.details||"",priority:p.priority||"normal",status:"pending",due_date:p.due_date||null,created_visit:visitId,created_by:S.me.id,created_at:op.occurred_at,version:1,pending:true};S.data.tasks.push(newTask);S.data.activities.push({id:p.activity_id||op.id,task:op.entity_id,visit:visitId,action:"created",task_title:p.title,text:p.text||"",author_name:S.me.name,occurred_at:op.occurred_at,pending:true}); }
    else if(op.kind.startsWith("task.") && t) { const action={"task.complete":"completed","task.reopen":"reopened","task.comment":"commented","task.edit":"edited","task.archive":"archived"}[op.kind];if(op.kind==="task.complete")t.status="done";if(op.kind==="task.reopen")t.status="pending";if(op.kind==="task.archive")t.status="archived";if(op.kind==="task.edit")Object.assign(t,p);if(op.kind!=="task.comment")t.version++;t.pending=true;S.data.activities.push({id:p.activity_id||op.id,task:t.id,visit:visitId,action,task_title:t.title,text:p.text||"",author_name:S.me.name,occurred_at:op.occurred_at,pending:true}); }
    else if(op.kind==="calibration.create")S.data.calibrations.unshift({...p,id:op.entity_id,site:S.siteId,version:1,is_archived:false,pending:true});
    else if(op.kind==="calibration.edit"){const record=S.data.calibrations.find(r=>r.id===op.entity_id);if(record){Object.assign(record,p);record.version++;record.pending=true;}}
    else if(op.kind==="caveat.draft")S.data.caveats.push({id:op.entity_id,sites:[S.siteId],title:p.title,description:p.description,variables:p.variables,period_label:p.period_label,status:"draft",treatment:"",version:1,pending:true});
  }
}
let queueOrder=Date.now();
async function enqueue(kind, entityId, payload={}, version, files=[]) {
  if (!write() || currentSite()?.is_archived) throw new Error("This site is read-only.");
  for(const file of files)if(file.size>25*1024*1024)throw new Error("Maximum file size is 25 MB per file.");
  payload={...payload};
  if(kind.startsWith("task."))payload.activity_id=payload.activity_id||uuid();
  const operation={id:uuid(),kind,entity_id:entityId,site_id:S.siteId,payload,occurred_at:new Date().toISOString()};
  if(version!==undefined)operation.base_version=version;
  const order=()=>queueOrder=Math.max(queueOrder+1,Date.now());
  const item={id:operation.id,kind:"operation",account:S.me.id,siteId:S.siteId,operation,order:order()};
  const links=kind.startsWith("task.")?{task:entityId,activity:payload.activity_id,visit:payload.visit_id||null}:kind==="observation.create"?{observation:entityId,visit:payload.visit_id}:kind.startsWith("visit.")?{visit:entityId}:kind==="caveat.draft"?{caveat:entityId}:kind.startsWith("calibration.")?{calibration:entityId}:{};
  const uploads=files.map(file=>({id:uuid(),kind:"upload",account:S.me.id,siteId:S.siteId,file,fields:{...links,caption:file.name},order:order()}));
  await store.putMany("outbox",[item,...uploads].map(entry=>[entry.id,entry]));
  await readQueue();project();render();
  toast(S.online?"Saved on this device; synchronizing…":"Saved on this device · pending upload");
  void synchronize();return entityId;
}
async function queueFile(file,fields,siteId=S.siteId) {
  if (file.size>25*1024*1024) throw new Error("Maximum file size is 25 MB.");
  const item={id:uuid(),kind:"upload",account:S.me.id,siteId,file,fields,order:queueOrder=Math.max(queueOrder+1,Date.now())};
  await store.put("outbox",item.id,item); await readQueue();project();render();void synchronize();
}
async function synchronize() {
  if(S.syncing || !S.me || !navigator.onLine || S.blocked || !S.queue.length)return;
  S.syncing=true;updateConnection();
  try {
    await refreshCsrf();
    const me=await api("/api/bootstrap/");
    if(me.me.id!==S.me.id)throw new Error("The signed-in account differs from the account that recorded this work. Sign in with the original account.");
    while(true){
      await readQueue(); if(!S.queue.length||S.blocked)break;
      const item=S.queue[0];
      try {
        if(item.kind==="upload") { const form=new FormData();form.append("id",item.id);form.append("site",item.siteId);form.append("file",item.file,item.file.name);for(const[k,v]of Object.entries(item.fields))if(v)form.append(k,v);await api("/api/attachments/",{method:"POST",form}); }
        else { const reply=await api("/api/sync/",{method:"POST",data:{operations:[item.operation]}});const result=reply.results[0];if(!result?.ok){const error=new Error(errorMessage(result?.error));error.status=result?.status;error.body=result?.error;throw error;} }
        await store.remove("outbox",item.id);
      } catch(e) { if(e.status && ![429,503].includes(e.status)){item.error={status:e.status,message:e.message,body:e.body};await store.put("outbox",item.id,item);await readQueue();}throw e; }
    }
    await loadSite(S.siteId,false);await loadOverview();
    toast("All field records are synced.");
  } catch(e){toast(e.message,true);}
  finally {S.syncing=false;await readQueue();project();if(!$("#dialog").open)render();updateConnection();}
}
async function loadSite(id,draw=true) {
  if(!id)return;
  S.siteId=Number(id);await store.put("meta",`${S.me.id}:selected`,S.siteId);
  let data;
  if(navigator.onLine){try{data=await api(`/api/snapshot/?site=${S.siteId}`);await store.put("snapshots",`${S.me.id}:${S.siteId}`,data);}catch(e){if(e.status){throw e;}}}
  if(!data)data=await store.get("snapshots",`${S.me.id}:${S.siteId}`);
  if(!data){S.base=null;S.data=null;$("#main").innerHTML=empty("This site is not available offline","Prepare this site while you have a connection.");return;}
  S.base=data;const index=S.sites.findIndex(s=>s.id===S.siteId);if(index>=0)S.sites[index]=data.site;
  project();$("#site-select").value=S.siteId;if(draw)render();
}
async function loadOverview(){if(!navigator.onLine)return;try{S.overview=await api("/api/overview/");await store.put("meta",`${S.me.id}:overview`,S.overview);}catch{}}
function header(title,subtitle,actions=""){return `<div class="page-header"><div><span class="eyebrow">${esc(currentSite()?.code||"CARBONIQUE NETWORK")}</span><h1>${title}</h1><p>${subtitle}</p></div><div class="page-actions">${actions}</div></div>`;}
function stat(label,value,foot=""){return `<div class="stat"><div class="label"><span class="accent"></span>${label}</div><strong>${value}</strong><small>${foot}</small></div>`;}
function renderNavigation(){const views=[["overview","◫","Overview"],["field","✓","Field work"],["history","◷","History"],["sites","⌁","Sites & instruments"],["data","≋","Data & processing"],["inventory","▤","Equipment inventory"],["monitor","◉","Tower status"],["badm","◇","Site BADM"],["protocols","▧","Protocols"],["knowledge","▥","Reference library"]];if(admin())views.push(["admin","⚙","Administration"]);$("#navigation").innerHTML=views.map(([id,icon,label])=>`<button class="nav-button ${S.view===id?"active":""}" data-action="view" data-id="${id}"><span class="nav-icon" aria-hidden="true">${icon}</span>${label}</button>`).join("")+'<a class="nav-button" href="/fieldnotes/" target="_blank" rel="noopener"><span class="nav-icon" aria-hidden="true">↗</span>Public Field Notes</a>';}
function render(){
  const main=$("#main"),sameView=main.dataset.view===S.view&&main.dataset.site===String(S.siteId);
  const detailKey=element=>element.dataset.key||[(element.closest("article")?.id||element.closest("article")?.querySelector("h3")?.textContent||""),element.querySelector("summary")?.textContent].join(":");
  const details=sameView?new Map([...main.querySelectorAll("details")].map(element=>[detailKey(element),element.open])):new Map();
  for(const url of S.objectURLs)URL.revokeObjectURL(url);S.objectURLs=[];
  renderNavigation();updateConnection();
  const views={overview:overviewView,field:fieldView,history:historyView,sites:siteView,data:dataView,inventory:inventoryView,admin:adminView,badm:resources.badmView,protocols:resources.protocolsView,monitor:monitor.view,knowledge:records.knowledgeView};
  if(!S.data && S.view!=="overview" && S.view!=="admin" && S.view!=="protocols" && S.view!=="monitor" && S.view!=="knowledge"){$("#main").innerHTML=empty("Select an available site");return;}
  $("#main").innerHTML=(S.sites.find(s=>s.id===S.siteId)?.is_archived?`<div class="notice">This site is archived. Its history remains available.</div>`:"")+(views[S.view]||overviewView)();
  normalizeProse(main);
  main.dataset.view=S.view;main.dataset.site=String(S.siteId);
  for(const element of main.querySelectorAll("details"))if(details.has(detailKey(element)))element.open=details.get(detailKey(element));
  void hydrateImages();
}
function overviewView(){
  const rows=S.overview.length?S.overview:S.sites.map(s=>({id:s.id,code:s.code,name:s.name,pending:s.id===S.siteId?S.data?.tasks.filter(t=>t.status==="pending").length||0:"Not recorded",visits:s.id===S.siteId?S.data?.visits.length||0:"Not recorded",caveats:s.id===S.siteId?S.data?.caveats.filter(c=>c.status!=="resolved").length||0:"Not recorded"}));
  const sum=key=>rows.reduce((n,r)=>n+(Number(r[key])||0),0);
  const caveatCount=rows.every(r=>Array.isArray(r.caveat_ids))?new Set(rows.flatMap(r=>r.caveat_ids)).size:S.data?.caveats.filter(c=>c.status!=="resolved").length||0;
  return header("Field science, connected.","A shared record of the work and the measurements behind it.",write()?button("＋ Plan work","plan-task","","primary"):"")+`<div class="stats">${stat("Sites",S.sites.filter(s=>!s.is_archived).length,"Carbonique network")}${stat("Open tasks",sum("pending"),"Across accessible sites")}${stat("Field visits",sum("visits"),"Recorded history")}${stat("Data caveats",caveatCount,"Awaiting review or resolution")}</div><div class="panel-title"><h2>Your site network</h2><span class="small muted">Select a site to open its workspace</span></div><div class="site-grid">${rows.map(r=>`<button class="site-tile" data-action="open-site" data-id="${r.id}"><div class="code">${esc(r.code)}${r.archived?pill("archived"):pill("active")}</div><h3>${esc(r.name)}</h3><span class="small muted">${r.last_visit?`Last visit ${day(r.last_visit)}`:"Ready for the next field visit"}</span>${resources.conditionHTML(r.condition,true)}<div class="site-details"><span><strong>${esc(r.pending)}</strong>Open tasks</span><span><strong>${esc(r.visits)}</strong>Visits</span><span><strong>${esc(r.caveats)}</strong>Caveats</span></div></button>`).join("")||empty("No sites yet","Add your first site in Administration.")}</div><div class="notice" style="margin-top:24px">Before leaving for a site, use <strong>Prepare for fieldwork</strong> to save its tasks, site information and attachments on this device.</div>`;
}
function taskCard(t,onsite=false){
  const events=S.data.activities.filter(a=>a.task===t.id&&a.action==="commented");
  return `<article class="task-card ${t.status=== "done"?"done":""}"><div class="task-top">${onsite&&write()?`<button class="check ${t.status==="done"?"checked":""}" data-action="toggle-task" data-id="${t.id}" aria-label="${t.status==="done"?"Reopen":"Complete"} ${esc(t.title)}">${t.status==="done"?"✓":""}</button>`:""}<div class="task-title"><h3>${esc(t.title)}</h3><div class="task-meta">${pill(t.status)}${t.priority==="high"?pill("high"):""}${t.due_date?`Due ${day(t.due_date)}`:""}${t.pending?`<span class="offline-tag">Pending sync</span>`:""}</div></div></div>${t.details?`<p>${esc(t.details)}</p>`:""}${attachmentsHTML({task:t.id},S.data.attachments.filter(file=>!events.some(event=>event.id===file.activity)))}${events.length?`<div class="observations">${events.slice(-3).map(a=>`<div class="note-entry"><p><strong>${esc(a.author_name)}</strong> · ${esc(a.text)}</p>${attachmentsHTML({activity:a.id})}${write()?button("Attach to this note","upload-activity",a.id):""}</div>`).join("")}</div>`:""}<div class="row-actions">${button("Activity history","task-history",t.id)}${write()?`${button("Add note","task-note",t.id)}${button("Attach files","upload-task",t.id)}${button("Edit","edit-task",t.id)}${t.status==="done"?button("Reopen","reopen-task",t.id):""}${admin()||t.created_by===S.me.id?button("Archive","archive-task",t.id):""}`:""}</div></article>`;
}
function fieldView(){
  const v=selectedVisit(),onsite=S.mode==="onsite";
  let tasks=S.data.tasks.filter(t=>t.status!=="archived"&&(onsite?t.status==="pending"||S.data.activities.some(a=>a.task===t.id&&a.visit===v?.id&&a.action==="completed"):t.status==="pending"));
  tasks=tasks.filter(t=>(t.title+" "+t.details).toLowerCase().includes(S.filter.toLowerCase())).sort((a,b)=>(a.priority==="high"?-1:0)-(b.priority==="high"?-1:0));
  return resources.conditionHTML()+header("Field work",onsite?"Record the work as it happens.":"Prepare the next visit and keep the work organized.",write()?button("＋ Add task","plan-task","","primary"):"")+`<div class="segmented"><button data-action="field-mode" data-id="offsite" class="${!onsite?"active":""}">Off site · Plan</button><button data-action="field-mode" data-id="onsite" class="${onsite?"active":""}">On site · Record</button></div>${onsite?(v?`<div class="visit-banner"><div><span class="eyebrow">VISIT IN PROGRESS</span><strong>${esc(v.title||"Field visit")} · ${day(v.date)}</strong><p>${esc(v.crew)}${S.data.visits.filter(x=>x.status==="open").length>1?` · ${button("Choose visit","choose-visit")}`:""}</p></div><div class="row-actions">${write()?button("Visit details","edit-visit",v.id)+button("End visit","close-visit",v.id,"primary"):""}</div></div>`:`<div class="visit-banner"><div><strong>Ready to start a visit?</strong><p>Tasks and observations will be linked to this visit.</p></div>${write()?button("Start visit","start-visit","","primary"):""}</div>`):""}<div class="grid-two"><section><div class="toolbar"><input data-search="tasks" placeholder="Search tasks…" value="${esc(S.filter)}" aria-label="Search tasks"><span class="filter-count">${tasks.length} tasks</span></div><div class="task-list">${tasks.map(t=>taskCard(t,onsite)).join("")||empty("No pending tasks","Add planned work or apply a maintenance checklist.")}</div></section><aside><div class="panel"><div class="panel-title"><h3>${onsite?"Record additional work":"Maintenance checklists"}</h3></div>${onsite?`${write()&&v?button("＋ Log unplanned work","unplanned","","primary full")+button("Add visit observation","visit-note",v.id,"secondary full")+button("Calibration / sensor swap","records-calibration-new",v.id,"secondary full")+button("Flag a data issue","draft-caveat",v.id,"secondary full")+button("Attach photos / files","upload",v.id,"secondary full"):""}<p class="small muted" style="margin-top:15px">Observations and completed work are retained in the visit history.</p>`:`${S.checklists.map(c=>`<div class="section-divider"><strong>${esc(c.name)}</strong><p class="small muted">${c.tasks.length} suggested tasks</p>${write()?button("Add to site","apply-checklist",c.id):""}</div>`).join("")||empty("No checklists yet")}`}</div>${onsite&&v?`<div class="panel"><h3>Visit observations</h3>${S.data.observations.filter(o=>o.visit===v.id).map(o=>`<div class="observations note-entry"><p><strong>${esc(o.author_name)}</strong><br>${esc(o.text)}</p>${attachmentsHTML({observation:o.id})}${write()?button("Attach to this note","upload-observation",o.id):""}</div>`).join("")||`<p class="small muted">Record access conditions, weather, water level and anything unusual.</p>`}${attachmentsHTML({visit:v.id,activity:null,observation:null})}</div>`:""}</aside></div>`;
}
function draftReport(v){const lines=[`${currentSite().code}: ${v.title||"Field visit"} · ${v.date}`,`Crew: ${v.crew}`,"", "Visit activity"];for(const a of S.data.activities.filter(a=>a.visit===v.id))lines.push(`- ${a.action}: ${a.task_title}${a.text?": "+a.text:""} (${a.author_name})`);for(const o of S.data.observations.filter(o=>o.visit===v.id))lines.push(`- ${o.author_name}: ${o.text}`);if(v.narrative)lines.push("",new DOMParser().parseFromString(rich(v.narrative),"text/html").body.textContent);return lines.join("\n");}
function historyTasksView(){const tasks=S.data.tasks.filter(t=>(t.title+" "+t.details+" "+S.data.activities.filter(a=>a.task===t.id).map(a=>a.text).join(" ")).toLowerCase().includes(S.filter.toLowerCase()));return header("Task history","All planned work and its recorded activity.",`<a class="button secondary" href="/export.csv?site=${S.siteId}&kind=tasks">Export tasks CSV</a>`)+`<div class="segmented"><button data-action="history-mode" data-id="visits">Visits</button><button class="active" data-action="history-mode" data-id="tasks">All tasks</button></div><div class="toolbar"><input data-search="all-tasks" placeholder="Search every task and its notes…" aria-label="Search task history" value="${esc(S.filter)}"></div><div class="task-list">${tasks.map(t=>taskCard(t)).join("")||empty("No tasks match")}</div>`;}
function historyView(){
  if(S.histMode==="tasks")return historyTasksView();
  const visits=S.data.visits.filter(v=>(v.title+" "+v.crew+" "+v.narrative+" "+S.data.observations.filter(o=>o.visit===v.id).map(o=>o.text).join(" ")).toLowerCase().includes(S.filter.toLowerCase())&&(S.typeFilter==="all"||v.classification===S.typeFilter)).sort((a,b)=>b.date.localeCompare(a.date));
  return header("Site history","Every visit, its observations and the work that followed.",`<a class="button secondary" href="/export.csv?site=${S.siteId}&kind=visits">Export visits CSV</a><a class="button secondary" href="/export.csv?site=${S.siteId}&kind=tasks">Export tasks CSV</a>`)+`<div class="segmented"><button class="active" data-action="history-mode" data-id="visits">Visits</button><button data-action="history-mode" data-id="tasks">All tasks</button></div><div class="toolbar"><input data-search="history" placeholder="Search visits and observations…" value="${esc(S.filter)}" aria-label="Search history"><select data-filter="classification" aria-label="Visit classification">${[["all","All visit types"],["routine","Routine"],["major","Major work"],["fault","Fault"]].map(([v,l])=>`<option value="${v}" ${S.typeFilter===v?"selected":""}>${l}</option>`).join("")}</select></div><div class="timeline" aria-label="Visit timeline">${[...visits].reverse().map(v=>`<button class="${v.classification}" data-action="scroll-visit" data-id="${v.id}" title="${day(v.date)} · ${esc(v.title)}" aria-label="${day(v.date)} ${esc(v.title)}"></button>`).join("")}<span class="small muted">${visits.length} visits</span></div>${visits.map(v=>`<article class="visit-card" id="visit-${v.id}"><div class="visit-heading"><div><span class="eyebrow">${day(v.date)}</span><h3>${esc(v.title||"Field visit")}</h3><span class="small muted">${esc(v.crew)}</span></div><div>${pill(v.classification)} ${pill(v.status)} ${v.pending?`<span class="offline-tag">Pending sync</span>`:""}</div></div>${v.narrative?`<div class="rich-text section-divider">${rich(v.narrative)}</div>`:""}<details><summary>Visit report ${v.reports?.length?`· revision ${v.reports[0].revision}`:v.status==="open"?"· in progress":""}</summary><pre class="report">${esc(v.status==="closed"&&v.reports?.length?v.reports[0].text:draftReport(v))}</pre><div class="row-actions">${button("Copy text","copy-report",v.id)}${button("Copy Markdown","copy-markdown",v.id)}${v.reports?.length>1?button("Previous revisions","report-revisions",v.id):""}</div></details>${visitNotesHTML(v)}${attachmentsHTML({visit:v.id,activity:null,observation:null})}${write()?`<div class="row-actions section-divider">${v.status==="closed"?button("Reopen to add corrections","reopen-visit",v.id):button("Continue visit","continue-visit",v.id)}${button("Attach photos / files","upload",v.id)}</div>`:""}</article>`).join("")||empty("No visits match","Start a field visit or import your historical EcoFlux records.")}`;
}
function visitNotesHTML(visit){
  const observations=S.data.observations.filter(note=>note.visit===visit.id),activities=S.data.activities.filter(note=>note.visit===visit.id);
  if(!observations.length&&!activities.length)return "";
  return `<details class="section-divider"><summary>Individual notes & attachments</summary>${observations.map(note=>`<div class="note-entry"><strong>Visit observation · ${esc(note.author_name)}</strong><p>${esc(note.text)}</p>${attachmentsHTML({observation:note.id})}${write()?button("Attach to this note","upload-observation",note.id):""}</div>`).join("")}${activities.map(note=>`<div class="note-entry"><strong>${esc(note.action)} · ${esc(note.task_title)}</strong><p>${esc(note.text)}</p>${attachmentsHTML({activity:note.id})}${write()?button("Attach to this entry","upload-activity",note.id):""}</div>`).join("")}</details>`;
}
function attachmentsHTML(filter={},source=S.data.attachments){
  const files=source.filter(file=>Object.entries(filter).every(([key,value])=>value===null?file[key]==null:file[key]===value));
  if(!files.length)return "";
  const images=files.filter(file=>file.content_type?.startsWith("image/")),media=files.filter(file=>file.content_type?.startsWith("video/")||file.content_type?.startsWith("audio/"));
  const link=file=>`<a class="file-link" href="${esc(file.url||"#")}" data-action="download" data-id="${file.id}">↳ ${esc(file.caption||file.filename)} ${file.pending?"· Pending upload":""}</a>`;
  return `<div class="gallery">${images.map(file=>`<figure><a href="${esc(file.url||"#")}" data-action="download" data-id="${file.id}"><img data-file="${file.id}" src="${file.url?esc(file.url):"/static/hub/icon.svg"}" alt="${esc(file.caption||file.filename)}" loading="lazy"></a><figcaption>${esc(file.caption||file.filename)}${file.pending?" · Pending upload":""}</figcaption></figure>`).join("")}</div>`+media.map(file=>{const tag=file.content_type.startsWith("video/")?"video":"audio";return `<div class="note-media"><${tag} controls preload="metadata" data-file="${file.id}" ${file.url?`src="${esc(file.url)}"`:""}></${tag}>${link(file)}</div>`;}).join("")+files.filter(file=>!images.includes(file)&&!media.includes(file)).map(link).join("");
}
async function hydrateImages(){for(const media of document.querySelectorAll("img[data-file],video[data-file],audio[data-file]")){const file=S.data?.attachments.find(file=>file.id===media.dataset.file);if(!file)continue;let blob;if(file.pending)blob=S.queue.find(item=>item.id===file.id)?.file;else if(!S.online)blob=await store.get("downloads",`${S.me.id}:${file.url}`);if(blob){const url=URL.createObjectURL(blob);(media.closest("#dialog")?S.dialogURLs:S.objectURLs).push(url);media.src=url;}}}
function relatedTabs(group, sections, selected=sections[0].id){
  const active=sections.some(section=>section.id===selected)?selected:sections[0].id;
  return `<section class="related-records" data-related-tabs="${esc(group)}"><div class="related-tabs" role="tablist" aria-label="Related records">${sections.map(section=>`<button type="button" role="tab" id="${group}-tab-${section.id}" aria-controls="${group}-panel-${section.id}" aria-selected="${section.id===active}" tabindex="${section.id===active?0:-1}" data-action="related-tab" data-id="${section.id}">${esc(section.label)}${section.count!==undefined?`<span class="tab-count">${section.count}</span>`:""}</button>`).join("")}</div>${sections.map(section=>`<div class="related-panel" role="tabpanel" id="${group}-panel-${section.id}" aria-labelledby="${group}-tab-${section.id}" tabindex="0" ${section.id===active?"":"hidden"}>${section.html}</div>`).join("")}</section>`;
}
function activateRelatedTab(tab){
  const group=tab.closest("[data-related-tabs]");
  for(const candidate of group.querySelectorAll('[role="tab"]')){
    const active=candidate===tab;
    candidate.setAttribute("aria-selected",String(active));
    candidate.tabIndex=active?0:-1;
    document.getElementById(candidate.getAttribute("aria-controls")).hidden=!active;
  }
  if(group.dataset.relatedTabs==="site")S.siteTab=tab.dataset.id;
  tab.focus();
}
function siteView(){
  const site=S.data.site,equipment=S.data.equipment.filter(item=>item.site===site.id);
  const equipmentIds=new Set(equipment.map(item=>item.id));
  const files=S.data.attachments.filter(file=>file.site===site.id||((file.legacy||file.pending)&&(file.equipment==null||equipmentIds.has(file.equipment))));
  const visits=[...S.data.visits].sort((a,b)=>b.date.localeCompare(a.date));
  return resources.conditionHTML()+header("Sites & instruments",`${esc(site.name)} · ${esc(site.location)}`,button("Tower status","monitor-site")+(admin()?button("Edit site information","edit-site",site.id,"primary"):"" ))+relatedTabs("site",[
    {id:"reference",label:"Site reference",html:siteReferenceView()},
    {id:"calibrations",label:"Calibration log",count:S.data.calibrations.filter(r=>!r.is_archived).length,html:records.calibrationsView()},
    {id:"equipment",label:"Equipment",count:equipment.length,html:`<div class="panel table-wrap"><h2>Equipment at ${esc(site.code)}</h2><table><thead><tr><th>Instrument</th><th>Model</th><th>Serial number</th><th>Status</th><th>Actions</th></tr></thead><tbody>${equipment.map(item=>`<tr><td>${esc(item.instrument)}</td><td>${esc(item.model_number)}</td><td>${esc(item.serial_number)}</td><td>${pill(item.is_archived?"archived":item.status)}</td><td>${button("Details / history","equipment-details",item.id)}</td></tr>`).join("")}</tbody></table>${equipment.length?"":empty("No equipment assigned to this site","Use Inventory to assign instruments or inspect equipment in storage.")}</div>`},
    {id:"visits",label:"Visits",count:visits.length,html:`<div class="panel"><div class="panel-title"><h2>Site visits</h2>${button("Full visit history","site-history")}</div>${visits.map(visit=>`<div class="section-divider"><strong>${esc(visit.title||"Field visit")}</strong><span class="small muted">${day(visit.date)} · ${esc(visit.crew)}</span><div class="row-actions">${pill(visit.classification)} ${pill(visit.status)} ${button("View report","site-visit",visit.id)}</div></div>`).join("")||empty("No visits recorded yet")}</div>`},
    {id:"files",label:"Files",count:files.length,html:`<div class="panel"><h2>Site photos & documents</h2>${attachmentsHTML({},files)||empty("No files for this site","Attach files to a visit, instrument or data issue.")}</div>`},
    {id:"identifiers",label:"Data identifiers",count:S.data.dois.length,html:`<div class="panel"><div class="panel-title"><h2>Data identifiers</h2>${research()?button("＋ DOI","add-doi"):""}</div>${S.data.dois.map(record=>`<a class="file-link" href="${esc(record.doi_link)}" target="_blank" rel="noopener noreferrer">${esc(record.label)}</a>`).join("")||empty("No DOI records yet")}</div>`},
  ],S.siteTab);
}
function siteReferenceView(){
  const site=S.data.site,reference=site.metadata.reference||{},sections=clone(reference.sections||[]).filter(section=>section.h!=="Processing settings");
  for(const section of sections)for(const item of section.items||[])if(item.k==="Site name")item.v=site.name;
  const deployments=S.data.deployments.sort((a,b)=>b.installed_at.localeCompare(a.installed_at));
  const active=deployments.filter(d=>!d.removed_at||new Date(d.removed_at)>new Date());
  const equip=id=>S.data.equipment.find(e=>e.id===id);
  return `<div class="grid-two"><div><div class="panel"><div class="panel-title"><h2>${esc(site.name)}</h2>${pill(site.is_archived?"archived":"active")}</div><div class="rich-text">${rich(site.description)}</div><div class="metadata-list">${[["Site code",site.code],["AmeriFlux ID",site.amp],["Active since",day(site.date_activated)],["Coordinates",site.gps_coordinates||`${reference.lat??"Not recorded"}, ${reference.lon??"Not recorded"}`],["Logger time basis","Fixed EST · UTC−05:00"],["Retired",site.date_retired?day(site.date_retired):"Not recorded"]].map(([k,v])=>`<div class="metadata-row"><span>${esc(k)}</span><span>${esc(v)}</span></div>`).join("")}</div>${attachmentsHTML({visit:null,equipment:null,caveat:null,configuration:null,calibration:null})}</div>${resources.mediaHTML()}${sections.map(section=>`<div class="panel"><h2>${esc(section.h)}</h2>${(section.items||[]).map(i=>`<div class="metadata-row"><span>${esc(i.k)}</span><span>${esc(i.v)}</span></div>`).join("")}${(section.subs||[]).map(sub=>`<div class="section-divider"><h3>${esc(sub.h)}</h3>${(sub.items||[]).map(i=>`<div class="metadata-row"><span>${esc(i.k)}</span><span>${esc(i.v)}</span></div>`).join("")}</div>`).join("")}</div>`).join("")}</div><aside><div class="panel"><h3>Tower & sensor positions</h3>${mastDiagram(active,sections)}<p class="small muted">Heights above ground. Depths are positive downward. Reference values are shown when no deployment history is available.</p></div><div class="panel"><div class="panel-title"><h3>Instrument deployments</h3>${research()?button("＋ Add","add-deployment"):""}</div>${deployments.map(d=>`<div class="section-divider"><strong>${esc(equip(d.equipment)?.instrument||"Instrument")}</strong><span class="small muted">${esc(equip(d.equipment)?.serial_number||"")} · ${d.height_m!==null?`${d.height_m} m high`:d.depth_m!==null?`${d.depth_m} m deep`:"Position not recorded"}</span><p class="small">${time(d.installed_at)} → ${d.removed_at?time(d.removed_at):"Present"}<br>${esc(d.variables)}</p>${research()?button("Edit / record removal","edit-deployment",d.id):""}</div>`).join("")||empty("No deployment records","Historical reference metadata remains available on the left.")}</div></aside></div>`;
}
function mastDiagram(deployments,sections){let sensors=deployments.filter(d=>d.height_m!==null).map(d=>({height:Number(d.height_m),name:S.data.equipment.find(e=>e.id===d.equipment)?.instrument||"Sensor"}));if(!sensors.length)for(const section of sections)for(const sub of section.subs||[]){const value=(sub.items||[]).find(i=>/^(sonic height|height)$/i.test(i.k));if(value){const m=value.v.match(/-?\d+(?:\.\d+)?/);if(m&&Number(m[0])>=0)sensors.push({height:Number(m[0]),name:sub.h});}}if(!sensors.length)return empty("Positions not recorded","Add a deployment with sensor height or depth.");sensors.sort((a,b)=>b.height-a.height);const max=Math.max(...sensors.map(s=>s.height),1)*1.15;const y=h=>270-h/max*235;const labelY=[],labelGap=Math.min(13,240/Math.max(sensors.length-1,1));for(const sensor of sensors)labelY.push(Math.max(y(sensor.height),labelY.length?labelY.at(-1)+labelGap:30));for(let i=labelY.length-1;i>=0;i--)labelY[i]=Math.min(labelY[i],i===labelY.length-1?280:labelY[i+1]-labelGap);return `<div class="mast-wrap"><svg viewBox="0 0 200 300" role="img" aria-label="Sensor height diagram"><line x1="70" y1="30" x2="70" y2="270" stroke="#809273" stroke-width="5"/><line x1="20" y1="270" x2="180" y2="270" stroke="#9eb593" stroke-width="2"/>${Array.from({length:5},(_,i)=>{const h=max*i/4;return `<line x1="43" y1="${y(h)}" x2="52" y2="${y(h)}" stroke="#a0b498"/><text x="35" y="${y(h)+4}" text-anchor="end" font-size="10" fill="#738077">${h.toFixed(1)}</text>`;}).join("")}${sensors.map((s,i)=>`<line x1="70" y1="${y(s.height)}" x2="${105+(i%2)*25}" y2="${y(s.height)}" stroke="#527b3d" stroke-width="2"/><circle cx="${105+(i%2)*25}" cy="${y(s.height)}" r="5" fill="${["#8ec161","#54b4cc","#f7c200","#77633c"][i%4]}"/><line x1="${110+(i%2)*25}" y1="${y(s.height)}" x2="150" y2="${labelY[i]}" stroke="#a0b498"/><text x="155" y="${labelY[i]+4}" font-size="10" fill="#738077">${s.height} m</text>`).join("")}</svg><div class="mast-legend">${sensors.map((s,i)=>`<div><span class="dot" style="background:${["#8ec161","#54b4cc","#f7c200","#77633c"][i%4]}"></span> ${esc(s.name)}<br><span class="small muted">${s.height} m</span></div>`).join("")}</div></div>`;}
function referenceProcessingHTML(){const site=S.data.site,sections=[...(site.metadata.reference?.sections||[]).filter(s=>s.h==="Processing settings"),...(site.metadata.common||[]).flatMap(c=>[{h:c.title,items:[]},...(c.sections||[])])];return `<details class="panel"><summary><strong>Reference processing settings & shared network setup</strong></summary>${sections.map(section=>`<h3 class="section-divider">${esc(section.h)}</h3>${(section.items||[]).map(i=>`<div class="metadata-row"><span>${esc(i.k)}</span><span>${esc(i.v)}</span></div>`).join("")}`).join("")}</details>`;}
let processingFiles;
function dataView(){const caveats=S.data.caveats.filter(c=>(c.title+" "+c.description+" "+c.variables).toLowerCase().includes(S.filter.toLowerCase())&&(S.typeFilter==="all"||c.status===S.typeFilter));return header("Data & processing","Connect measurement issues to their affected periods and treatment.",`<a class="button secondary" href="/inventory-source.zip">Download source inventory</a>${write()?button("＋ Flag data issue","draft-caveat","","primary"):""}`)+`<div class="toolbar"><input data-search="caveats" value="${esc(S.filter)}" placeholder="Search caveats or variables…" aria-label="Search caveats"><select data-filter="caveat-status">${["all","draft","reviewed","resolved"].map(v=>`<option value="${v}" ${S.typeFilter===v?"selected":""}>${v==="all"?"All statuses":v}</option>`).join("")}</select></div>${processingFiles.view()}${referenceProcessingHTML()}<div class="data-grid">${caveats.map(c=>`<article class="caveat-card">${pill(c.status)} ${c.pending?`<span class="offline-tag">Pending sync</span>`:""}<h3>${esc(c.title)}</h3><p class="small muted">${esc(c.period_label||"Affected period needs review")}${c.variables?` · ${esc(c.variables)}`:""}</p>${c.affected_from?`<p class="small">${esc(c.affected_from)} → ${esc(c.affected_to||"Ongoing")}<br>${esc(c.time_basis)}</p>`:""}<div class="rich-text">${rich(c.description)}</div>${c.treatment?`<div class="section-divider"><h3>Processing treatment</h3><div class="rich-text">${rich(c.treatment)}</div></div>`:""}${c.evidence?.flag?`<div class="notice"><strong>Needs confirmation</strong><div class="rich-text">${rich(c.evidence.flag)}</div></div>`:""}${c.evidence?.xref?`<details><summary>Cross-check against field notes</summary><div class="rich-text">${rich(c.evidence.xref)}</div></details>`:""}${attachmentsHTML({caveat:c.id})}${Object.keys(c.evidence||{}).length?`<details class="section-divider"><summary class="small">Source evidence</summary><pre class="json-block">${esc(JSON.stringify(c.evidence,null,2))}</pre></details>`:""}<div class="row-actions section-divider">${research()?button("Review / edit","edit-caveat",c.id):""}${write()?button("Attach evidence","upload-caveat",c.id):""}</div></article>`).join("")||empty("No matching caveats")}</div><div class="panel" style="margin-top:25px"><div class="panel-title"><h2>Scientific configuration history</h2>${research()?button("＋ New version","add-config","","primary"):""}</div>${S.data.configurations.sort((a,b)=>b.effective_from.localeCompare(a.effective_from)).map(c=>`<details class="section-divider"><summary><strong>${esc(c.label)}</strong> <span class="small muted">${esc(c.effective_from)} → ${esc(c.effective_to||"Open-ended")} · ${esc(c.time_basis)}</span></summary><pre class="json-block">${esc(JSON.stringify(c.settings,null,2))}</pre><p class="small">${esc(c.notes)}</p>${attachmentsHTML({configuration:c.id})}<div class="row-actions">${research()?button("Create corrected version","replace-config",c.id):""}${write()?button("Attach INI / metadata","upload-config",c.id):""}</div></details>`).join("")||empty("No structured configurations yet","Reference processing settings remain available under Sites & instruments.")}</div>`;}
function inventoryView(){const items=S.data.equipment.filter(e=>(e.instrument+" "+e.serial_number+" "+e.model_number).toLowerCase().includes(S.filter.toLowerCase()));return header("Equipment inventory","Follow each instrument from storage to deployment and repair.",research()?button("＋ Add equipment","add-equipment","","primary"):"")+`<div class="toolbar"><input data-search="inventory" value="${esc(S.filter)}" placeholder="Search instrument, model or serial number…" aria-label="Search inventory"></div><div class="panel table-wrap"><table><thead><tr><th>Instrument</th><th>Model / manufacturer</th><th>Serial number</th><th>Current site</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(e=>`<tr><td><strong>${esc(e.instrument)}</strong><span class="small muted">Purchased ${day(e.date_purchased)}</span></td><td>${esc(e.model_number)}<span class="small muted">${esc(e.manufacturer)}</span></td><td>${esc(e.serial_number)||"Not recorded"}</td><td>${esc(S.sites.find(s=>s.id===e.site)?.code||"Storage / unassigned")}</td><td>${pill(e.is_archived?"archived":e.status)}</td><td><div class="row-actions">${button("Details / history","equipment-details",e.id)}${research()?button("Edit","edit-equipment",e.id):""}</div></td></tr>`).join("")}</tbody></table>${!items.length?empty("No tracked equipment records yet","Instrument specifications from the supplied reference are under Sites & instruments. Create tracked equipment records when serial numbers and purchase details are known."):""}</div>`;}
function adminView(){if(!admin())return empty("Administrator access required");return header("Administration","Manage sites, team access and maintenance checklists.",`<a class="button secondary" href="/admin/" target="_blank">Django administration ↗</a>`)+`<div class="panel"><div class="panel-title"><h2>Sites</h2>${button("＋ Add site","add-site","","primary")}</div><div class="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>AmeriFlux</th><th>Status</th><th></th></tr></thead><tbody>${S.sites.map(s=>`<tr><td>${esc(s.code)}</td><td>${esc(s.name)}</td><td>${esc(s.amp)}</td><td>${pill(s.is_archived?"archived":"active")}</td><td>${button("Edit","edit-site",s.id)} ${button(s.is_archived?"Restore":"Archive","archive-site",s.id)}</td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="panel-title"><h2>Team</h2>${button("＋ Create account","add-member","","primary")}</div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Username / email</th><th>Role</th><th>Access</th><th></th></tr></thead><tbody>${S.team.map(u=>`<tr><td>${esc(u.name)}</td><td>${esc(u.username)}<span class="small muted">${esc(u.email)}</span></td><td>${esc(u.role||"Not assigned")}</td><td>${u.is_active?"Active":"Disabled"}</td><td>${u.id!==S.me.id?button("Edit access","edit-member",u.id):""}</td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="panel-title"><h2>Maintenance checklists</h2>${button("＋ Add checklist","add-checklist","","primary")}</div>${S.checklists.map(c=>`<div class="section-divider"><strong>${esc(c.name)}</strong> <span class="small muted">${c.tasks.length} tasks</span> ${button("Edit","edit-checklist",c.id)}</div>`).join("")}</div>`;}

function field(name,label,value="",{type="text",required=false,help="",options,wide=false,multiple=false}={}){
  const control=options?`<select name="${name}" ${multiple?"multiple":""}>${options.map(([v,l])=>`<option value="${esc(v)}" ${multiple?(value||[]).map(String).includes(String(v))?"selected":"":String(value)===String(v)?"selected":""}>${esc(l)}</option>`).join("")}</select>`:type==="textarea"?`<textarea name="${name}" ${required?"required":""}>${esc(value)}</textarea>`:`<input name="${name}" type="${type}" value="${esc(value)}" ${required?"required":""} ${type==="number"?'step="any"':""}>`;
  return `<label class="${wide?"wide":""}">${esc(label)}${control}${help?`<span class="field-help">${esc(help)}</span>`:""}</label>`;
}
let dialogHandler;
function openForm(title,body,save,label="Save"){
  setNavigationOpen(false);
  S.dialogURLs.forEach(url=>URL.revokeObjectURL(url));S.dialogURLs=[];
  $("#dialog-title").textContent=title;$("#dialog-body").innerHTML=body;$("#dialog-error").hidden=true;$("#dialog-save").textContent=label;$("#dialog-save").hidden=!save;$("#dialog-save").disabled=false;dialogHandler=save;normalizeProse($("#dialog"));$("#dialog").showModal();void hydrateImages();
}
function closeDialog(){S.dialogURLs.forEach(url=>URL.revokeObjectURL(url));S.dialogURLs=[];$("#dialog").close();dialogHandler=null;}
$("#dialog-close").onclick=closeDialog;$("#dialog-cancel").onclick=closeDialog;
$("#dialog-form").onsubmit=async event=>{event.preventDefault();if(!dialogHandler)return;$("#dialog-save").disabled=true;try{await dialogHandler(new FormData(event.target));closeDialog();render();}catch(e){$("#dialog-error").textContent=e.message;$("#dialog-error").hidden=false;}finally{$("#dialog-save").disabled=false;}};
const values=form=>Object.fromEntries([...form.entries()].filter(([,value])=>!(value instanceof File)));
const noteFiles=form=>form.getAll("files").filter(file=>file instanceof File&&file.size>0);
const noteFileField=()=>'<label class="wide">Documents, images, audio or video (optional)<input type="file" name="files" multiple><span class="field-help">Up to 25 MB per file. The note and its files are saved together on this device before uploading.</span></label>';
const onlineOnly=()=>{if(!navigator.onLine)throw new Error("This change needs a connection. Field tasks, visits, observations and files can still be saved offline.");};
processingFiles=createProcessingFiles({data:()=>S.data,site:currentSite,canWrite:research,openForm,api,refreshCsrf,refreshWorkspace,render,esc,button,empty,toast,onlineOnly});
async function mutate(endpoint,data,id){onlineOnly();await refreshCsrf();await api(`/api/${endpoint}/${id?id+"/":""}`,{method:id?"PATCH":"POST",data});await refreshWorkspace();toast("Saved.");}
async function refreshWorkspace(){const b=await api("/api/bootstrap/");S.me=b.me;S.sites=b.sites;S.checklists=b.checklists;S.protocols=b.protocols||[];if(!S.sites.some(s=>s.id===S.siteId))S.siteId=S.sites.find(s=>!s.is_archived)?.id||S.sites[0]?.id;await store.put("meta",`${S.me.id}:bootstrap`,b);populateSites();await loadSite(S.siteId,false);await loadOverview();if(admin())S.team=await api("/api/team/");}
function taskForm(task){openForm(task?"Edit task":"Plan work at this site",`<div class="form-grid">${field("title","Task title",task?.title,{required:true,wide:true})}${field("details","Details / equipment to bring",task?.details,{type:"textarea",wide:true})}${field("priority","Priority",task?.priority||"normal",{options:[["normal","Normal"],["high","High"]]})}${field("due_date","Due date",task?.due_date,{type:"date"})}${noteFileField()}</div>`,async form=>{const data=values(form);if(task)await enqueue("task.edit",task.id,data,task.version,noteFiles(form));else await enqueue("task.create",uuid(),data,undefined,noteFiles(form));});}
function visitForm(visit){openForm(visit?"Visit details":"Start a field visit",`<div class="form-grid">${field("date","Visit date",visit?.date||today(),{type:"date",required:true})}${field("classification","Visit type",visit?.classification||"routine",{options:[["routine","Routine"],["major","Major work"],["fault","Fault"]]})}${field("title","Visit title",visit?.title||"",{wide:true})}${field("crew","Crew",visit?.crew||S.me.name,{required:true,wide:true})}${visit?field("narrative","Field notes",visit.narrative,{type:"textarea",wide:true}):""}${noteFileField()}</div>`,async form=>{const id=visit?.id||uuid();await enqueue(visit?"visit.edit":"visit.create",id,values(form),visit?.version,noteFiles(form));S.visitId=id;S.mode="onsite";S.view="field";},visit?"Save changes":"Start visit");}
function noteForm(title,save){openForm(title,field("text","Observation","",{type:"textarea",required:true})+noteFileField(),form=>save(form.get("text"),noteFiles(form)));}
function uploadForm(fields={}){openForm("Attach photographs or files",`<p class="small muted">Files are saved on this device first and uploaded when a connection is available. Maximum 25 MB per file.</p><label>Files<input name="files" type="file" multiple required></label>${field("caption","Caption / description")}`,async form=>{for(const file of form.getAll("files")){if(file.size)await queueFile(file,{...fields,caption:form.get("caption")},fields.equipment?(S.data.equipment.find(e=>e.id===Number(fields.equipment))?.site||S.siteId):S.siteId);}toast("Files saved on this device; upload is queued.");},"Save files");}
function siteForm(site){openForm(site?"Edit site information":"Add site",`<p class="notice small">Site information and field visits appear in the read-only public report.</p><div class="form-grid">${field("code","Site code",site?.code,{required:true})}${field("amp","AmeriFlux ID",site?.amp||"",{required:true})}${field("name","Site name",site?.name,{required:true,wide:true})}${field("location","Location",site?.location,{required:true,wide:true})}${field("date_activated","Active since",site?.date_activated||today(),{type:"date",required:true})}${field("date_retired","Retired date",site?.date_retired,{type:"date"})}${field("gps_coordinates","Coordinates",site?.gps_coordinates,{wide:true})}${field("description","Site description",site?.description,{type:"textarea",required:true,wide:true})}<details class="wide"><summary>Advanced reference metadata</summary>${field("metadata","Reference metadata (JSON)",JSON.stringify(site?.metadata||{},null,2),{type:"textarea",help:"Preserve the reference.sections structure to retain instrument information."})}</details></div>`,async form=>{const d=values(form);d.date_retired=d.date_retired||null;d.metadata=JSON.parse(d.metadata||"{}");if(site)d.base_version=site.version;await mutate("sites",d,site?.id);});}
function equipmentForm(equipment){openForm(equipment?"Edit equipment":"Add equipment",`<div class="form-grid">${field("instrument","Instrument",equipment?.instrument,{required:true,wide:true})}${field("manufacturer","Manufacturer",equipment?.manufacturer)}${field("model_number","Model",equipment?.model_number)}${field("serial_number","Serial number",equipment?.serial_number)}${field("date_purchased","Purchase date",equipment?.date_purchased||today(),{type:"date",required:true})}${field("site","Current location",equipment?.site||"",{options:[["","Storage / unassigned"],...S.sites.map(s=>[s.id,s.code])]})}${field("status","Status",equipment?.status||"available",{options:[["available","Available"],["deployed","Deployed"],["repair","Under repair"],["retired","Retired"]]})}${field("notes","Notes",equipment?.notes,{type:"textarea",wide:true})}<label class="wide"><input type="checkbox" name="is_archived" ${equipment?.is_archived?"checked":""}>Archive this equipment record</label></div>`,async form=>{const d=values(form);d.site=d.site?Number(d.site):null;d.is_archived=form.has("is_archived");if(equipment)d.base_version=equipment.version;await mutate("equipment",d,equipment?.id);});}
const localInput=value=>{if(!value)return "";const d=new Date(value);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);};
const ecInput=value=>value?new Date(new Date(value).getTime()-5*3600000).toISOString().slice(0,16):"";
const ecUTC=value=>value?new Date(value+"-05:00").toISOString():null;
function deploymentForm(deployment){const equipment=S.data.equipment.filter(e=>!e.is_archived);openForm(deployment?"Edit deployment / record removal":"Record instrument deployment",`<div class="form-grid">${field("equipment","Individual instrument",deployment?.equipment||equipment[0]?.id,{options:equipment.map(e=>[e.id,`${e.instrument} · ${e.serial_number||e.model_number||e.id}`]),required:true,wide:true})}${field("installed_at","Installed at (your local time)",localInput(deployment?.installed_at||new Date().toISOString()),{type:"datetime-local",required:true})}${field("removed_at","Removed at (your local time)",localInput(deployment?.removed_at),{type:"datetime-local"})}${field("height_m","Height above ground (m)",deployment?.height_m,{type:"number"})}${field("depth_m","Depth below ground (m)",deployment?.depth_m,{type:"number"})}${field("variables","Measured variables",deployment?.variables,{wide:true,help:"For example TA_1_1_1, RH_1_1_1"})}${field("position","Position / mounting location",deployment?.position,{wide:true})}${field("notes","Notes",deployment?.notes,{type:"textarea",wide:true})}</div>`,async form=>{const d=values(form);d.site=S.siteId;d.equipment=Number(d.equipment);d.installed_at=new Date(d.installed_at).toISOString();d.removed_at=d.removed_at?new Date(d.removed_at).toISOString():null;d.height_m=d.height_m||null;d.depth_m=d.depth_m||null;if(deployment)d.base_version=deployment.version;await mutate("deployments",d,deployment?.id);});}
function configForm(previous){openForm(previous?"Create corrected configuration version":"New processing configuration",`<p class="small muted">Times below use fixed EST (UTC−05:00), without daylight saving time. Existing configurations are retained.</p><div class="form-grid">${field("label","Configuration label",previous?.label||"EddyPro / SmartFlux settings",{required:true,wide:true})}${field("effective_from","Effective from (fixed EST)",ecInput(previous?.effective_from)||today()+"T00:00",{type:"datetime-local",required:true})}${field("effective_to","Effective to (fixed EST)",ecInput(previous?.effective_to),{type:"datetime-local"})}${field("deployment","Related deployment",previous?.deployment||"",{options:[["","Site-wide settings"],...S.data.deployments.map(d=>[d.id,`${S.data.equipment.find(e=>e.id===d.equipment)?.instrument||"Instrument"} · ${time(d.installed_at)}`])],wide:true})}${field("settings","Processing settings (JSON)",JSON.stringify(previous?.settings||{sonic_height_m:null,north_offset_deg:null,intake_length_cm:null},null,2),{type:"textarea",required:true,wide:true})}${field("notes","Reason / supporting notes",previous?.notes,{type:"textarea",wide:true})}</div>`,async form=>{const d=values(form);d.site=S.siteId;d.effective_from=ecUTC(d.effective_from);d.effective_to=ecUTC(d.effective_to);d.deployment=d.deployment||null;d.settings=JSON.parse(d.settings);d.time_basis="EST_FIXED_UTC_MINUS_05";if(previous)d.supersedes=previous.id;await mutate("configurations",d);});}
function caveatForm(caveat,visitId){
  if(!caveat){openForm("Flag a data issue",`<div class="form-grid">${field("title","Issue title","",{required:true,wide:true})}${field("description","What happened?","",{type:"textarea",required:true,wide:true})}${field("variables","Affected variables","",{wide:true})}${field("period_label","Affected period / uncertainty","",{wide:true,help:"For example: since the previous visit; exact start needs checking."})}</div>`,form=>enqueue("caveat.draft",uuid(),{...values(form),visit_id:visitId||null}),"Save draft for review");return;}
  openForm("Review data caveat",`<p class="notice small">Caveats appear in the read-only public report with their current review status. Saved changes appear on refresh. <a href="/fieldnotes/" target="_blank" rel="noopener">View public report ↗</a></p><p class="small muted">Measurement times use fixed EST (UTC−05:00). Leave unknown boundaries empty and describe the uncertainty.</p><div class="form-grid">${field("title","Title",caveat.title,{required:true,wide:true})}${field("sites","Affected sites",caveat.sites,{options:S.sites.map(s=>[s.id,s.code]),multiple:true,wide:true})}${field("status","Review status",caveat.status,{options:[["draft","Draft"],["reviewed","Reviewed"],["resolved","Resolved"]]})}${field("variables","Variables",caveat.variables)}${field("affected_from","Affected from (fixed EST)",ecInput(caveat.affected_from),{type:"datetime-local"})}${field("affected_to","Affected to (fixed EST)",ecInput(caveat.affected_to),{type:"datetime-local"})}${field("period_label","Affected period / uncertainty",caveat.period_label,{wide:true})}${field("description","Description",caveat.description,{type:"textarea",wide:true})}${field("treatment","Recommended processing treatment",caveat.treatment,{type:"textarea",wide:true})}${field("equipment","Related instrument",caveat.equipment||"",{options:[["","None selected"],...S.data.equipment.map(e=>[e.id,`${e.instrument} · ${e.serial_number}`])],wide:true})}${field("configurations","Related configurations",caveat.configurations||[],{options:[...new Map([...S.data.configurations,...(caveat.configuration_details||[])].map(c=>[c.id,c])).values()].map(c=>[c.id,c.label+" · "+ecInput(c.effective_from)]),multiple:true,wide:true})}</div>`,async form=>{const d=values(form);d.sites=form.getAll("sites").map(Number);d.configurations=form.getAll("configurations");d.affected_from=ecUTC(d.affected_from);d.affected_to=ecUTC(d.affected_to);d.equipment=d.equipment?Number(d.equipment):null;d.base_version=caveat.version;await mutate("caveats",d,caveat.id);});
}
function memberForm(user){openForm(user?"Edit team access":"Create team account",`<div class="form-grid">${!user?field("username","Username","",{required:true}):""}${!user?field("name","Name","",{required:true}):""}${!user?field("email","Email address","",{type:"email",wide:true}):""}${field("password",user?"New password (optional)":"Initial password","",{type:"password",required:!user,wide:true,help:"Share credentials directly with the colleague; this form does not send an invitation."})}${field("role","Role",user?.role||"member",{options:[["viewer","Viewer"],["member","Field member"],["researcher","Researcher"],["manager","Manager"],["admin","Administrator"]],wide:true})}${field("sites","Allowed sites",user?.sites||[],{options:S.sites.map(s=>[s.id,s.code]),multiple:true,wide:true,help:"Leave empty for access to all sites."})}${user?`<label class="wide"><input type="checkbox" name="is_active" ${user.is_active?"checked":""}>Account is active</label>`:""}</div>`,async form=>{onlineOnly();const d=values(form);d.sites=form.getAll("sites").map(Number);if(user){d.id=user.id;d.is_active=form.has("is_active");}await api("/api/team/",{method:user?"PATCH":"POST",data:d});await refreshWorkspace();toast("Team access updated.");});}
function checklistForm(checklist){openForm(checklist?"Edit maintenance checklist":"Add maintenance checklist",`${field("name","Checklist name",checklist?.name,{required:true})}${field("lines","Tasks",checklist?.tasks.map(t=>`${t.title}|${t.details||""}|${t.priority||"normal"}`).join("\n")||"",{type:"textarea",required:true,help:"One task per line: title | details | normal or high"})}`,async form=>{const tasks=form.get("lines").split("\n").filter(l=>l.trim()).map(line=>{const[title,details,priority]=line.split("|").map(v=>v.trim());return{title,details:details||"",priority:priority||"normal"};});await mutate("checklists",{name:form.get("name"),tasks},checklist?.id);});}
async function copy(text){if(navigator.clipboard){try{await navigator.clipboard.writeText(text);toast("Copied.");return;}catch{}}const box=document.createElement("textarea");box.value=text;document.body.append(box);box.select();document.execCommand("copy");box.remove();toast("Copied.");}
async function downloadAttachment(id){const attachment=S.data.attachments.find(a=>a.id===id);let blob=attachment.pending?S.queue.find(q=>q.id===id)?.file:await store.get("downloads",`${S.me.id}:${attachment.url}`);if(!blob){const response=await fetch(attachment.url,{credentials:"same-origin"});if(!response.ok||response.redirected)throw new Error("Sign in to download this file.");blob=await response.blob();}const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=attachment.filename||"attachment";link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
async function prepareFieldwork(){
  onlineOnly();openForm("Prepare for fieldwork",`<p>Choose sites to save on this device, including tasks, instrument reference information and attachments.</p><p class="small muted">Use a trusted device. Cached records and photographs remain available offline until you sign out and clear this device.</p>${field("sites","Sites",[S.siteId],{options:S.sites.filter(s=>!s.is_archived).map(s=>[s.id,s.code+" · "+s.name]),multiple:true})}<label><input type="checkbox" name="files" checked>Download attachments and protocols</label><div id="prepare-progress" class="small muted"></div>`,async form=>{
    if(!("serviceWorker" in navigator))throw new Error("Offline reopening requires a browser with service-worker support and HTTPS (or localhost).");
    const ids=form.getAll("sites");if(!ids.length)throw new Error("Select at least one site.");
    const registration=await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(()=>reject(new Error("The offline app could not be installed. Check your connection and use HTTPS or localhost.")),15000))]);
    await new Promise((resolve,reject)=>{const channel=new MessageChannel(),timer=setTimeout(()=>{channel.port1.close();reject(new Error("The app shell could not be saved. Try preparing again while connected."));},15000);channel.port1.onmessage=event=>{clearTimeout(timer);channel.port1.close();event.data.ok?resolve():reject(new Error(event.data.error));};registration.active.postMessage("CACHE_SHELL",[channel.port2]);});
    let count=0,missing=0;
    for(const id of ids){$("#prepare-progress").textContent=`Saving ${S.sites.find(s=>s.id===Number(id)).code}…`;const data=await api(`/api/snapshot/?site=${id}`);await store.put("snapshots",`${S.me.id}:${id}`,data);if(form.has("files"))for(const a of data.attachments){try{const response=await fetch(a.url,{credentials:"same-origin"});if(!response.ok||response.redirected)throw new Error();await store.put("downloads",`${S.me.id}:${a.url}`,await response.blob());count++;}catch{missing++;}}}
    await resources.loadSchema();if(form.has("files"))for(const protocol of S.protocols.filter(p=>p.available!==false)){try{const response=await fetch(protocol.url,{credentials:"same-origin"});if(!response.ok||response.redirected)throw new Error();await store.put("downloads",`${S.me.id}:${protocol.url}`,await response.blob());count++;}catch{missing++;}}
    await store.put("meta",`${S.me.id}:prepared`,new Date().toISOString());S.prepared=true;toast(`${ids.length} sites and ${count} attachments saved for offline use.${missing?` ${missing} files could not be downloaded.`:""}`);
  },"Download selected sites");
}
async function queueDialog(){await readQueue();openForm("Synchronization queue",`<p class="small muted">${S.queue.length} records remain on this device. A blocked item pauses later records so dependent work stays in order.</p>${S.queue.map(item=>`<div class="section-divider"><strong>${esc(item.kind==="upload"?item.file.name:item.operation.kind)}</strong><p class="small muted">${esc(S.sites.find(s=>s.id===item.siteId)?.code)} · ${time(new Date(item.order).toISOString())}</p>${item.error?`<div class="error">${esc(item.error.message)}</div><div class="row-actions">${button("Review & retry","review-queue",item.id)}${button("Export pending record","export-queue",item.id)}${button("Discard this record","discard-queue",item.id,"danger small")}</div>`:""}</div>`).join("")||empty("Everything is synced")}`,async()=>{closeDialog();S.blocked=null;void synchronize();},"Sync now");}
async function reviewQueue(id){const item=S.queue.find(q=>q.id===id);onlineOnly();const latest=await api(`/api/snapshot/?site=${item.siteId}`);const record=item.kind==="operation"?[...latest.tasks,...latest.visits,...(latest.calibrations||[])].find(r=>r.id===item.operation.entity_id):null;closeDialog();openForm("Review the conflicting record",`<p>Compare your queued change with the current server record before retrying.</p><h3>Your change</h3><pre class="json-block">${esc(JSON.stringify(item.operation?.payload||item.fields,null,2))}</pre><h3>Current record</h3><pre class="json-block">${esc(JSON.stringify(record||item.error.body,null,2))}</pre><p class="small muted">Retry uses the current version. Your intended change will still be checked by the server.</p>`,async()=>{if(item.operation){item.operation.id=uuid();if(record)item.operation.base_version=record.version;}delete item.error;await store.put("outbox",item.id,item);await readQueue();void synchronize();},"Apply my change to current version");}
async function navigate(view){S.view=view;S.filter="";S.typeFilter="all";location.hash=view;setNavigationOpen(false);if(view==="badm")await resources.loadSchema();if(view==="knowledge")await records.loadKnowledge();if(view==="monitor"){monitor.network();render();await monitor.load(true);return;}if(view==="admin"&&admin()&&navigator.onLine)S.team=await api("/api/team/");render();}
document.addEventListener("click",async event=>{
  const target=event.target.closest("[data-action]");if(!target)return;event.preventDefault();const action=target.dataset.action,id=target.dataset.id;
  try{if(await records.action(action,id))return;if(await processingFiles.action(action,id))return;if(await resources.action(action,id))return;if(await monitor.action(action,id))return;const task=S.data?.tasks.find(t=>t.id===id),visit=S.data?.visits.find(v=>v.id===id);switch(action){
    case"related-tab":activateRelatedTab(target);break;
    case"site-history":S.histMode="visits";await navigate("history");break;
    case"site-visit":S.histMode="visits";await navigate("history");document.getElementById(`visit-${id}`)?.scrollIntoView({block:"start"});break;
    case"view":await navigate(id);break;
    case"open-site":await loadSite(Number(id));await navigate("sites");break;
    case"field-mode":S.mode=id;render();break;
    case"history-mode":S.histMode=id;S.filter="";render();break;
    case"plan-task":taskForm();break;
    case"edit-task":taskForm(task);break;
    case"start-visit":visitForm();break;
    case"edit-visit":visitForm(visit);break;
    case"continue-visit":S.visitId=id;S.mode="onsite";await navigate("field");break;
    case"choose-visit":openForm("Choose the visit you are working on",field("visit","Open visit",selectedVisit()?.id,{options:S.data.visits.filter(v=>v.status==="open").map(v=>[v.id,`${v.date} · ${v.title||v.crew}`])}),form=>{S.visitId=form.get("visit");});break;
    case"close-visit":openForm("Review and end this visit",`<pre class="report">${esc(draftReport(visit))}</pre><p class="small muted">The server saves a permanent report after all earlier queued work has synced.</p>`,()=>enqueue("visit.close",visit.id,{},visit.version),"End visit");break;
    case"reopen-visit":openForm("Reopen this visit?","<p>Earlier report revisions remain available. Close the visit again after adding your corrections.</p>",()=>enqueue("visit.reopen",visit.id,{},visit.version),"Reopen visit");break;
    case"toggle-task":if(task.status==="done")await enqueue("task.reopen",id,{visit_id:selectedVisit()?.id||null},task.version);else if(!selectedVisit())visitForm();else await enqueue("task.complete",id,{visit_id:selectedVisit().id},task.version);break;
    case"reopen-task":await enqueue("task.reopen",id,{visit_id:selectedVisit()?.id||null},task.version);break;
    case"archive-task":openForm("Archive this task?","<p>The task leaves the working list. Its activity and visit history remain available.</p>",()=>enqueue("task.archive",id,{},task.version),"Archive");break;
    case"task-history":openForm("Task activity history",S.data.activities.filter(a=>a.task===id).map(a=>`<div class="section-divider"><strong>${esc(a.action)} · ${esc(a.task_title)}</strong><p class="small muted">${esc(a.author_name)} · ${time(a.occurred_at)}</p><p>${esc(a.text)}</p>${attachmentsHTML({activity:a.id})}${write()?button("Attach to this entry","upload-activity",a.id):""}</div>`).join("")||empty("No activity yet"),null);break;
    case"task-note":noteForm("Add task observation",(text,files)=>enqueue("task.comment",id,{text,visit_id:S.view==="field"&&S.mode==="onsite"?selectedVisit()?.id||null:null},undefined,files));break;
    case"visit-note":noteForm("Add visit observation",(text,files)=>enqueue("observation.create",uuid(),{visit_id:id,text},undefined,files));break;
    case"unplanned":openForm("Record unplanned work",`${field("title","Work performed","",{required:true})}${field("details","Details","",{type:"textarea"})}${field("outcome","Outcome","done",{options:[["done","Completed during this visit"],["pending","New task for a later visit"]]})}${noteFileField()}`,async form=>{const d=values(form),tid=uuid(),vid=selectedVisit()?.id;if(!vid)throw new Error("Start a visit first.");await enqueue("task.create",tid,{title:d.title,details:d.details,visit_id:vid},undefined,noteFiles(form));if(d.outcome==="done")await enqueue("task.complete",tid,{visit_id:vid},1);});break;
    case"apply-checklist":{const checklist=S.checklists.find(c=>c.id===Number(id));openForm("Apply maintenance checklist",`<p>Add ${checklist.tasks.length} tasks from ${esc(checklist.name)}?</p>`,async()=>{for(const t of checklist.tasks)await enqueue("task.create",uuid(),t);});break;}
    case"draft-caveat":caveatForm(null,id||selectedVisit()?.id);break;
    case"edit-caveat":caveatForm(S.data.caveats.find(c=>c.id===id));break;
    case"upload":uploadForm(id?{visit:id}:{});break;
    case"upload-task":uploadForm({task:id});break;
    case"upload-activity":uploadForm({activity:id});break;
    case"upload-observation":uploadForm({observation:id});break;
    case"upload-caveat":uploadForm({caveat:id});break;
    case"upload-config":uploadForm({configuration:id});break;
    case"download":await downloadAttachment(id);break;
    case"copy-report":await copy(visit.status==="closed"&&visit.reports?.length?visit.reports[0].text:draftReport(visit));break;
    case"copy-markdown":await copy(visit.status==="closed"&&visit.reports?.length?visit.reports[0].markdown:"## "+draftReport(visit));break;
    case"report-revisions":openForm("Previous report revisions",visit.reports.map(r=>`<h3>Revision ${r.revision} · ${time(r.created_at)}</h3><pre class="report">${esc(r.text)}</pre>`).join(""),null);break;
    case"scroll-visit":document.getElementById("visit-"+id)?.scrollIntoView({behavior:"smooth",block:"center"});break;
    case"add-site":siteForm();break;
    case"edit-site":siteForm(S.sites.find(s=>s.id===Number(id)));break;
    case"archive-site":{const site=S.sites.find(s=>s.id===Number(id));openForm(site.is_archived?"Restore site?":"Archive site?","<p>All visits, equipment links and measurement history are retained.</p>",()=>mutate("sites",{is_archived:!site.is_archived,base_version:site.version},site.id));break;}
    case"add-equipment":equipmentForm();break;
    case"edit-equipment":equipmentForm(S.data.equipment.find(e=>e.id===Number(id)));break;
    case"equipment-details":{
      const e=S.data.equipment.find(e=>e.id===Number(id));
      const history=S.data.equipment_history.filter(record=>record.item===e.id);
      const files=S.data.attachments.filter(file=>file.equipment===e.id);
      openForm(e.instrument+" · "+e.serial_number,`<p>${esc(e.notes)}</p>`+relatedTabs(`equipment-${e.id}`,[
        {id:"history",label:"Service history",count:history.length,html:history.map(record=>`<div class="section-divider"><span class="small muted">${day(record.date)}</span><p>${esc(record.note)}</p></div>`).join("")+(history.length?"":empty("No service history yet"))+(write()?field("note","Add a service observation","",{type:"textarea"}):"")},
        {id:"files",label:"Files",count:files.length,html:(attachmentsHTML({},files)||empty("No equipment files yet"))+(write()?button("Attach equipment document","upload-equipment",e.id):"")},
      ]),write()?async form=>{if(form.get("note"))await mutate("equipment-history",{item:e.id,date:today(),note:form.get("note")});}:null);
      break;
    }
    case"upload-equipment":closeDialog();uploadForm({equipment:Number(id)});break;
    case"add-deployment":deploymentForm();break;
    case"edit-deployment":deploymentForm(S.data.deployments.find(d=>d.id===id));break;
    case"add-config":configForm();break;
    case"replace-config":configForm(S.data.configurations.find(c=>c.id===id));break;
    case"add-doi":openForm("Add data DOI",field("label","Label","",{required:true})+field("doi_link","DOI URL","https://doi.org/",{type:"url",required:true}),form=>mutate("dois",{...values(form),site:S.siteId}));break;
    case"add-member":memberForm();break;
    case"edit-member":memberForm(S.team.find(u=>u.id===Number(id)));break;
    case"add-checklist":checklistForm();break;
    case"edit-checklist":checklistForm(S.checklists.find(c=>c.id===Number(id)));break;
    case"review-queue":await reviewQueue(id);break;
    case"export-queue":{const item=S.queue.find(q=>q.id===id);const blob=item.kind==="upload"?item.file:new Blob([JSON.stringify(item.operation,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=item.file?.name||"pending-operation.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);break;}
    case"discard-queue":{const item=S.queue.find(q=>q.id===id);closeDialog();openForm("Discard this queued record?","<p>This removes only the selected pending record from this device. Later dependent records may need review. Export the record first if you want a separate copy.</p>",async()=>{await store.remove("outbox",item.id);await readQueue();project();void synchronize();},"Discard record");break;}
  }}catch(e){toast(e.message,true);}
});
document.addEventListener("keydown",event=>{
  const tab=event.target.closest('[data-action="related-tab"]');
  if(!tab||!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
  event.preventDefault();
  const tabs=[...tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]')];
  const index=tabs.indexOf(tab);
  const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(index+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;
  activateRelatedTab(tabs[next]);
});
let searchTimer;document.addEventListener("input",event=>{if(!event.target.dataset.search)return;S.filter=event.target.value;clearTimeout(searchTimer);const start=event.target.selectionStart,end=event.target.selectionEnd,key=event.target.dataset.search;searchTimer=setTimeout(()=>{render();const input=document.querySelector(`[data-search="${key}"]`);input?.focus();input?.setSelectionRange(start,end);},180);});
document.addEventListener("change",event=>{if(event.target.dataset.filter){S.typeFilter=event.target.value;render();}});
$("#site-select").onchange=async event=>{S.visitId=null;await loadSite(Number(event.target.value));};
// Older prepared shells can still load the updated assets while offline.
if(!$("#navigation-close"))$(".sidebar").insertAdjacentHTML("afterbegin",'<button id="navigation-close" class="icon-button navigation-close" aria-label="Close navigation">×</button>');
if(!$("#navigation-backdrop"))document.body.insertAdjacentHTML("afterbegin",'<button id="navigation-backdrop" class="navigation-backdrop" aria-label="Close navigation" tabindex="-1" hidden></button>');
$(".sidebar").id="workspace-navigation";
$(".sidebar").setAttribute("aria-label","Workspace navigation");
$("#mobile-menu").setAttribute("aria-controls","workspace-navigation");
$("#mobile-menu").setAttribute("aria-label","Open navigation");
// Keep a phone drawer accessible without allowing clicks behind it.
const phoneNavigation=window.matchMedia("(max-width:760px)");
function setNavigationOpen(open,{restoreFocus=true}={}){
  const sidebar=$(".sidebar"),wasOpen=sidebar.classList.contains("visible");
  const expanded=phoneNavigation.matches&&open;
  sidebar.classList.toggle("visible",expanded);
  sidebar.inert=phoneNavigation.matches&&!expanded;
  $(".workspace").inert=expanded;
  document.body.classList.toggle("navigation-open",expanded);
  $("#navigation-backdrop").hidden=!expanded;
  $("#mobile-menu").setAttribute("aria-expanded",String(expanded));
  if(expanded){
    sidebar.setAttribute("role","dialog");sidebar.setAttribute("aria-modal","true");
    $("#navigation-close").focus();
  }else{
    sidebar.removeAttribute("role");sidebar.removeAttribute("aria-modal");
    if(wasOpen&&restoreFocus&&phoneNavigation.matches)$("#mobile-menu").focus();
  }
}
$("#mobile-menu").onclick=()=>setNavigationOpen(true);
$("#navigation-close").onclick=()=>setNavigationOpen(false);
$("#navigation-backdrop").onclick=()=>setNavigationOpen(false);
phoneNavigation.addEventListener("change",()=>setNavigationOpen(false));
document.addEventListener("keydown",event=>{
  if(!phoneNavigation.matches||!$(".sidebar").classList.contains("visible"))return;
  if(event.key==="Escape"){event.preventDefault();setNavigationOpen(false);return;}
  if(event.key!=="Tab")return;
  const controls=[...$(".sidebar").querySelectorAll("a[href],button:not(:disabled)")].filter(el=>el.getClientRects().length);
  const first=controls[0],last=controls.at(-1);
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
});
setNavigationOpen(false,{restoreFocus:false});
$("#prepare-button").onclick=()=>prepareFieldwork().catch(e=>toast(e.message,true));
$("#queue-button").onclick=()=>queueDialog().catch(e=>toast(e.message,true));
$("#refresh-button").onclick=async()=>{try{await synchronize();await refreshWorkspace();render();toast("Workspace refreshed.");}catch(e){toast(e.message,true);}};
$("#logout-button").onclick=()=>openForm("Sign out and clear this device?",`<p>${S.queue.length?`There are ${S.queue.length} pending records. Sync or export them before signing out.`:"Your offline site copies and downloaded attachments will be removed from this device."}</p>`,async()=>{if(S.queue.length)throw new Error("Resolve or export and discard the pending records before clearing this device.");await refreshCsrf();await fetch("/accounts/logout/",{method:"POST",headers:{"X-CSRFToken":S.csrf},credentials:"same-origin"});await store.clearDevice();const reg=await navigator.serviceWorker?.getRegistration();reg?.active?.postMessage("CLEAR_SHELL");location.href="/accounts/login/";},"Sign out & clear");
window.addEventListener("online",()=>{S.online=true;updateConnection();void synchronize();});window.addEventListener("offline",()=>{S.online=false;updateConnection();});
window.addEventListener("hashchange",()=>{const view=location.hash.slice(1);if(view&&view!==S.view)void navigate(view);});
function populateSites(){$("#site-select").innerHTML=S.sites.map(s=>`<option value="${s.id}">${esc(s.code)} · ${esc(s.name)}</option>`).join("");if(S.siteId)$("#site-select").value=S.siteId;}
async function boot(){
  try{
    let bootstrap;
    if(navigator.onLine){try{bootstrap=await api("/api/bootstrap/");await store.put("meta","active-account",bootstrap.me.id);await store.put("meta",`${bootstrap.me.id}:bootstrap`,bootstrap);}catch(e){if(e.status)throw e;}}
    if(!bootstrap){const account=await store.get("meta","active-account");bootstrap=await store.get("meta",`${account}:bootstrap`);}
    if(!bootstrap)throw new Error("Sign in online and prepare your sites before working offline.");
    S.me=bootstrap.me;S.sites=bootstrap.sites;S.checklists=bootstrap.checklists;S.protocols=bootstrap.protocols||[];queueOrder=Math.max(queueOrder,...(await store.all("outbox")).map(q=>q.order||0));
    S.siteId=(await store.get("meta",`${S.me.id}:selected`))||S.sites.find(s=>!s.is_archived)?.id||S.sites[0]?.id;
    S.overview=(await store.get("meta",`${S.me.id}:overview`))||[];S.prepared=!!(await store.get("meta",`${S.me.id}:prepared`));
    $("#user-badge").textContent=S.me.name.split(/\s+/).map(x=>x[0]).slice(0,2).join("").toUpperCase();$("#user-badge").title=S.me.name+" · "+S.me.role;populateSites();await readQueue();await loadSite(S.siteId,false);await loadOverview();if(S.view==="badm")await resources.loadSchema();if(S.view==="admin"&&admin()&&navigator.onLine)S.team=await api("/api/team/");render();
    if(S.view==="knowledge"){await records.loadKnowledge();render();}
    if(S.view==="monitor")void monitor.load(true);
    if("serviceWorker" in navigator)await navigator.serviceWorker.register("/sw.js",{scope:"/"});
    void synchronize();
    setInterval(async()=>{if(!navigator.onLine||S.syncing||$("#dialog").open||$(".sidebar").classList.contains("visible"))return;if(S.queue.length){void synchronize();return;}if(S.view==="monitor"){await monitor.auto();return;}try{await loadSite(S.siteId,false);if(S.view==="overview")await loadOverview();render();}catch{}},15000);
  }catch(e){$("#main").innerHTML=empty("Could not open the workspace",e.message);toast(e.message,true);}
}
const resources=createResources({S,esc,rich,day,time,button,empty,field,openForm,api,refreshCsrf,refreshWorkspace,render,toast,onlineOnly,header,store});
const monitor=createMonitor({S,esc,button,empty,header,time,api,render,toast,store});
const records=createRecordResources({S,esc,day,time,button,empty,field,openForm,api,refreshCsrf,refreshWorkspace,render,toast,onlineOnly,header,enqueue,uploadForm,attachmentsHTML,uuid,today,write,values,noteFileField,noteFiles});
void boot();
