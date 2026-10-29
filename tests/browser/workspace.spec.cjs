const {test,expect}=require('@playwright/test');
const password='Disposable-browser-password-2026';
test.beforeEach(async({page})=>{page._applicationErrors=[];page.on('pageerror',error=>page._applicationErrors.push(error.message));});
test.afterEach(async({page})=>{expect(page._applicationErrors).toEqual([]);});
async function login(page,username='browser-a'){
 await page.goto('/accounts/login/');await page.getByLabel('Username',{exact:true}).fill(username);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:/Sign in/}).click();
 await expect(page.locator('#main')).toHaveAttribute('data-site',/\d+/);
}
async function nav(page,name){if(await page.locator('#mobile-menu').isVisible())await page.locator('#mobile-menu').click();await page.getByRole('button',{name,exact:true}).click();}
async function addTask(page,title){await page.locator('[data-action="plan-task"]').click();await page.getByLabel('Task title',{exact:true}).fill(title);await page.locator('#dialog-save').click();await expect(page.locator('#dialog')).not.toBeVisible();}
async function saved(page,name){return page.evaluate(async name=>{const store=await import('/static/hub/storage.js');return store.all(name);},name);}
async function authWithCookies(context,user){const response=await context.request.get('/accounts/login/');const html=await response.text(),csrf=html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/)[1];const result=await context.request.post('/accounts/login/',{form:{username:user,password,csrfmiddlewaretoken:csrf},headers:{Referer:'http://127.0.0.1:8786/accounts/login/'}});expect(result.ok()).toBeTruthy();}
function pdf(label){const stream=`BT /F1 12 Tf 72 720 Td (${label}) Tj ET`,objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`];let data='%PDF-1.4\n',offsets=[0];objects.forEach((object,i)=>{offsets.push(Buffer.byteLength(data));data+=`${i+1} 0 obj\n${object}\nendobj\n`;});const at=Buffer.byteLength(data);data+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(x=>`${String(x).padStart(10,'0')} 00000 n \n`).join('')+`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${at}\n%%EOF\n`;return Buffer.from(data);}

test('site switching keeps the selected site and every stored snapshot aligned',async({page})=>{
 await login(page);await nav(page,'Field work');
 let held;const ready=new Promise(resolve=>held=resolve);let release;
 const gate=new Promise(resolve=>release=resolve);
 await page.route('**/api/snapshot/?site=2',async route=>{const response=await route.fetch();held();await gate;await route.fulfill({response});});
 await page.locator('#site-select').selectOption('2');await ready;
 await page.locator('#site-select').selectOption('1');await expect(page.locator('#main')).toHaveAttribute('data-site','1');release();
 await expect.poll(async()=>page.evaluate(async()=>{const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('carbonique-hub-v1',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});return new Promise(resolve=>{const tx=db.transaction('snapshots'),request=tx.objectStore('snapshots').openCursor();let ok=true;request.onsuccess=()=>{const row=request.result;if(!row)return resolve(ok);ok&&=Number(String(row.key).split(':').at(-1))===row.value.site.id;row.continue();};});})).toBe(true);
 await expect(page.locator('#main')).toHaveAttribute('data-site','1');
});
test('offline work survives partial synchronization and reload',async({page,context})=>{
 await login(page);await nav(page,'Field work');await context.setOffline(true);
 await addTask(page,'First acknowledged browser task');await addTask(page,'Second queued browser task');
 let count=0;await page.route('**/api/sync/',async route=>{if(++count===2)await route.fulfill({status:200,contentType:'application/json',headers:{'X-Workspace-Account':route.request().headers()['x-workspace-account'],'X-Workspace-Session':route.request().headers()['x-workspace-session']},body:JSON.stringify({results:[{ok:false,status:400,error:'Controlled validation failure'}]})});else await route.continue();});
 await context.setOffline(false);await expect(page.locator('#connection-label')).toHaveText('Sync needs review');
 await expect(page.getByRole('heading',{name:'First acknowledged browser task',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Second queued browser task',exact:true})).toBeVisible();
 const outbox=await saved(page,'outbox');expect(outbox).toHaveLength(1);expect(outbox[0].operation.payload.title).toBe('Second queued browser task');
 const snapshots=await saved(page,'snapshots');expect(snapshots.some(s=>s.tasks.some(t=>t.title==='First acknowledged browser task'&&!t.pending))).toBe(true);
 await page.reload();await expect(page.getByRole('heading',{name:'First acknowledged browser task',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Second queued browser task',exact:true})).toBeVisible();
});
test('another account signing out preserves the original account pending work',async({page,context})=>{
 await login(page);await nav(page,'Field work');await context.setOffline(true);await addTask(page,'Account A unsynchronized task');
 // Hold synchronization so the task remains pending while the shared cookie changes.
 await page.route('**/api/csrf/',route=>route.abort());await context.setOffline(false);
 const second=await context.newPage();await login(second,'browser-b');await expect(page.getByRole('heading',{name:'Workspace paused'})).toBeVisible();
 expect((await saved(second,'outbox')).some(item=>item.operation?.payload.title==='Account A unsynchronized task')).toBe(true);
 await second.locator('#logout-button').click();await second.locator('#dialog-save').click();await expect(second).toHaveURL(/accounts\/login/);
 const pending=await saved(second,'outbox');expect(pending.some(item=>item.operation?.payload.title==='Account A unsynchronized task')).toBe(true);
});
test('a changed cookie is rejected before an immediate online edit',async({page,context})=>{
 await login(page);await nav(page,'Reference library');await authWithCookies(context,'browser-b');
 await page.locator('[data-action="records-knowledge-new"]').click();await page.getByLabel('Title',{exact:true}).fill('Should not be saved by another account');await page.locator('#dialog-save').click();
 await expect(page.getByRole('heading',{name:'Workspace paused'})).toBeVisible();
 const response=await context.request.get('/api/knowledge/');expect(JSON.stringify(await response.json())).not.toContain('Should not be saved by another account');
});
test('protocol replacement renders and caches the new digest',async({page})=>{
 await login(page);await nav(page,'Protocols');await page.locator('[data-action="resource-protocol-read"]').click();await expect(page.locator('#protocol-viewer canvas')).toHaveCount(1);await page.locator('#dialog-close').click();
 await page.locator('[data-action="resource-protocol-edit"]').click();await page.getByLabel('Revision / effective date',{exact:true}).fill('Revision two');await page.locator('input[name="file"]').setInputFiles({name:'replacement.pdf',mimeType:'application/pdf',buffer:pdf('Protocol revision two')});await page.locator('#dialog-save').click();await expect(page.locator('#dialog')).not.toBeVisible();
 await page.locator('[data-action="resource-protocol-read"]').click();await expect(page.locator('#protocol-viewer canvas')).toHaveCount(1);await expect(page.locator('#dialog-body')).toContainText('Revision two');
 const content=await page.evaluate(async()=>{const store=await import('/static/hub/storage.js');return Promise.all((await store.all('downloads')).filter(value=>value instanceof Blob).map(value=>value.text()));});expect(content.some(text=>text.includes('Protocol revision two'))).toBe(true);
});
test('atomic account clearing refuses pending work and rejects later stale writes',async({page})=>{
 await login(page);const result=await page.evaluate(async()=>{
  const store=await import('/static/hub/storage.js'),bootstrap=await store.get('meta',`${await store.get('meta','active-account')}:bootstrap`),account=bootstrap.me.id,session=bootstrap.workspace_session;
  await store.put('outbox','pending-check',{id:'pending-check',account,siteId:1,kind:'operation',operation:{kind:'task.create',payload:{title:'Preserve me'}}});
  let refused=false;try{await store.clearAccount(account,session);}catch{refused=true;}
  const remains=!!(await store.get('outbox','pending-check'));await store.remove('outbox','pending-check');await store.clearAccount(account,session);
  let rejected=false;try{await store.put('outbox','late-write',{id:'late-write',account});}catch{rejected=true;}
  return {refused,remains,rejected,late:await store.get('outbox','late-write')};
 });expect(result).toEqual({refused:true,remains:true,rejected:true,late:undefined});
});
test('acknowledgements prevent older network responses overwriting local saved records',async({page})=>{
 await login(page);const result=await page.evaluate(async()=>{
  const store=await import('/static/hub/storage.js'),account=await store.get('meta','active-account'),key=`${account}:1`,before=await store.get('snapshots',key),revision=await store.get('meta',`${account}:snapshot-revision:1`)||0;
  const item={id:'ack-test',account,siteId:1,kind:'operation',operation:{id:'ack-test',entity_id:'ack-task',kind:'task.create',payload:{title:'Durable ack'}}};
  await store.put('outbox',item.id,item);await store.acknowledge(item,{record:{id:'ack-task',title:'Durable ack',version:1}}, {id:account,name:'Tester'});
  const replaced=await store.saveSnapshot(account,1,before,revision),after=await store.get('snapshots',key);return {replaced,exists:after.tasks.some(row=>row.id==='ack-task'),pending:!!await store.get('outbox',item.id)};
 });expect(result).toEqual({replaced:false,exists:true,pending:false});
});
test('phone navigation and queue recovery remain usable without horizontal overflow',async({page,context})=>{
 await page.setViewportSize({width:375,height:812});await login(page);await nav(page,'Field work');await context.setOffline(true);await addTask(page,'Phone pending recovery task');await page.locator('#mobile-menu').click();await page.locator('#queue-button').click();await expect(page.getByRole('heading',{name:'Synchronization queue'})).toBeVisible();
 const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Export pending record',exact:true}).click();const download=await downloadEvent;expect(download.suggestedFilename()).toBe('pending-operation.json');const stream=await download.createReadStream();let text='';for await(const chunk of stream)text+=chunk;expect(JSON.parse(text).payload.title).toBe('Phone pending recovery task');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);await expect.poll(async()=>{const rect=await page.locator('.sidebar').boundingBox();return rect.x+rect.width;}).toBeLessThanOrEqual(0);await page.screenshot({path:'test-results/phone-recovery.png'});await page.locator('#dialog-close').click();
});

test('prepared workspace reopens offline with its saved site and pending work',async({browser})=>{
 const context=await browser.newContext({baseURL:'http://127.0.0.1:8786',serviceWorkers:'allow'}),page=await context.newPage();
 try{
  await login(page);await page.locator('#prepare-button').click();await page.locator('input[name="files"]').uncheck();await page.locator('#dialog-save').click();await expect(page.locator('#dialog')).not.toBeVisible({timeout:30000});await expect(page.locator('#toast')).toContainText('saved for offline use');
  await nav(page,'Field work');await context.setOffline(true);await addTask(page,'Offline reopen task');await page.reload();
  await expect(page.getByRole('heading',{name:'Offline reopen task',exact:true})).toBeVisible();expect((await saved(page,'outbox')).some(item=>item.operation?.payload.title==='Offline reopen task')).toBe(true);
 }finally{await context.close();}
});
