export function createProcessingFiles({data,site,canWrite,openForm,api,refreshCsrf,refreshWorkspace,render,esc,button,empty,toast,onlineOnly}) {
  let scope='all';
  const documents=()=>data()?.processing_files||[];
  function view(){
    const files=documents().filter(file=>scope==='all'||!file.site_code||file.site===site()?.id);
    return `<section class="panel" style="margin:20px 0"><div class="panel-title"><div><h2>TraceAnalysis INI library</h2><p class="small muted">Current files and their original bytes. Uploads create versions; earlier copies stay available. Files are never executed by the app.</p></div>${canWrite()?button('Upload INI files','processing-upload','','primary'):''}</div><div class="row-actions">${button('All accessible files','processing-scope','all',scope==='all'?'primary small':'secondary small')}${button('This site & shared files','processing-scope','site',scope==='site'?'primary small':'secondary small')}</div><div class="table-wrap"><table><thead><tr><th>File</th><th>Station</th><th>Latest</th><th>Actions</th></tr></thead><tbody>${files.map(file=>{const latest=file.latest;return `<tr><td><strong>${esc(file.path)}</strong>${latest?.source_modified_at?`<span class="small muted">Source modified ${esc(new Date(latest.source_modified_at).toLocaleString())}</span>`:''}</td><td>${esc(file.site_code||'Shared include')}${file.site_code&&!file.site?' · unassigned':''}</td><td>${latest?`v${latest.revision}<span class="small muted">${Math.ceil(latest.size/1024)} KiB · ${esc(new Date(latest.uploaded_at).toLocaleDateString())}</span>`:'No version'}</td><td><div class="row-actions">${latest?`<a class="button secondary small" href="${esc(latest.url)}">Download</a>${button('Read','processing-read',latest.id)}`:''}${button('Versions','processing-history',file.id)}</div></td></tr>`;}).join('')}</tbody></table>${files.length?'':empty('No INI files here yet','Upload files or import the supplied source snapshot.')}</div></section>`;
  }
  function upload(){
    let dropped=[];
    openForm('Upload INI versions',`<p>Select files, choose a folder, or drop .ini files below. Site prefixes keep the existing station folders. Changed files create a new revision; identical latest copies are skipped.</p><div id="ini-drop-zone" class="ini-drop-zone" tabindex="0"><strong>Drop INI files here</strong><p id="ini-drop-count" class="small muted">No dropped files</p></div><label>Choose files<input type="file" name="files" multiple accept=".ini"></label><label>Or choose a folder<input type="file" name="folder" webkitdirectory multiple></label><label>Version note (optional)<textarea name="note" maxlength="500"></textarea></label><p class="small muted">Up to 100 files; 5 MiB per file and 25 MiB per batch. This stores a copy and does not change your source files.</p>`,async form=>{
      onlineOnly();
      const selected=[...dropped,...form.getAll('files'),...form.getAll('folder')].filter(file=>file instanceof File&&file.size&&file.name.toLowerCase().endsWith('.ini'));
      const unique=[...new Map(selected.map(file=>[file.webkitRelativePath||file.name,file])).values()];
      if(!unique.length)throw new Error('Select at least one .ini file.');
      const payload=new FormData();
      unique.forEach(file=>payload.append('files',file,file.name));
      payload.append('paths',JSON.stringify(unique.map(file=>file.webkitRelativePath||file.name)));
      payload.append('note',form.get('note')||'');
      await refreshCsrf();
      const result=await api('/api/processing-files/',{method:'POST',form:payload});
      await refreshWorkspace();toast(`${result.created} new versions; ${result.unchanged} unchanged files.`);
    },'Upload versions');
    const zone=document.getElementById('ini-drop-zone');
    zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('dragging');});
    zone.addEventListener('dragleave',()=>zone.classList.remove('dragging'));
    zone.addEventListener('drop',event=>{event.preventDefault();zone.classList.remove('dragging');dropped=[...event.dataTransfer.files].filter(file=>file.name.toLowerCase().endsWith('.ini'));document.getElementById('ini-drop-count').textContent=`${dropped.length} INI files selected`;});
  }
  async function action(name,id){
    if(name==='processing-upload'){onlineOnly();upload();return true;}
    if(name==='processing-scope'){scope=id;render();return true;}
    if(name==='processing-history'){
      const file=documents().find(file=>file.id===id);if(!file)throw new Error('Refresh the file library first.');
      openForm('INI version history',`<h3>${esc(file.path)}</h3>${file.versions.map(version=>`<section class="section-divider"><strong>Version ${version.revision}${version.id===file.latest?.id?' · Latest':''}</strong><p class="small muted">${esc(new Date(version.uploaded_at).toLocaleString())} · ${version.size} bytes</p><p>${esc(version.note)}</p><code class="small">SHA-256 ${esc(version.sha256)}</code><div class="row-actions"><a class="button secondary small" href="${esc(version.url)}">Download this version</a>${button('Read','processing-read',version.id)}</div></section>`).join('')}`,null);return true;
    }
    if(name==='processing-read'){
      onlineOnly();let version;
      for(const file of documents()){version=file.versions.find(version=>version.id===id);if(version)break;}
      if(!version)throw new Error('Refresh the file library first.');
      const content=await api(version.url+'?preview=1');
      document.getElementById('dialog').close();
      openForm(`INI · version ${content.revision}`,`<h3>${esc(content.path)}</h3><pre class="report">${esc(content.text)}</pre>`,null);return true;
    }
    return false;
  }
  return {view,action};
}
