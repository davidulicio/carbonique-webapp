(() => {
  const tabs = [...document.querySelectorAll('[data-tab]')];
  function selectTab(tab) {
    for (const button of tabs) {
      const active = button === tab;
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
      document.getElementById(button.getAttribute('aria-controls')).hidden = !active;
    }
  }
  for (const [index, tab] of tabs.entries()) {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      const next = {ArrowRight:(index+1)%tabs.length, ArrowLeft:(index+tabs.length-1)%tabs.length, Home:0, End:tabs.length-1}[event.key];
      if (next === undefined) return;
      event.preventDefault(); selectTab(tabs[next]); tabs[next].focus();
    });
  }
  const records = [...document.querySelectorAll('.record')];
  const site = document.getElementById('site-filter'), type = document.getElementById('type-filter'), search = document.getElementById('search');
  function filter() {
    const query = search.value.trim().toLocaleLowerCase();
    let count = 0;
    for (const record of records) {
      const match = (!site.value || record.dataset.sites.trim().split(/\s+/).includes(site.value)) &&
        (!type.value || record.dataset.type === type.value || (type.value === 'caveat' && record.classList.contains('caveat'))) &&
        (!query || record.textContent.toLocaleLowerCase().includes(query));
      record.hidden = !match; if (match) count++;
    }
    document.getElementById('result-count').textContent = `${count} of ${records.length} records`;
    document.getElementById('no-results').hidden = count > 0 || records.length === 0;
    for (const group of document.querySelectorAll('.record-group')) {
      const children = [...group.querySelectorAll('.record')];
      group.hidden = children.length > 0 && children.every(record => record.hidden);
    }
  }
  [site,type,search].forEach(control => control.addEventListener('input',filter)); filter();
  const markers = [...document.querySelectorAll('.marker')];
  if (markers.length) {
    const dates = markers.map(marker => Date.parse(marker.dataset.date+'T12:00:00Z'));
    const start = Math.min(...dates), end = Math.max(...dates), span = end-start || 86400000;
    markers.forEach((marker,index) => marker.style.left = (2+96*(dates[index]-start)/span)+'%');
    document.getElementById('timeline-range').textContent = `${new Date(start).toISOString().slice(0,10)} → ${new Date(end).toISOString().slice(0,10)}`;
  }
  const lightbox = document.getElementById('lightbox');
  document.querySelectorAll('figure img').forEach(img => img.addEventListener('click', () => {
    lightbox.querySelector('img').src=img.src;lightbox.querySelector('img').alt=img.alt;lightbox.showModal();
  }));
  lightbox.querySelector('button').addEventListener('click',()=>lightbox.close());
  for (const button of document.querySelectorAll('.download-ini')) button.addEventListener('click', () => {
    const bytes=Uint8Array.from(atob(button.dataset.bytes),character=>character.charCodeAt(0));
    const blob = new Blob([bytes],{type:'application/octet-stream'});
    const url=URL.createObjectURL(blob), link=document.createElement('a');
    link.href=url;link.download=button.dataset.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),4000);
  });
  if (location.hash.startsWith('#site-') || location.hash === '#common-setup') {
    selectTab(document.getElementById('sites-tab'));
    document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }
})();
