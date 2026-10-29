/* Pure projections keep pending work and durable acknowledgements consistent. */
export function projectSnapshot(base, queue, actor, siteId) {
  const data=structuredClone(base);
  data.calibrations ||= []; data.knowledge ||= [];
  for (const item of queue.filter(q=>q.siteId===siteId||(q.kind==="upload"&&q.fields.equipment&&data.equipment.some(e=>e.id===Number(q.fields.equipment))))) {
    if (item.kind === "upload") { data.attachments.push({id:item.id,visit:item.fields.visit||null,equipment:item.fields.equipment||null,caveat:item.fields.caveat||null,configuration:item.fields.configuration||null,task:item.fields.task||null,activity:item.fields.activity||null,observation:item.fields.observation||null,calibration:item.fields.calibration||null,filename:item.file.name,caption:item.fields.caption,content_type:item.file.type,url:"",pending:true}); continue; }
    const op=item.operation,p=op.payload,t=data.tasks.find(t=>t.id===op.entity_id),v=data.visits.find(v=>v.id===op.entity_id);
    const visitId=p.visit_id||null;
    if (op.kind === "visit.create") data.visits.unshift({id:op.entity_id,site:siteId,date:p.date,crew:p.crew,title:p.title,classification:p.classification||"routine",status:"open",started_at:op.occurred_at,version:1,reports:[],narrative:"",pending:true});
    else if (op.kind.startsWith("visit.") && v) { if (op.kind==="visit.close") {v.status="closed";v.ended_at=op.occurred_at;} else if(op.kind==="visit.reopen")v.status="open"; else if(op.kind==="visit.edit")Object.assign(v,p); v.version++;v.pending=true; }
    else if(op.kind==="observation.create") data.observations.push({id:op.entity_id,visit:visitId,text:p.text,author_name:actor.name,occurred_at:op.occurred_at,pending:true});
    else if(op.kind==="task.create") { const newTask={id:op.entity_id,site:siteId,title:p.title,details:p.details||"",priority:p.priority||"normal",status:"pending",due_date:p.due_date||null,created_visit:visitId,created_by:actor.id,created_at:op.occurred_at,version:1,pending:true};data.tasks.push(newTask);data.activities.push({id:p.activity_id||op.id,task:op.entity_id,visit:visitId,action:"created",task_title:p.title,text:p.text||"",author_name:actor.name,occurred_at:op.occurred_at,pending:true}); }
    else if(op.kind.startsWith("task.") && t) { const action={"task.complete":"completed","task.reopen":"reopened","task.comment":"commented","task.edit":"edited","task.archive":"archived"}[op.kind];if(op.kind==="task.complete")t.status="done";if(op.kind==="task.reopen")t.status="pending";if(op.kind==="task.archive")t.status="archived";if(op.kind==="task.edit")Object.assign(t,p);if(op.kind!=="task.comment")t.version++;t.pending=true;data.activities.push({id:p.activity_id||op.id,task:t.id,visit:visitId,action,task_title:t.title,text:p.text||"",author_name:actor.name,occurred_at:op.occurred_at,pending:true}); }
    else if(op.kind==="calibration.create")data.calibrations.unshift({...p,id:op.entity_id,site:siteId,version:1,is_archived:false,pending:true});
    else if(op.kind==="calibration.edit"){const record=data.calibrations.find(r=>r.id===op.entity_id);if(record){Object.assign(record,p);record.version++;record.pending=true;}}
    else if(op.kind==="caveat.draft")data.caveats.push({id:op.entity_id,sites:[siteId],title:p.title,description:p.description,variables:p.variables,period_label:p.period_label,status:"draft",treatment:"",version:1,pending:true});
  }
  return data;
}
const lists={task:"tasks",visit:"visits",observation:"observations",caveat:"caveats",calibration:"calibrations"};
function upsert(rows,record){const i=rows.findIndex(row=>String(row.id)===String(record.id));if(i<0)rows.push(record);else rows[i]=record;}
export function mergeAcknowledgement(base,item,result,actor){
  const data=projectSnapshot(base,[item],actor,item.siteId);
  if(item.kind==="upload")upsert(data.attachments,result);
  else{
    const kind=item.operation.kind.split(".")[0],list=lists[kind];
    if(result.record&&list)upsert(data[list],result.record);
    if(result.activity)upsert(data.activities,result.activity);
  }
  // Old receipts can omit complete records. Retain their optimistic values as
  // acknowledged until the next authoritative snapshot, without a pending tag.
  for(const list of [...Object.values(lists),"activities","attachments"]){
    for(const row of data[list]||[])delete row.pending;
  }
  return data;
}
export function protocolCacheKey(account,protocol){
  return `${account}:${protocol.url}:revision:${protocol.sha256||protocol.version}`;
}
