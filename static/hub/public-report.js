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
  document.getElementById('refresh-public')?.addEventListener('click',event => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = 'Refreshing…';
    location.reload();
  });
  const records = [...document.querySelectorAll('.record')];
  const site = document.getElementById('site-filter'), type = document.getElementById('type-filter'), search = document.getElementById('search');
  const timeline = setupTimeline();
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
    timeline?.update();
  }
  [site,type,search].forEach(control => control.addEventListener('input',filter)); filter();

  function setupTimeline() {
    const panel = document.getElementById('visit-timeline');
    if (!panel) return null;
    const plot = panel.querySelector('.timeline-plot');
    const rows = [...panel.querySelectorAll('.timeline-row')];
    const markers = [...panel.querySelectorAll('.marker')];
    const tooltip = document.getElementById('timeline-tooltip');
    const dateOf = marker => marker.dataset.date ? Date.parse(marker.dataset.date+'T12:00:00Z') : Infinity;
    const dates = markers.map(dateOf).filter(Number.isFinite);
    const first = new Date(Math.min(...dates)), last = new Date(Math.max(...dates));
    const start = Date.UTC(first.getUTCFullYear(), Math.floor(first.getUTCMonth()/3)*3, 1);
    const end = Date.UTC(last.getUTCFullYear(), Math.floor(last.getUTCMonth()/3)*3+3, 1);
    const position = date => 2+96*(date-start)/(end-start);
    const tickMonths = dates.length ? 3*Math.max(1,Math.ceil((last.getUTCFullYear()-first.getUTCFullYear())*4/48)) : 3;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const ticks = [];
    for (let date = new Date(start); date.getTime() <= end; date.setUTCMonth(date.getUTCMonth()+tickMonths)) {
      const tick = document.createElement('span');
      tick.className = 'timeline-tick';
      tick.style.left = position(date.getTime())+'%';
      tick.textContent = `${months[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
      panel.querySelector('.timeline-ticks').append(tick);
      ticks.push(tick);
    }
    document.getElementById('timeline-range').textContent = dates.length ? `${first.toISOString().slice(0,10)} → ${last.toISOString().slice(0,10)}` : 'Affected dates have not been recorded for these caveats.';
    for (const marker of markers) {
      if (marker.dataset.date) marker.style.left = position(dateOf(marker))+'%';
      // The native title is a fallback when scripting is unavailable.
      marker.removeAttribute('title');
    }
    for (const row of rows) {
      const grid = document.createElement('span');
      grid.className = 'timeline-grid'; grid.setAttribute('aria-hidden','true');
      for (const tick of ticks) {
        const line = document.createElement('i');
        line.style.left = tick.style.left; grid.append(line);
      }
      row.querySelector('.track').prepend(grid);
    }
    let activeMarker = null;
    function hideTooltip() {
      activeMarker?.removeAttribute('aria-describedby');
      activeMarker = null; tooltip.hidden = true;
    }
    function showTooltip(marker) {
      if (marker === activeMarker) return;
      hideTooltip(); activeMarker = marker;
      tooltip.dataset.kind = marker.dataset.kind;
      tooltip.dataset.status = marker.dataset.status;
      tooltip.querySelector('.timeline-tooltip-date').textContent = marker.dataset.date || 'Date unknown';
      tooltip.querySelector('.timeline-tooltip-kind').textContent = `${marker.dataset.site} · ${marker.dataset.label}`;
      tooltip.querySelector('.timeline-tooltip-title').textContent = marker.dataset.title;
      const detail = tooltip.querySelector('.timeline-tooltip-detail');
      detail.textContent = marker.dataset.detail; detail.hidden = !marker.dataset.detail;
      tooltip.hidden = false; marker.setAttribute('aria-describedby',tooltip.id);
      const rect = marker.getBoundingClientRect(), tip = tooltip.getBoundingClientRect();
      const left = Math.max(12, Math.min(rect.left+rect.width/2-tip.width/2, innerWidth-tip.width-12));
      let top = rect.bottom+10;
      if (top+tip.height > innerHeight-12) top = Math.max(12, rect.top-tip.height-10);
      tooltip.style.left = left+'px'; tooltip.style.top = top+'px';
    }
    panel.addEventListener('pointerover',event => {
      const marker = event.target.closest('.marker');
      if (marker) showTooltip(marker);
    });
    panel.addEventListener('pointerout',event => {
      const marker = event.target.closest('.marker');
      if (marker && !marker.contains(event.relatedTarget) && document.activeElement !== marker) hideTooltip();
    });
    panel.addEventListener('focusin',event => {
      const marker = event.target.closest('.marker');
      if (!marker) return;
      for (const sibling of marker.closest('.timeline-row').querySelectorAll('.marker')) sibling.tabIndex = sibling === marker ? 0 : -1;
      showTooltip(marker);
    });
    panel.addEventListener('focusout',event => {
      if (event.target === activeMarker) hideTooltip();
    });
    panel.addEventListener('keydown',event => {
      if (event.key === 'Escape') { hideTooltip(); return; }
      const marker = event.target.closest('.marker');
      if (!marker || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      const choices = [...marker.closest('.timeline-row').querySelectorAll('.marker')].filter(item => !item.hidden).sort((a,b) => dateOf(a)-dateOf(b));
      const current = choices.indexOf(marker);
      const next = {ArrowLeft:Math.max(0,current-1), ArrowRight:Math.min(choices.length-1,current+1), Home:0, End:choices.length-1}[event.key];
      event.preventDefault(); choices[next].focus();
    });
    panel.addEventListener('click',event => {
      const marker = event.target.closest('.marker');
      if (!marker || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const target = document.getElementById(marker.getAttribute('href').slice(1));
      if (!target) return;
      hideTooltip();
      target.classList.remove('timeline-highlight');
      requestAnimationFrame(() => target.classList.add('timeline-highlight'));
      setTimeout(() => target.classList.remove('timeline-highlight'),1800);
    });
    panel.addEventListener('toggle',() => { hideTooltip(); layout(); });
    window.addEventListener('scroll',hideTooltip,{passive:true});
    window.addEventListener('resize',hideTooltip);
    for (const tab of tabs) tab.addEventListener('click',hideTooltip);
    function layout() {
      const width = panel.querySelector('.timeline-ticks').clientWidth;
      if (!width) return;
      const stride = Math.max(1,Math.ceil(72*(ticks.length-1)/(width*.96)));
      let previous = -Infinity;
      ticks.forEach((tick,index) => {
        const x = parseFloat(tick.style.left)*width/100;
        const last = index === ticks.length-1;
        tick.hidden = !last && (index%stride !== 0 || (ticks.length-1-index)*width*.96/(ticks.length-1) < 72);
        if (!tick.hidden && x-previous < 60) tick.hidden = true;
        if (!tick.hidden) previous = x;
      });
      for (const row of rows) {
        const track = row.querySelector('.track');
        const laneEnds = [];
        const visible = [...track.querySelectorAll('.marker')].filter(marker => !marker.hidden).sort((a,b) => dateOf(a)-dateOf(b));
        for (const marker of visible) {
          const x = parseFloat(marker.style.left)*track.clientWidth/100;
          let lane = laneEnds.findIndex(last => x-last >= 18);
          if (lane < 0) lane = laneEnds.length;
          laneEnds[lane] = x; marker.style.top = (12+lane*12)+'px';
        }
        track.style.height = (Math.max(3,laneEnds.length)*12+8)+'px';
      }
    }
    new ResizeObserver(() => { hideTooltip(); layout(); }).observe(plot);
    function update() {
      hideTooltip();
      const visits = new Set(), caveats = new Set();
      for (const marker of markers) {
        const target = marker.getAttribute('href').slice(1);
        marker.hidden = !!document.getElementById(target)?.hidden || (!!site.value && marker.closest('.timeline-row').dataset.site !== site.value);
        if (!marker.hidden) (marker.dataset.recordKind === 'caveat' ? caveats : visits).add(target);
      }
      for (const row of rows) {
        row.hidden = !!site.value && row.dataset.site !== site.value;
        const visible = [...row.querySelectorAll('.marker')].filter(marker => !marker.hidden).sort((a,b) => dateOf(a)-dateOf(b));
        const selected = visible.find(marker => marker.tabIndex === 0) || visible[0];
        for (const marker of row.querySelectorAll('.marker')) marker.tabIndex = marker === selected ? 0 : -1;
      }
      const count = visits.size+caveats.size;
      plot.hidden = count === 0;
      panel.querySelector('.timeline-empty').hidden = count > 0;
      document.getElementById('timeline-count').textContent = `${visits.size} ${visits.size === 1 ? 'visit' : 'visits'} · ${caveats.size} ${caveats.size === 1 ? 'caveat' : 'caveats'}`;
      layout();
    }
    return {update};
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
