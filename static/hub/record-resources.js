import { showPDF } from "./pdf-viewer.js";

export function createRecordResources(ctx) {
  const {privateFetch,S, esc, day, time, button, empty, field, openForm, api, refreshCsrf, refreshWorkspace, render, toast, onlineOnly, header, enqueue, uploadForm, attachmentsHTML, uuid, today, write, values, noteFileField, noteFiles} = ctx;
  const types=[["swap","Sensor swap"],["onsite","On-site calibration"],["lab","Lab calibration"]];
  const preparations=[["cleaned_calibrated","Cleaned and lab calibrated"],["cleaned","Cleaned only"],["unknown","Not confirmed"]];
  const categories=[["general","General information"],["hardware","Hardware and manuals"],["wiring","Wiring and installation"],["troubleshooting","Troubleshooting"],["repairs","Repairs and service"],["notes","Notebook / OneNote"]];
  const K={scope:"site",category:"all",archived:false,entries:[]};
  const C={type:"all",archived:false,search:""};
  const siteWritable=()=>write()&&!S.sites.find(s=>s.id===S.siteId)?.is_archived;
  const label=(options,value)=>options.find(([key])=>key===value)?.[1]||value;
  const equipmentOptions=(selected)=>[["","Not linked / historical sensor"],...(S.data?.equipment||[]).map(e=>[e.id,`${e.instrument} · ${e.serial_number||"serial unknown"}`]),...(selected&&!(S.data?.equipment||[]).some(e=>e.id===selected)?[[selected,"Previously linked inventory instrument"]]:[])];
  const entries=()=>S.data?.knowledge||K.entries;
  const entry=id=>entries().find(item=>item.id===id);
  const canEdit=item=>write()&&(item.site?!S.sites.find(s=>s.id===item.site)?.is_archived:S.me.can_edit_shared_references===true);
  const text=value=>`<div class="record-text">${esc(value)}</div>`;
  const filesField=()=>'<label class="wide">Supporting documents or images<input type="file" name="files" multiple><span class="field-help">Up to 10 files, 25 MB total. Files are uploaded while connected. Original OneNote files can be stored here; use a web sharing link to open a notebook.</span></label>';
  async function loadKnowledge(){
    if(!navigator.onLine)return;
    const data=await api("/api/knowledge/");K.entries=data.entries;
    if(S.base){S.base.knowledge=data.entries;S.data.knowledge=data.entries;}
  }
  function calibrationsView(){
    const all=S.data?.calibrations||[];
    const rows=all.filter(r=>r.is_archived===C.archived&&(C.type==="all"||r.event_type===C.type)&&[r.sensor_name,r.sensor_model,r.serial_number,r.replacement_serial_number,r.replacement_description,r.notes,r.performed_by,r.reference].join(" ").toLowerCase().includes(C.search.toLowerCase())).sort((a,b)=>b.event_date.localeCompare(a.event_date));
    return `<section class="panel"><div class="panel-title"><div><h2>Calibration log</h2><p class="small muted">Sensor swaps, on-site work, and laboratory calibrations for this site.</p></div>${siteWritable()?button("＋ Record calibration","records-calibration-new","","primary"):""}</div><div class="toolbar"><input data-record-search="calibrations" aria-label="Search calibrations" placeholder="Find a sensor, serial number or comment…" value="${esc(C.search)}"><select data-record-filter="calibration-type" aria-label="Calibration type">${[["all","All calibration types"],...types].map(([v,l])=>`<option value="${v}" ${v===C.type?"selected":""}>${esc(l)}</option>`).join("")}</select>${button(C.archived?"Show active records":"Show archived records","records-calibration-archives")}</div><p class="small muted">${rows.length} records · Dates are recorded as local calendar dates. A log records the work; update instrument installations separately under Site reference → Instrument deployments.</p></section><div class="record-list">${rows.map(r=>`<article class="panel calibration-card"><div class="panel-title"><div><span class="eyebrow">${day(r.event_date)}</span><h3>${esc(r.sensor_name)}</h3></div><div>${pillType(r.event_type)} ${r.pending?'<span class="offline-tag">Pending sync</span>':""}${r.is_archived?'<span class="pill archived">Archived</span>':""}</div></div><dl class="record-facts"><div><dt>${r.event_type==="swap"?"Removed sensor":"Sensor"}</dt><dd>${esc([r.sensor_model,r.serial_number].filter(Boolean).join(" · ")||"Serial / model not recorded")}</dd></div>${r.event_type==="swap"?`<div><dt>Installed replacement</dt><dd>${esc([r.replacement_description,r.replacement_serial_number].filter(Boolean).join(" · ")||(S.data.equipment.find(e=>e.id===r.replacement_equipment)?.instrument||"Inventory instrument"))}<br><span class="small muted">${esc(label(preparations,r.preparation))}</span></dd></div>`:""}${[["Lab calibrated",r.lab_calibrated_on?day(r.lab_calibrated_on):""],["Next calibration due",r.next_due_on?day(r.next_due_on):""],["Performed by",r.performed_by],["Laboratory",r.laboratory],["Certificate / reference",r.reference]].filter(([,v])=>v).map(([k,v])=>`<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>${r.notes?text(r.notes):""}${r.source_visit?`<p class="small muted">Linked visit: ${esc(S.data.visits.find(v=>v.id===r.source_visit)?.title||"Field visit")}</p>${button("Open source visit","site-visit",r.source_visit)}`:""}${attachmentsHTML({calibration:r.id})}<div class="row-actions section-divider">${siteWritable()?button("Edit record","records-calibration-edit",r.id)+(r.is_archived?button("Restore","records-calibration-restore",r.id):button("Attach calibration file","records-calibration-upload",r.id)+button("Archive","records-calibration-archive",r.id)):""}</div></article>`).join("")||empty(C.archived?"No archived calibrations":"No calibration records match","Record the sensors exchanged during a visit, or add historical lab and on-site calibrations.")}</div>`;
  }
  const pillType=type=>`<span class="pill calibration-${esc(type)}">${esc(label(types,type))}</span>`;
  function calibrationForm(record,visitId){
    if(!siteWritable())throw new Error("This site is read-only.");
    const r=record||{event_date:today(),event_type:"swap",preparation:"cleaned_calibrated",source_visit:visitId||"",performed_by:S.me.name};
    const id=r.id||uuid();
    const swapFields=()=>`${field("replacement_equipment","Replacement inventory instrument",r.replacement_equipment||"",{options:equipmentOptions(r.replacement_equipment)})}${field("replacement_serial_number","Replacement serial number",r.replacement_serial_number)}${field("replacement_description","Replacement model / description",r.replacement_description,{wide:true,help:"Identify the installed sensor with a serial number, description or inventory link."})}${field("preparation","Replacement preparation",r.preparation||"cleaned_calibrated",{options:preparations})}`;
    openForm(record?"Edit calibration record":"Record calibration / sensor swap",`<p class="small muted">Use Sensor swap when a prepared instrument replaces the one at the tower. Leave unknown serial numbers and dates blank, and explain the uncertainty in the comments.</p><div class="form-grid">${field("event_type","Work type",r.event_type,{options:types})}${field("event_date","Work date",r.event_date,{type:"date",required:true})}${field("sensor_name","Sensor / measured variable",r.sensor_name,{required:true})}${field("sensor_model","Sensor model",r.sensor_model)}${field("equipment","Serviced / removed inventory instrument",r.equipment||"",{options:equipmentOptions(r.equipment)})}${field("serial_number","Serviced / removed serial number",r.serial_number)}<fieldset class="wide calibration-replacement" id="replacement-fields" ${r.event_type!=="swap"?"hidden disabled":""}><legend>Installed replacement</legend><div class="form-grid">${swapFields()}</div></fieldset>${field("lab_calibrated_on","Lab calibration date",r.lab_calibrated_on||"",{type:"date",help:"For swaps, this is the replacement sensor's calibration date."})}${field("next_due_on","Next calibration due (optional)",r.next_due_on||"",{type:"date"})}${field("performed_by","Work performed by",r.performed_by)}${field("laboratory","Laboratory / calibration provider",r.laboratory)}${field("reference","Certificate / reference number",r.reference,{wide:true})}${field("source_visit","Linked field visit",r.source_visit||"",{options:[["","No linked visit"],...(S.data.visits||[]).map(v=>[v.id,`${v.date} · ${v.title||v.crew}`])],wide:true})}${field("notes","Comments, checks and sensor details",r.notes,{type:"textarea",wide:true})}${noteFileField()}</div>`,async form=>{
      const data=values(form);
      for(const key of ["equipment","replacement_equipment","source_visit"])data[key]=data[key]?key==="source_visit"?data[key]:Number(data[key]):null;
      for(const key of ["lab_calibrated_on","next_due_on"])data[key]=data[key]||null;
      if(data.event_type!=="swap")Object.assign(data,{replacement_equipment:null,replacement_serial_number:"",replacement_description:"",preparation:""});
      if(data.event_type==="swap"&&!data.replacement_equipment&&!data.replacement_serial_number.trim()&&!data.replacement_description.trim())throw new Error("Identify the replacement instrument with a description, serial number or inventory link.");
      if(data.event_type==="swap"&&((data.equipment&&data.equipment===data.replacement_equipment)||(data.serial_number&&data.serial_number.trim().toLowerCase()===data.replacement_serial_number.trim().toLowerCase())))throw new Error("The removed and replacement sensors must be different instruments.");
      if(data.lab_calibrated_on&&data.lab_calibrated_on>data.event_date)throw new Error("Lab calibration must be on or before the work date.");
      if(data.next_due_on&&data.next_due_on<data.event_date)throw new Error("The next calibration date must be on or after the work date.");
      await enqueue(record?"calibration.edit":"calibration.create",id,data,record?.version,noteFiles(form));
    });
    for(const [name,prefix] of [["equipment",""],["replacement_equipment","replacement_"]])document.querySelector(`#dialog [name="${name}"]`).onchange=event=>{const instrument=S.data.equipment.find(e=>e.id===Number(event.target.value));if(!instrument)return;const serial=document.querySelector(`#dialog [name="${prefix}serial_number"]`);if(!serial.value)serial.value=instrument.serial_number||"";const description=document.querySelector(`#dialog [name="${prefix?"replacement_description":"sensor_model"}"]`);if(!description.value)description.value=instrument.model_number||instrument.instrument;};
    document.querySelector('#dialog [name="event_type"]').onchange=event=>{const f=document.getElementById("replacement-fields");f.hidden=f.disabled=event.target.value!=="swap";};
  }
  function knowledgeFiles(item,archived=false){
    const files=(item.files||[]).filter(f=>f.is_archived===archived);
    return files.length?`<div class="knowledge-files">${files.map(f=>`<div class="knowledge-file">${!archived&&f.content_type.startsWith("image/")?`<img loading="lazy" src="${esc(f.url)}" alt="${esc(f.filename)}">`:""}<div><strong>${esc(f.filename)}</strong><span class="small muted">${(f.size/1024).toFixed(1)} KB${f.is_archived?" · Archived":""}</span><div class="row-actions">${f.content_type==="application/pdf"?button("Read PDF","records-file-read",f.id):""}<a class="button secondary small" href="${esc(f.url)}" download>Download</a>${canEdit(item)?button(archived?"Restore file":"Archive file",archived?"records-file-restore":"records-file-archive",f.id):""}</div></div></div>`).join("")}</div>`:"";
  }
  function knowledgeView(){
    const rows=entries().filter(r=>r.is_archived===K.archived&&(K.scope==="all"||K.scope==="shared"?K.scope==="all"||!r.site:!r.site||r.site===S.siteId)&&(K.category==="all"||r.category===K.category)&&[r.title,r.body,r.category_label,...(r.files||[]).map(f=>f.filename)].join(" ").toLowerCase().includes(S.filter.toLowerCase()));
    return header("Reference library","Tower documents, wiring, troubleshooting, repairs and shared notebooks.",write()?button("＋ Add reference","records-knowledge-new","","primary"):"")+`<div class="toolbar"><input data-search="knowledge" aria-label="Search references" placeholder="Find a document, repair or wiring note…" value="${esc(S.filter)}"><select data-record-filter="knowledge-scope" aria-label="Reference scope">${[["site","Selected site + shared"],["shared","Shared network references"],["all","All accessible sites"]].map(([v,l])=>`<option value="${v}" ${K.scope===v?"selected":""}>${l}</option>`).join("")}</select><select data-record-filter="knowledge-category" aria-label="Reference category">${[["all","All categories"],...categories].map(([v,l])=>`<option value="${v}" ${K.category===v?"selected":""}>${l}</option>`).join("")}</select>${button(K.archived?"Show active references":"Show archived references","records-knowledge-archives")}</div><p class="small muted">${rows.length} references · Operational procedures belong in Protocols. Reference files and notebook links require a connection.</p><div class="reference-grid">${rows.map(r=>`<article class="panel reference-card"><div class="panel-title"><span class="eyebrow">${esc(r.site_code||"Shared network")}</span><span class="pill">${esc(label(categories,r.category))}</span></div><h2>${esc(r.title)}</h2>${r.body?text(r.body):""}${r.external_url?`<a class="button secondary small notebook-link" href="${esc(r.external_url)}" target="_blank" rel="noopener noreferrer">Open linked document ↗</a>`:""}${knowledgeFiles(r)}${(r.files||[]).some(f=>f.is_archived)?`<details class="section-divider"><summary>Archived files</summary>${knowledgeFiles(r,true)}</details>`:""}<p class="small muted">Updated ${time(r.updated_at)}</p>${canEdit(r)?`<div class="row-actions section-divider">${button("Edit reference","records-knowledge-edit",r.id)}${r.is_archived?button("Restore","records-knowledge-restore",r.id):button("Add files","records-knowledge-upload",r.id)+button("Archive","records-knowledge-archive",r.id)}</div>`:""}</article>`).join("")||empty("No references match","Keep hardware manuals, wiring diagrams, troubleshooting notes and OneNote sharing links here.")}</div>`;
  }
  async function uploadKnowledge(id,files){
    if(!files.length)return;
    if(files.length>10||files.reduce((n,f)=>n+f.size,0)>25*1024*1024)throw new Error("Select up to 10 files, totaling no more than 25 MB.");
    const form=new FormData();for(const f of files)form.append("files",f,f.name);
    return api(`/api/knowledge/${id}/files/`,{method:"POST",form});
  }
  function knowledgeForm(record){
    onlineOnly();
    let saved=record;
    const r=record||{site:S.siteId,category:"general"};
    const scopeOptions=[...(S.me.can_edit_shared_references===true?[["","Shared network"]]:[]),...S.sites.filter(s=>!s.is_archived).map(s=>[s.id,`${s.code} · ${s.name}`])];
    openForm(record?"Edit reference":"Add technical reference",`<div class="form-grid">${field("title","Title",r.title,{required:true,wide:true})}${field("site","Site / scope",r.site||"",{options:scopeOptions})}${field("category","Category",r.category,{options:categories})}${field("body","Notes, instructions and troubleshooting",r.body,{type:"textarea",wide:true})}${field("external_url","Document or OneNote web sharing link",r.external_url,{type:"url",wide:true,help:"Paste the notebook's HTTP(S) sharing link. The original service controls who can open it."})}${filesField()}</div>`,async form=>{
      onlineOnly();const data=values(form);data.site=data.site?Number(data.site):null;
      const files=noteFiles(form);if(files.length>10||files.reduce((n,f)=>n+f.size,0)>25*1024*1024)throw new Error("Select up to 10 files, totaling no more than 25 MB.");
      if(data.external_url){const url=new URL(data.external_url);if(!["http:","https:"].includes(url.protocol)||url.username||url.password)throw new Error("Use an HTTP(S) sharing link without embedded credentials.");}
      await refreshCsrf();saved=await api(`/api/knowledge/${saved?saved.id+"/":""}`,{method:saved?"PATCH":"POST",data:{...data,...(saved?{base_version:saved.version}:{})}});
      try{await uploadKnowledge(saved.id,files);}catch(error){await refreshWorkspace();throw new Error(`The reference was saved. Its files still need uploading: ${error.message} Retry Save to upload them.`);}
      await refreshWorkspace();await loadKnowledge();toast("Reference saved.");
    });
  }
  async function changeArchive(item,archived){
    onlineOnly();await refreshCsrf();await api(`/api/knowledge/${item.id}/`,{method:"PATCH",data:{is_archived:archived,base_version:item.version}});await refreshWorkspace();await loadKnowledge();toast(archived?"Reference archived; its files remain in history.":"Reference restored.");
  }
  async function action(name,id){
    if(!name.startsWith("records-"))return false;
    const calibration=(S.data?.calibrations||[]).find(r=>r.id===id);
    switch(name){
      case "records-calibration-new":calibrationForm(null,id);break;
      case "records-calibration-edit":calibrationForm(calibration);break;
      case "records-calibration-upload":uploadForm({calibration:id});break;
      case "records-calibration-archives":C.archived=!C.archived;render();break;
      case "records-calibration-archive":case "records-calibration-restore":openForm(name.endsWith("restore")?"Restore calibration record?":"Archive calibration record?","<p>The record and its files remain in the site's calibration history.</p>",()=>enqueue("calibration.edit",id,{is_archived:name.endsWith("archive")},calibration.version));break;
      case "records-knowledge-new":knowledgeForm();break;
      case "records-knowledge-edit":knowledgeForm(entry(id));break;
      case "records-knowledge-archives":K.archived=!K.archived;render();break;
      case "records-knowledge-upload":onlineOnly();openForm("Add reference files",filesField(),async form=>{await refreshCsrf();const files=noteFiles(form);if(!files.length)throw new Error("Select a file to upload.");await uploadKnowledge(id,files);await refreshWorkspace();await loadKnowledge();toast("Reference files saved.");});break;
      case "records-knowledge-archive":case "records-knowledge-restore":openForm(name.endsWith("restore")?"Restore reference?":"Archive reference?","<p>Archived references remain available in the library's history.</p>",()=>changeArchive(entry(id),name.endsWith("archive")));break;
      case "records-file-read":{
        onlineOnly();const file=entries().flatMap(r=>r.files||[]).find(f=>f.id===id);openForm(file.filename,'<div class="pdf-viewer" id="reference-pdf">Loading document…</div>',null);
        const container=document.getElementById("reference-pdf");const response=await privateFetch(file.url);if(!response.ok)throw new Error("The document could not be opened. Sign in or refresh the library.");
        const data=new Uint8Array(await response.arrayBuffer());if(!container.isConnected)break;
        const destroy=await showPDF(container,data);document.getElementById("dialog").addEventListener("close",destroy,{once:true});break;
      }
      case "records-file-archive":case "records-file-restore":{
        onlineOnly();const parent=entries().find(r=>r.files.some(f=>f.id===id));const file=parent.files.find(f=>f.id===id);
        openForm(name.endsWith("restore")?"Restore file?":"Archive file?",`<p>${esc(file.filename)} will remain in the reference history.</p>`,async()=>{await refreshCsrf();await api(`/api/knowledge/${parent.id}/files/${id}/`,{method:"PATCH",data:{is_archived:name.endsWith("archive"),base_version:file.version}});await refreshWorkspace();await loadKnowledge();});break;
      }
      default:return false;
    }
    return true;
  }
  document.addEventListener("input",event=>{if(event.target.dataset.recordSearch!=="calibrations")return;C.search=event.target.value;const start=event.target.selectionStart;render();const input=document.querySelector('[data-record-search="calibrations"]');input?.focus();input?.setSelectionRange(start,start);});
  document.addEventListener("change",event=>{const key=event.target.dataset.recordFilter;if(!key)return;const value=event.target.value;if(key==="calibration-type")C.type=value;if(key==="knowledge-scope")K.scope=value;if(key==="knowledge-category")K.category=value;render();});
  return {calibrationsView,knowledgeView,loadKnowledge,action};
}
