import {mergeAcknowledgement} from "./offline-state.js";
const DB_NAME="carbonique-hub-v1";
let opening,owner;
function database(){
  if(!opening)opening=new Promise((resolve,reject)=>{
    const request=indexedDB.open(DB_NAME,1);
    request.onupgradeneeded=()=>{for(const name of ["meta","snapshots","outbox","downloads"])request.result.createObjectStore(name);};
    request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
  });
  return opening;
}
export function bindAccount(account,session){owner={account:Number(account),session:session||null};}
const stale=()=>new Error("This saved workspace belongs to another or signed-out session. Reload and sign in again. Pending work is preserved.");
function checkOwner(tx,identity,ready,fail){
  if(!identity){ready();return;}
  const meta=tx.objectStore("meta"),values={};let left=3;
  for(const [name,key] of [["session",`${identity.account}:session`],["sealed",`${identity.account}:sealed`],["active","active-account"]]){
    const request=meta.get(key);request.onsuccess=()=>{values[name]=request.result;if(--left===0){
      if(values.sealed||Number(values.active)!==identity.account||(values.session||null)!==identity.session){fail(stale());return;}
      ready();
    }};
  }
}
async function transact(name,mode,callback){
  const db=await database(),identity=owner?{...owner}:null;
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(mode==="readwrite"?[...new Set([name,"meta"])]:name,mode);let result,error;
    const fail=e=>{error=e;tx.abort();};
    const run=()=>{try{const request=callback(tx.objectStore(name));if(request)request.onsuccess=()=>{result=request.result;};}catch(e){fail(e);}};
    tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(error||tx.error);tx.onabort=()=>reject(error||tx.error||new Error("Local storage transaction aborted."));
    if(mode==="readwrite")checkOwner(tx,identity,run,fail);else run();
  });
}
export const get=(name,key)=>transact(name,"readonly",s=>s.get(key));
export const put=(name,key,value)=>transact(name,"readwrite",s=>s.put(value,key));
export const putMany=(name,entries)=>transact(name,"readwrite",s=>{for(const [key,value] of entries)s.put(value,key);});
export const remove=(name,key)=>transact(name,"readwrite",s=>s.delete(key));
export const all=name=>transact(name,"readonly",s=>s.getAll());
export async function activateAccount(account,session){
  account=Number(account);session=session||null;
  const db=await database();
  await new Promise((resolve,reject)=>{
    const tx=db.transaction("meta","readwrite"),meta=tx.objectStore("meta");let error;
    const request=meta.get(`${account}:sealed`);
    request.onsuccess=()=>{
      if(request.result&&request.result.session===session){error=stale();tx.abort();return;}
      meta.delete(`${account}:sealed`);meta.put(session,`${account}:session`);meta.put(account,"active-account");
    };
    tx.oncomplete=resolve;tx.onerror=()=>reject(error||tx.error);tx.onabort=()=>reject(error||tx.error);
  });
  bindAccount(account,session);
}
export async function saveSnapshot(account,siteId,data,revision){
  const db=await database(),identity=owner?{...owner}:null;
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(["meta","snapshots"],"readwrite");let error,saved=false;
    const fail=e=>{error=e;tx.abort();};tx.oncomplete=()=>resolve(saved);tx.onerror=()=>reject(error||tx.error);tx.onabort=()=>reject(error||tx.error);
    checkOwner(tx,identity,()=>{
      const request=tx.objectStore("meta").get(`${account}:snapshot-revision:${siteId}`);
      request.onsuccess=()=>{if((request.result||0)!==revision)return;tx.objectStore("snapshots").put(data,`${account}:${siteId}`);saved=true;};
    },fail);
  });
}
export async function acknowledge(item,result,actor){
  const db=await database(),identity=owner?{...owner}:null;
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(["meta","snapshots","outbox"],"readwrite");let error;
    const fail=e=>{error=e;tx.abort();};
    tx.oncomplete=resolve;tx.onerror=()=>reject(error||tx.error);tx.onabort=()=>reject(error||tx.error);
    checkOwner(tx,identity,()=>{
      if(identity&&item.account!==identity.account){fail(stale());return;}
      const snapshots=tx.objectStore("snapshots"),key=`${item.account}:${item.siteId}`,request=snapshots.get(key);
      request.onsuccess=()=>{
        if(!request.result){fail(new Error("Refresh this site's saved copy before retrying synchronization. The operation remains queued."));return;}
        try{
          snapshots.put(mergeAcknowledgement(request.result,item,result,actor),key);
          const revisionKey=`${item.account}:snapshot-revision:${item.siteId}`,revision=tx.objectStore("meta").get(revisionKey);
          revision.onsuccess=()=>tx.objectStore("meta").put((revision.result||0)+1,revisionKey);
          tx.objectStore("outbox").delete(item.id);
        }catch(e){fail(e);}
      };
    },fail);
  });
}
export async function clearAccount(account,session){
  account=Number(account);
  const db=await database();
  await new Promise((resolve,reject)=>{
    const tx=db.transaction(["meta","snapshots","outbox","downloads"],"readwrite");let error;
    const fail=e=>{error=e;tx.abort();};
    tx.oncomplete=resolve;tx.onerror=()=>reject(error||tx.error);tx.onabort=()=>reject(error||tx.error);
    checkOwner(tx,{account,session:session||null},()=>{
      const pending=tx.objectStore("outbox").getAll();pending.onsuccess=()=>{
        if(pending.result.some(item=>item.account===account)){fail(new Error("Sync or export and discard this account's pending records before signing out."));return;}
        for(const name of ["meta","snapshots","downloads"]){
          const cursor=tx.objectStore(name).openCursor();cursor.onsuccess=()=>{
            const row=cursor.result;if(!row)return;
            if(String(row.key).startsWith(`${account}:`)&&!([`${account}:sealed`,`${account}:session`].includes(row.key)))row.delete();
            row.continue();
          };
        }
        tx.objectStore("meta").put({session:session||null},`${account}:sealed`);
        // Other accounts' data and every outbox entry remain untouched.
      };
    },fail);
  });
}
