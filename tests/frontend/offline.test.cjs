const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const {pathToFileURL}=require('node:url');const path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../../static/hub/app.js'),'utf8');
const part=(start,end)=>app.slice(app.indexOf(start),app.indexOf(end,app.indexOf(start)));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const base=id=>({site:{id,metadata:{}},tasks:[],visits:[],activities:[],observations:[],equipment:[],attachments:[],caveats:[],calibrations:[],knowledge:[]});
const modules=import(pathToFileURL(path.join(__dirname,'../../static/hub/offline-state.js')));
test('late site response cannot overwrite another site or cache key',async()=>{
 const {projectSnapshot}=await modules,pending=[],cache=new Map(),S={me:{id:7},siteId:1,sites:[{id:1},{id:2}],base:base(1),queue:[],loadGeneration:0,changeGeneration:0,identityGeneration:0};
 const scope={S,navigator:{onLine:true},identity:()=>({account:7,generation:0}),api:url=>new Promise(resolve=>pending.push({url,resolve})),store:{get:async(name,key)=>cache.get(name+':'+key),put:async(name,key,value)=>cache.set(name+':'+key,structuredClone(value)),saveSnapshot:async(account,site,data)=>{cache.set('snapshots:'+account+':'+site,data);return true;}},$:()=>({}),empty:()=>'',project:()=>{S.data=projectSnapshot(S.base,S.queue,S.me,S.siteId)},render:()=>{}};
 vm.createContext(scope);vm.runInContext(part('async function loadSite(','async function loadOverview('),scope);
 const first=scope.loadSite(1,false);await tick();const second=scope.loadSite(2,false);await tick();pending[1].resolve(base(2));await second;pending[0].resolve(base(1));await first;
 assert.equal(S.siteId,2);assert.equal(S.base.site.id,2);assert.equal(cache.get('snapshots:7:2').site.id,2);
});
test('partial synchronization keeps acknowledged records durably visible',async()=>{
 const {projectSnapshot,mergeAcknowledgement}=await modules;
 const item=(id,title,order)=>({id,account:7,siteId:1,order,kind:'operation',operation:{id,entity_id:id,kind:'task.create',payload:{title}}});
 const first=item('first','Saved task',1),second=item('second','Remaining task',2),outbox=new Map([[first.id,first],[second.id,second]]),cache=new Map([['7:1',base(1)]]);
 const S={me:{id:7,name:'Tester'},siteId:1,base:base(1),queue:[first,second],changeGeneration:0};let sent=0;
 const scope={S,navigator:{onLine:true},identity:()=>({account:7}),assertIdentity:()=>{},clone:structuredClone,projectSnapshot,store:{all:async()=>[...outbox.values()],get:async(name,key)=>cache.get(key),put:async(name,key,value)=>outbox.set(key,value),acknowledge:async(item,result,actor)=>{cache.set('7:1',mergeAcknowledgement(cache.get('7:1'),item,result,actor));outbox.delete(item.id);}},$:()=>({open:false}),updateConnection(){},render(){},toast(){},errorMessage:JSON.stringify,refreshCsrf:async()=>{},loadSite:async()=>{},loadOverview:async()=>{},api:async url=>url==='/api/bootstrap/'?{me:{id:7}}:{results:[++sent===1?{ok:true,record:{id:'first',site:1,title:'Saved task',version:1}}:{ok:false,status:400,error:'Validation error'}]}};
 vm.createContext(scope);vm.runInContext(part('async function readQueue()','let queueOrder='),scope);vm.runInContext(part('async function synchronize()','async function loadSite('),scope);await scope.synchronize();
 assert.equal(outbox.has('first'),false);assert.equal(cache.get('7:1').tasks[0].title,'Saved task');assert.equal(S.data.tasks.length,2);assert.equal(S.queue.length,1);assert.ok(S.blocked);
});
test('protocol replacements have distinct immutable cache keys',async()=>{const {protocolCacheKey}=await modules;assert.notEqual(protocolCacheKey(7,{url:'/guide/',sha256:'old'}),protocolCacheKey(7,{url:'/guide/',sha256:'new'}));});
test('acknowledged records use server versions and complete activity metadata',async()=>{const {mergeAcknowledgement}=await modules;const item={siteId:1,kind:'operation',operation:{id:'op',entity_id:'task',kind:'task.create',payload:{title:'Pending'}}};const data=mergeAcknowledgement(base(1),item,{record:{id:'task',title:'Saved',version:4},activity:{id:'op',task:'task',action:'created',author_name:'Server actor'}},{id:7,name:'Tester'});assert.equal(data.tasks[0].version,4);assert.equal(data.activities.length,1);assert.equal(data.activities[0].author_name,'Server actor');assert.equal(data.tasks[0].pending,undefined);});
