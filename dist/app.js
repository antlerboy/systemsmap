'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safe = (u) => /^https?:\/\//i.test(u || '') ? esc(u) : '#';
  const labels = {'systems':'Systems thinking','cybernetics':'Cybernetics','complexity':'Complexity','system-dynamics':'System dynamics','systemic-design':'Systemic design'};
  const formats = {'online':'Online','in-person':'In person','hybrid':'Hybrid','unknown':'Format not specified'};
  const localZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const dataBase = location.hostname==='antlerboy.github.io' ? './' : 'https://raw.githubusercontent.com/antlerboy/systemsmap/main/dist/';
  let events=[], sourceData=[], feeds=[], filtered=[], limit=30, map, pins, selectedId=null;
  const params = new URLSearchParams(location.search);
  const dateOnly = value => new Date(value.slice(0,10)+'T12:00:00Z');
  const today = () => {const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
  function zone(e) {let z=$('#timezone').value;return z==='local'?localZone:z==='source'?(e.timezone||'UTC'):z;}
  function formatter(e, opts) {try{return new Intl.DateTimeFormat('en-GB',{...opts,timeZone:e.allDay?'UTC':zone(e)});}catch{return new Intl.DateTimeFormat('en-GB',{...opts,timeZone:'UTC'});}}
  function when(e) {
    const start=e.allDay?dateOnly(e.start):new Date(e.start);
    const day=formatter(e,{day:'numeric',month:'short',year:'numeric'}).format(start);
    if(e.allDay){let end=e.end?dateOnly(e.end):null;if(end)end.setUTCDate(end.getUTCDate()-1);return day+(end&&end>start?' – '+formatter(e,{day:'numeric',month:'short',year:'numeric'}).format(end):'')+' · Times not published';}
    if(!e.calendarEligible)return e.start.replace('T',' ')+' · Time zone not published';
    const time=formatter(e,{hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(start);
    const end=e.end?new Date(e.end):null;
    if(end&&e.end.slice(0,10)!==e.start.slice(0,10))return `${day}, ${time} – ${formatter(e,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(end)}`;
    return `${day} · ${time}${end?' – '+formatter(e,{hour:'2-digit',minute:'2-digit'}).format(end):''}`;
  }
  function badge(e){return `<div class="badges"><span class="badge ${esc(e.format)}">${formats[e.format]||'Not specified'}</span>${e.status==='cancelled'?'<span class="badge warning">Cancelled</span>':''}${e.stale?'<span class="badge warning">Needs rechecking</span>':''}${e.notes.some(n=>n.includes('Title year'))?'<span class="badge warning">Check published date</span>':''}</div>`;}
  function card(e){
    const d=e.allDay?dateOnly(e.start):new Date(e.start);
    return `<article class="event-card" id="event-${esc(e.id)}"><div class="date-badge"><strong>${formatter(e,{day:'numeric'}).format(d)}</strong><span>${formatter(e,{month:'short'}).format(d)}</span></div><div><div class="org-name">${esc(e.organiser)}</div><h3><button data-event="${esc(e.id)}">${esc(e.title)}</button></h3><p class="event-meta">${esc(when(e))}</p><p class="event-meta">${esc(e.format==='online'?'Online · join from anywhere':e.location)}</p>${badge(e)}</div></article>`;
  }
  function match(e){
    const q=$('#q').value.trim().toLocaleLowerCase(), p=$('#period').value, org=$('#org').value, fmt=$('#format').value, country=$('#country').value, topic=$('#topics input:checked').value;
    const ends=e.end||e.start;
    if(p!=='all' && (e.allDay?ends.slice(0,10)<today():new Date(ends)<new Date()))return false;
    if(/^\d+$/.test(p) && dateOnly(e.start)>new Date(Date.now()+Number(p)*86400000))return false;
    return (!q||[e.title,e.description,e.organiser,e.location,e.country,e.language,...e.topics.map(t=>labels[t])].join(' ').toLocaleLowerCase().includes(q))&&(!org||e.organisationIds.includes(org))&&(!fmt||e.format===fmt)&&(!country||e.country===country)&&(!topic||e.topics.includes(topic));
  }
  function render(){
    filtered=events.filter(match);$('#count').textContent=`${filtered.length} event${filtered.length===1?'':'s'}`;
    $('#results').innerHTML=filtered.length?filtered.slice(0,limit).map(card).join(''):'<div class="empty"><strong>No events match these filters.</strong><p>Try a wider date range, another subject, or fewer filters. The sources register shows where coverage is still incomplete.</p><button class="secondary" data-reset>Clear filters</button></div>';
    $('#more').hidden=filtered.length<=limit;$('#export').disabled=!filtered.some(e=>e.calendarEligible);
    renderPins();saveFilters();
  }
  function saveFilters(){const p=new URLSearchParams();for(const key of ['q','period','org','format','country']){const v=$('#'+key).value;if(v&&!(key==='period'&&v==='upcoming'))p.set(key,v);}const t=$('#topics input:checked').value;if(t)p.set('topic',t);history.replaceState(null,'',location.pathname+(p.size?'?'+p:'')+location.hash);}
  function renderPins(){
    const located=filtered.filter(e=>['in-person','hybrid'].includes(e.format)&&Number.isFinite(Number(e.latitude))&&e.latitude!==null&&e.longitude!==null&&e.status!=='cancelled');
    $('#map-count').textContent=`${located.length} mapped event${located.length===1?'':'s'}`;
    $('#online-count').textContent=`${filtered.filter(e=>e.format==='online').length} online in the list`;
    if(!map||!pins)return;pins.clearLayers();const groups=new Map();
    for(const e of located){const key=e.latitude+','+e.longitude;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}
    for(const es of groups.values()){
      const e=es[0], marker=L.marker([Number(e.latitude),Number(e.longitude)],{icon:L.divIcon({className:`map-pin ${e.format==='hybrid'?'hybrid':''}`,html:String(es.length),iconSize:[31,31],iconAnchor:[15,15]}),title:`${es.length} event${es.length===1?'':'s'}: ${e.location}`,keyboard:true});
      marker.bindPopup(`<strong>${esc(e.location)}</strong>${es.slice(0,8).map(x=>`<p><button data-event="${esc(x.id)}">${esc(x.title)}</button><br>${esc(when(x))}</p>`).join('')}${es.length>8?`<p>${es.length-8} more events at this location. Search for the city to see all.</p>`:''}`);pins.addLayer(marker);
    }
  }
  async function setupMap(){
    if(typeof L==='undefined'){$('#map').innerHTML='<p class="empty">The map couldn’t load. All events remain available in the list.</p>';return;}
    map=L.map('map',{scrollWheelZoom:false,minZoom:1,maxZoom:11,worldCopyJump:true}).setView([23,8],2);
    map.attributionControl.addAttribution('Geography: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');pins=L.layerGroup().addTo(map);
    try{const world=await fetch('vendor/world.geojson').then(r=>{if(!r.ok)throw Error();return r.json();});L.geoJSON(world,{style:{color:'#a8becd',weight:.6,fillColor:'#f7fafc',fillOpacity:1},interactive:false}).addTo(map).bringToBack();}
    catch{$('#map-count').textContent='Base map unavailable; event locations are still shown';}
    renderPins();$('#reset-map').addEventListener('click',()=>map.setView([23,8],2));
  }
  function openEvent(id){const e=events.find(x=>x.id===id);if(!e)return;selectedId=id;
    $('#detail-content').innerHTML=`<p class="eyebrow">${esc(e.organiser)}</p><h2>${esc(e.title)}</h2>${badge(e)}<p>${esc(when(e))}</p><dl><dt>Where</dt><dd>${esc(e.location)}${e.locationPrecision==='city'?'<br><small>Map pin is approximate, at city level.</small>':''}</dd><dt>Language</dt><dd>${esc(e.language)}</dd><dt>Cost</dt><dd>${esc(e.price)}</dd><dt>Access</dt><dd>${esc(e.access)}</dd></dl>${e.description?`<p>${esc(e.description)}</p>`:''}${e.notes.length?`<p class="event-meta">${e.notes.map(esc).join('<br>')}</p>`:''}<p class="event-meta">Last found: ${esc(new Date(e.lastSeen).toLocaleDateString('en-GB'))}${e.stale?' · Latest recheck incomplete':''}</p><div class="detail-buttons"><a class="button" href="${safe(e.url)}" target="_blank" rel="noopener">Event details / booking</a>${e.calendarEligible?`<button class="secondary" data-download="${esc(e.id)}">Add to calendar</button>`:''}</div><p class="event-meta">Sources: ${e.sources.map(s=>`<a target="_blank" rel="noopener" href="${safe(s.url)}">${esc(s.name)}</a>`).join(', ')}</p><a class="event-meta" href="https://github.com/antlerboy/systemsmap/issues/new?title=${encodeURIComponent('Correction: '+e.title)}&body=${encodeURIComponent('Event: '+e.url+'\n\nCorrection and evidence:\n')}">Report a correction</a>`;
    $('#detail').showModal();
  }
  const icEsc=s=>String(s??'').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');
  function fold(s){const enc=new TextEncoder();let lines=[],line='';for(const ch of s){if(enc.encode(line+ch).length>74){lines.push(line);line=' '+ch;}else line+=ch;}return lines.concat(line).join('\r\n');}
  function ics(es){let a=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Systems Events Map//EN','CALSCALE:GREGORIAN'];for(const e of es.filter(x=>x.calendarEligible)){
    a.push('BEGIN:VEVENT','UID:'+e.id+'@systemsmap.antlerboy.com','DTSTAMP:'+new Date(e.updatedAt).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,''),'SEQUENCE:'+e.sequence,'SUMMARY:'+icEsc(e.title));
    for(const [k,f] of [['start','DTSTART'],['end','DTEND']])if(e[k])a.push(f+(e.allDay?';VALUE=DATE:':':')+(e.allDay?e[k].replace(/-/g,''):new Date(e[k]).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')));
    a.push('URL:'+e.url,'LOCATION:'+icEsc(e.location),'DESCRIPTION:'+icEsc(e.organiser+'\n'+e.url+'\n'+e.notes.join('\n')),'STATUS:'+(e.status==='cancelled'?'CANCELLED':'CONFIRMED'),'TRANSP:TRANSPARENT','END:VEVENT');
  }return a.concat('END:VCALENDAR').map(fold).join('\r\n')+'\r\n';}
  function download(es){const blob=new Blob([ics(es)],{type:'text/calendar;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='systems-events.ics';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function updateFeed(){const url=new URL(dataBase+'feeds/'+$('#feed').value+'.ics',location.href).href;$('#feed-url').textContent=url;$('#feed-url').href=url;$('#webcal-feed').href=url.replace(/^https?:/,'webcal:');$('#google-feed').href='https://calendar.google.com/calendar/render?cid='+encodeURIComponent(url.replace(/^https?:/,'webcal:'));$('#copy-status').textContent='';}
  async function load(){
    try{
      const [data,coverage,feedData]=await Promise.all(['events','sources','feeds'].map(n=>fetch(dataBase+'data/'+n+'.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error(n+' unavailable');return r.json();})));
      events=data.events;sourceData=coverage.sources;feeds=feedData;
      const age=(Date.now()-new Date(data.generatedAt))/86400000;$('#freshness').textContent=(age>2?'Collection needs attention · ':'Last collection · ')+new Date(data.generatedAt).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'})+` · ${sourceData.length} monitored sources`;
      $('#org').insertAdjacentHTML('beforeend',sourceData.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join(''));
      $('#country').insertAdjacentHTML('beforeend',[...new Set(events.map(e=>e.country).filter(Boolean))].sort().map(c=>`<option>${esc(c)}</option>`).join(''));
      for(const key of ['q','period','org','format','country'])if(params.has(key))$('#'+key).value=params.get(key);
      if(params.has('topic')){const el=[...document.querySelectorAll('#topics input')].find(x=>x.value===params.get('topic'));if(el)el.checked=true;}
      $('#feed').innerHTML=feeds.map(f=>`<option value="${esc(f.id)}">${esc(f.name)} (${f.events})</option>`).join('');updateFeed();
      const collecting=sourceData.filter(s=>s.events>0).length;$('#coverage-stats').innerHTML=`<span><strong>${sourceData.length}</strong>sources checked</span><span><strong>${collecting}</strong>yielding events</span><span><strong>${sourceData.filter(s=>s.status==='failed'||s.status==='needs-review').length}</strong>need attention</span>`;
      $('#sources').innerHTML=sourceData.map(s=>`<tr><td><a href="${safe(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a><small>${esc(s.region||'International')}</small></td><td><span class="status ${s.status==='failed'?'fail':s.status==='ok'?'':'warn'}">${({ok:'Collecting',partial:'Partly collected',failed:'Couldn’t collect','needs-review':'Needs review'})[s.status]}</span><small>${esc(s.message)}</small>${s.errors?.length?`<details><summary>Check details</summary><small>${s.errors.map(esc).join('<br>')}</small></details>`:''}</td><td>${s.events}</td></tr>`).join('');
      render();await setupMap();
    }catch(err){$('#freshness').textContent='The collection could not be loaded.';$('#results').innerHTML='<div class="empty">Event data is temporarily unavailable. <a href="https://github.com/antlerboy/systemsmap/actions">Check collection status</a> or reload this page.</div>';$('#count').textContent='Couldn’t load events';$('#map').innerHTML='<p class="empty">The map will appear when event data is available.</p>';console.error(err);}
  }
  $('#filters').addEventListener('submit',e=>e.preventDefault());$('#filters').addEventListener('input',()=>{limit=30;render();});
  $('#filters').addEventListener('reset',()=>setTimeout(()=>{limit=30;render();},0));$('#timezone').addEventListener('change',render);
  $('#more').addEventListener('click',()=>{limit+=30;render();});$('#export').addEventListener('click',()=>download(filtered));
  $('#detail .close').addEventListener('click',()=>$('#detail').close());$('#detail').addEventListener('click',e=>{if(e.target===$('#detail'))$('#detail').close();});
  document.addEventListener('click',e=>{const t=e.target.closest('[data-event],[data-download],[data-reset]');if(!t)return;if(t.dataset.event)openEvent(t.dataset.event);if(t.dataset.download)download(events.filter(x=>x.id===t.dataset.download));if(t.hasAttribute('data-reset'))$('#filters').reset();});
  $('#feed').addEventListener('change',updateFeed);$('#copy-feed').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#feed-url').href);$('#copy-status').textContent='Subscription URL copied.';}catch{$('#copy-status').textContent='Copy the link from ‘View the feed URL’ below.';$('#feed-url').closest('details').open=true;}});
  $('#submission-kind').addEventListener('change',()=>{const event=$('#submission-kind').value==='event';$('#submission-dates').hidden=!event;$('#submission-location').hidden=!event;});
  $('#submission').addEventListener('submit',e=>{
    e.preventDefault();const form=e.currentTarget,d=Object.fromEntries(new FormData(form));
    let url;try{url=new URL(d.url.replace(/^webcal:/,'https:'));if(!['https:','http:'].includes(url.protocol)||url.username||url.password)throw Error();}catch{$('#submission-status').textContent='Please enter a public https:// or webcal:// URL.';return;}
    if(d.start&&d.end&&d.end<d.start){$('#submission-status').textContent='The end date must be on or after the start date.';return;}
    if(d.timezone){try{new Intl.DateTimeFormat('en',{timeZone:d.timezone});}catch{$('#submission-status').textContent='Use an IANA time zone such as Europe/London, or leave it blank.';return;}}
    const proposal={kind:d.kind,title:d.title.trim(),url:url.href,organiser:d.organiser.trim(),start:d.start||null,end:d.end||null,startTime:d.startTime||null,endTime:d.endTime||null,timezone:d.timezone.trim()||null,location:d.location.trim(),topics:[d.topic],description:d.description.trim()};
    const body='Please review this public '+d.kind+' submission.\n\n```json\n'+JSON.stringify(proposal,null,2)+'\n```\n\nSubmitted through the Systems events map. Inclusion requires maintainer review.';
    const target=new URL('https://github.com/antlerboy/systemsmap/issues/new');target.searchParams.set('title','Submission: '+proposal.title);target.searchParams.set('body',body);target.searchParams.set('labels','submission');
    $('#submission-status').textContent='Opening GitHub. Your submission is sent when you choose ‘Create’ there.';window.open(target.href,'_blank','noopener');
  });
  load();
})();
