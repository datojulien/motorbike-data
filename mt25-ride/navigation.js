/* MT-25 Ride v2 — foreground turn-by-turn navigation.
 * Router: community OSRM public demo (experimental, non-critical use).
 * Geocoder: Photon demo (search only on explicit user request).
 * No tokens, user accounts, location uploads of recorded tracks, or offline tile scraping.
 */
(() => {
  'use strict';
  const ROUTER = 'https://router.project-osrm.org';
  const GEOCODER = 'https://photon.komoot.io';
  const VOICE_SETTING = 'mt25-navigation-voice-v2';
  const EARTH_M = 6371008.8;
  const radians = Math.PI / 180;
  const $ = id => document.getElementById(id);
  const haversine = (a,b) => {
    const dlat=(b.lat-a.lat)*radians,dlon=(b.lon-a.lon)*radians;
    const x=Math.sin(dlat/2)**2+Math.cos(a.lat*radians)*Math.cos(b.lat*radians)*Math.sin(dlon/2)**2;
    return 2*EARTH_M*Math.atan2(Math.sqrt(x),Math.sqrt(Math.max(0,1-x)));
  };
  const finitePoint=p=>p&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<=90&&Math.abs(p.lon)<=180;
  const routeDistance = n => !Number.isFinite(n)?'—':n<950?`${Math.max(0,Math.round(n/10)*10)} m`:`${(n/1000).toFixed(n<10000?1:0)} km`;
  const angleWord = d => ['north','north-east','east','south-east','south','south-west','west','north-west'][Math.round((((d%360)+360)%360)/45)%8];
  const coordsFromText = s => {
    const m=s.trim().match(/^(-?\d{1,2}(?:\.\d+)?)\s*[,;]\s*(-?\d{1,3}(?:\.\d+)?)$/);
    if(!m)return null;
    const pt={lat:Number(m[1]),lon:Number(m[2])};return finitePoint(pt)?pt:null;
  };
  const calcCumulative=points=>{
    const arr=[0];for(let i=1;i<points.length;i++)arr.push(arr[i-1]+haversine(points[i-1],points[i]));return arr;
  };
  // Closest projection to a road segment, in local metres. Position is cumulative road distance.
  function nearestLine(pt, points, cumulative, previous=0){
    let best=null; const cos=Math.max(.15,Math.cos(pt.lat*radians));
    for(let i=1;i<points.length;i++){
      const a=points[i-1], b=points[i],dx=(b.lon-a.lon)*111195*cos,dy=(b.lat-a.lat)*111195;
      const denominator=dx*dx+dy*dy;const px=(pt.lon-a.lon)*111195*cos,py=(pt.lat-a.lat)*111195;
      const t=Math.max(0,Math.min(1,denominator>0?(px*dx+py*dy)/denominator:0));
      const distance=Math.hypot(px-t*dx,py-t*dy);
      const progress=cumulative[i-1]+(cumulative[i]-cumulative[i-1])*t;
      // Penalise distant snap candidates when the road overlaps itself, but allow U-turns.
      const discontinuity=progress<previous-85?Math.min(180,(previous-progress)*.13):progress>previous+2200?Math.min(350,(progress-previous-2200)*.18):0;
      const score=distance+discontinuity;
      if(!best||score<best.score)best={distance,progress,score,segment:i-1};
    }
    return best;
  }
  function wordForManeuver(step){
    const m=step.maneuver||{}, modifier=m.modifier||'',road=String(step.name||step.ref||'').trim();
    const onto=road?` onto ${road}`:'';
    if(m.type==='arrive')return 'You have arrived at your destination';
    if(m.type==='depart')return `Head ${angleWord(m.bearing_after||0)}${onto}`;
    if(m.type==='roundabout'||m.type==='rotary')return m.exit?`At the roundabout, take exit ${m.exit}${onto}`:`Enter the roundabout${onto}`;
    if(m.type==='exit roundabout'||m.type==='exit rotary')return `Exit the roundabout${onto}`;
    if(m.type==='merge')return `Merge ${modifier.replace('slight ','')} ${onto}`.replace(/\s+/g,' ').trim();
    if(m.type==='on ramp')return `Take the ramp ${modifier}${onto}`.replace(/\s+/g,' ').trim();
    if(m.type==='off ramp')return `Take the exit ${modifier}${onto}`.replace(/\s+/g,' ').trim();
    if(m.type==='fork')return `Keep ${modifier.replace('slight ','')}${onto}`;
    if(m.type==='end of road')return `At the end of the road, turn ${modifier}${onto}`;
    if(m.type==='new name'||m.type==='notification')return road?`Continue onto ${road}`:'Continue straight';
    if(m.type==='continue'&&(!modifier||modifier==='straight'))return road?`Continue on ${road}`:'Continue straight';
    if(m.type==='turn'&&modifier==='uturn')return 'Make a U-turn'+onto;
    if(modifier==='straight')return `Continue straight${onto}`;
    if(modifier==='slight left'||modifier==='slight right')return `Bear ${modifier.replace('slight ','')}${onto}`;
    if(modifier==='sharp left'||modifier==='sharp right')return `Turn sharply ${modifier.replace('sharp ','')}${onto}`;
    if(modifier==='left'||modifier==='right')return `Turn ${modifier}${onto}`;
    return road?`Continue on ${road}`:'Continue straight';
  }
  function turnSymbol(step){
    const m=step.maneuver||{},t=m.type,mod=m.modifier||'';
    if(t==='arrive')return '⚑';
    if(t==='roundabout'||t==='rotary')return '⟳';
    if(mod==='uturn')return '↶';
    if(mod.includes('left'))return '↰';
    if(mod.includes('right'))return '↱';
    if(t==='fork')return '↗';
    return '↑';
  }
  function create(options){
    const {getPosition,getAccuracy,getSpeed,beginGPS,isDemo,drawMap,showModal,closeModal,toast,onNavState} = options;
    let route=null, destination=null, progress=0, lastNextId=-1, approachStage=-1;
    let waitingForFix=false, fetching=false, lastRouteRequest=0, offRouteFixes=0, requestSequence=0;
    let activeAbort=null, searchAbort=null, searchCache=new Map(),demoProgress=0;
    let voiceEnabled=localStorage.getItem(VOICE_SETTING)!=='off';
    let lastSpoken='', lastVoiceTime=0, routeNotice='';
    const navPane=$('nav-guidance');
    const canSpeak=()=>('speechSynthesis'in window)&&('SpeechSynthesisUtterance'in window);
    function speak(text,force=false){
      if(!voiceEnabled||!canSpeak()||document.hidden||!text)return;
      const now=Date.now();if(!force&&(text===lastSpoken&&now-lastVoiceTime<20000))return;
      try{
        const speech=new SpeechSynthesisUtterance(text);speech.lang='en-GB';speech.rate=.95;speech.volume=1;
        window.speechSynthesis.cancel();window.speechSynthesis.speak(speech);
        lastSpoken=text;lastVoiceTime=now;
      }catch{ /* Some Safari / helmet combinations cannot play web speech. */ }
    }
    function speakPrompt(){
      if(!voiceEnabled||!canSpeak())return;
      speak('Navigation voice on',true); // Call directly from tap to unlock iOS speech.
    }
    function render(){
      navPane.hidden=!destination;
      $('nav-btn').classList.toggle('nav-is-active',!!destination);
      $('nav-btn').querySelector('span').textContent=destination?'ROUTE ACTIVE':'NAVIGATE';
      $('map-area').classList.toggle('is-navigating',!!destination);
      if(!destination)return;
      const mute=$('nav-voice');mute.textContent=voiceEnabled?'🔊':'🔇';mute.setAttribute('aria-label',voiceEnabled?'Mute voice guidance':'Enable voice guidance');
      if(waitingForFix){
        $('nav-arrow').textContent='◎'; $('nav-distance').textContent='GPS';
        $('nav-instruction').textContent='Waiting for your location';
        $('nav-road').textContent=destination.label;$('nav-eta').textContent='';return;
      }
      if(fetching){
        $('nav-arrow').textContent='↻';$('nav-distance').textContent='ROUTE';
        $('nav-instruction').textContent='Calculating directions…';
        $('nav-road').textContent=destination.label;$('nav-eta').textContent='';return;
      }
      if(!route){
        $('nav-arrow').textContent='!';$('nav-distance').textContent='OFFLINE';
        $('nav-instruction').textContent=routeNotice||'Directions unavailable';
        $('nav-road').textContent=destination.label;$('nav-eta').textContent='Try Waze / Maps';return;
      }
      const next=nextManeuver();const remaining=Math.max(0,route.totalM-progress);
      $('nav-arrow').textContent=next?turnSymbol(next.step):'⚑';
      $('nav-distance').textContent=next?routeDistance(Math.max(0,next.at-progress)):'ARRIVING';
      $('nav-instruction').textContent=next?wordForManeuver(next.step):'Continue to destination';
      $('nav-road').textContent=destination.label;
      const seconds=(remaining/Math.max(route.totalM,1))*route.durationS;
      const eta=new Date(Date.now()+Math.max(0,seconds)*1000);
      $('nav-eta').textContent=`${routeDistance(remaining)} left · ETA ${eta.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})}`;
      if(routeNotice)$('nav-eta').textContent=routeNotice+' · '+$('nav-eta').textContent;
    }
    function nextManeuver(){
      if(!route)return null;
      return route.instructions.find(x=>x.at>progress+13 && x.step.maneuver?.type!=='depart')||route.instructions.at(-1)||null;
    }
    function drawOverlay({projected,topLeft,w,h,zoom}){
      const overlay=$('nav-route-overlay'),line=$('nav-route-line'),halo=$('nav-route-halo'),pin=$('nav-target-pin');
      if(!route||!route.coords.length){line.setAttribute('points','');halo.setAttribute('points','');pin.hidden=true;return;}
      overlay.setAttribute('viewBox',`0 0 ${w} ${h}`);
      const step=Math.max(1,Math.ceil(route.coords.length/2800));
      const points=[];
      for(let i=0;i<route.coords.length;i+=step){const p=projected(route.coords[i].lat,route.coords[i].lon,zoom);points.push(`${(p.x-topLeft.x).toFixed(1)},${(p.y-topLeft.y).toFixed(1)}`);}
      const last=route.coords.at(-1),lp=projected(last.lat,last.lon,zoom);
      if((route.coords.length-1)%step!==0)points.push(`${(lp.x-topLeft.x).toFixed(1)},${(lp.y-topLeft.y).toFixed(1)}`);
      const xy=points.join(' ');line.setAttribute('points',xy);halo.setAttribute('points',xy);
      pin.hidden=false;pin.style.left=`${lp.x-topLeft.x}px`;pin.style.top=`${lp.y-topLeft.y}px`;
    }
    function prepareRoute(data){
      if(data?.code!=='Ok'||!Array.isArray(data.routes)||!data.routes.length)throw new Error('No route found between those locations.');
      const r=data.routes[0],coords=r.geometry?.coordinates?.map(p=>({lat:Number(p[1]),lon:Number(p[0])}));
      if(!Array.isArray(coords)||coords.length<2||!coords.every(finitePoint))throw new Error('The routing service sent an invalid path.');
      const cum=calcCumulative(coords),steps=(r.legs||[]).flatMap(l=>l.steps||[]);
      const instructions=steps.map((step,i)=>{
        const xy=step.maneuver?.location;
        const loc=xy&&xy.length===2?{lat:xy[1],lon:xy[0]}:coords[Math.min(i,coords.length-1)];
        const match=nearestLine(loc,coords,cum,0);
        return {step,at:Math.max(0,match?.progress||0),index:i};
      }).sort((a,b)=>a.at-b.at||a.index-b.index);
      return {coords,cumulative:cum,totalM:cum.at(-1),durationS:Number(r.duration)||0,instructions};
    }
    async function fetchRoute(origin, target, reroute=false){
      if(!finitePoint(origin)||!finitePoint(target))return;
      if(activeAbort)activeAbort.abort();const controller=new AbortController();activeAbort=controller;
      const seq=++requestSequence;fetching=true;waitingForFix=false;routeNotice='';lastRouteRequest=Date.now();render();
      const from=[origin.lon,origin.lat].map(x=>x.toFixed(6)).join(',');const to=[target.lon,target.lat].map(x=>x.toFixed(6)).join(',');
      const url=`${ROUTER}/route/v1/driving/${from};${to}?overview=full&geometries=geojson&steps=true&alternatives=false`;
      const timeout=setTimeout(()=>controller.abort(),18000);
      try{
        const response=await fetch(url,{signal:controller.signal,referrerPolicy:'strict-origin-when-cross-origin'});
        if(!response.ok)throw new Error(response.status===429?'Routing server is busy. Try again later.':'Routing service is unavailable.');
        const data=await response.json();const result=prepareRoute(data);
        if(seq!==requestSequence)return;
        route=result;progress=0;offRouteFixes=0;lastNextId=-1;approachStage=-1;
        routeNotice='';demoProgress=0;
        fetching=false;render();drawMap();
        const next=nextManeuver();
        if(reroute){speak('Route recalculated',true);toast('Route recalculated.');}
        else{toast(`Route ready · ${routeDistance(route.totalM)}. Keep the dashboard open.`);speak('Route ready. '+(next?wordForManeuver(next.step):''),true);}
      }catch(err){
        if(seq!==requestSequence)return;
        fetching=false;
        if(err.name==='AbortError'&&activeAbort!==controller)return;
        routeNotice=err.name==='AbortError'?'Routing timed out':err.message||'Directions unavailable';
        if(!reroute)route=null;
        toast(routeNotice+'. Use Apple Maps or Waze as a backup.');render();drawMap();
      }finally{clearTimeout(timeout);if(activeAbort===controller)activeAbort=null;}
    }
    function startDestination(point,label){
      if(!finitePoint(point)){toast('Destination must have valid coordinates.');return;}
      stop(false);destination={lat:point.lat,lon:point.lon,label:String(label||'Pinned destination').slice(0,120)};
      // User click is our opportunity to unlock speech synthesis on iOS.
      speakPrompt();closeModal();onNavState(true);const origin=getPosition();
      if(!origin){waitingForFix=true;render();beginGPS();toast('Waiting for a GPS fix before planning the route.');return;}
      fetchRoute(origin,destination);
    }
    function stop(notify=true){
      requestSequence++;if(activeAbort){activeAbort.abort();activeAbort=null;}
      destination=null;route=null;progress=0;waitingForFix=false;fetching=false;routeNotice='';offRouteFixes=0;lastNextId=-1;approachStage=-1;demoProgress=0;
      if(canSpeak())window.speechSynthesis.cancel();
      render();drawMap();onNavState(false);if(notify)toast('Navigation stopped. Trip recording is unchanged.');
    }
    function handleFix(pos,accuracy,speed){
      if(!destination||!finitePoint(pos))return;
      if(waitingForFix){if(Number.isFinite(accuracy)&&accuracy>80)return;fetchRoute(pos,destination);return;}
      if(!route||fetching||!Number.isFinite(accuracy)||accuracy>65)return;
      const match=nearestLine(pos,route.coords,route.cumulative,progress);
      if(!match)return;
      const tolerance=Math.max(45,Math.min(100,accuracy*2));
      if(match.distance>tolerance){
        if((speed??0)>6&&!isDemo())offRouteFixes++;
        if(offRouteFixes>=3&&Date.now()-lastRouteRequest>30000){
          offRouteFixes=0;fetchRoute(pos,destination,true);
        }else if(offRouteFixes>=2){routeNotice='OFF ROUTE — checking…';render();}
        return;
      }
      routeNotice='';offRouteFixes=0;
      if(match.progress>=progress-20)progress=Math.max(progress,Math.min(match.progress,progress+Math.max(350,(speed||35)*1.8)));
      if(haversine(pos,destination)<40&&route.totalM-progress<110){
        stop(false);speak('You have arrived at your destination',true);toast('Destination reached. Have a lovely ride!');return;
      }
      const next=nextManeuver();
      if(next){
        const dist=next.at-progress;
        const stage=dist<=45?2:dist<=180?1:dist<=600?0:-1;
        if(next.index!==lastNextId){lastNextId=next.index;approachStage=-1;}
        if(stage>approachStage&&stage>=0){
          approachStage=stage;
          const lead=dist<=45?'Now, ':`In ${routeDistance(dist)}, `;
          const phr=wordForManeuver(next.step);
          if(next.step.maneuver?.type!=='arrive'||stage>=1)speak(lead+phr.charAt(0).toLowerCase()+phr.slice(1));
        }
      }
      render();
    }
    async function placeSearch(term){
      const query=term.trim();const container=$('place-results');container.replaceChildren();
      if(query.length<3){container.textContent='Enter at least three characters, or coordinates like 2.92, 101.69.';return;}
      const coords=coordsFromText(query);
      if(coords){addResult(container,'📍  '+coords.lat.toFixed(5)+', '+coords.lon.toFixed(5),'Coordinates',coords);return;}
      if(searchAbort)searchAbort.abort();const controller=new AbortController();searchAbort=controller;
      container.textContent='Searching for places…';$('place-search').disabled=true;
      const origin=getPosition()||{lat:2.925,lon:101.689};
      const url=`${GEOCODER}/api/?q=${encodeURIComponent(query)}&lang=en&limit=6&lat=${origin.lat.toFixed(5)}&lon=${origin.lon.toFixed(5)}`;
      const timeout=setTimeout(()=>controller.abort(),12000);
      try{
        let data=searchCache.get(query.toLowerCase());
        if(!data){const response=await fetch(url,{signal:controller.signal,referrerPolicy:'strict-origin-when-cross-origin'});if(!response.ok)throw new Error('Place search unavailable.');data=await response.json();searchCache.set(query.toLowerCase(),data);if(searchCache.size>20)searchCache.delete(searchCache.keys().next().value);}
        if(searchAbort!==controller)return;
        container.replaceChildren();
        const features=(data.features||[]).filter(f=>Array.isArray(f.geometry?.coordinates)&&f.geometry.coordinates.length===2);
        for(const f of features){
          const props=f.properties||{},xy=f.geometry.coordinates,point={lat:Number(xy[1]),lon:Number(xy[0])};if(!finitePoint(point))continue;
          const name=props.name||props.street||props.city||'Unnamed location';
          const info=[props.street&&props.street!==name?props.street:null,props.city,props.state,props.country].filter(Boolean).join(', ');
          addResult(container,name,info,point);
        }
        if(!container.children.length)container.textContent='No places found. Try a more specific search or use coordinates.';
      }catch(err){
        if(searchAbort!==controller)return;
        container.textContent=err.name==='AbortError'?'Place search timed out. Try again.':'Search unavailable. Enter coordinates or pin the map instead.';
      }finally{clearTimeout(timeout);if(searchAbort===controller){searchAbort=null;$('place-search').disabled=false;}}
    }
    function addResult(container,title,description,point){
      const btn=document.createElement('button');btn.type='button';btn.className='place-result';
      const titleNode=document.createElement('strong');titleNode.textContent=String(title).slice(0,125);
      const info=document.createElement('small');info.textContent=String(description).slice(0,180);
      btn.append(titleNode,info);
      btn.addEventListener('click',()=>startDestination(point,title));
      container.appendChild(btn);
    }
    function openPlanner(){
      if(destination){
        showModal('Navigation','RIDE / DIRECTIONS',`
          <div class="modal-card"><strong>Destination</strong><span id="active-destination"></span><p class="muted-note" id="active-nav-summary"></p></div>
          <div class="modal-actions"><button id="replace-route" class="action-btn primary">NEW DESTINATION</button><button id="retry-route" class="action-btn">RETRY ROUTE</button></div>
          <div class="modal-actions"><button id="external-waze" class="action-btn">WAZE ↗</button><button id="external-apple" class="action-btn">APPLE MAPS ↗</button></div>
          <button id="stop-navigation" class="action-btn danger full">END NAVIGATION</button>`);
        $('active-destination').textContent=destination.label;
        $('active-nav-summary').textContent=route?`${routeDistance(Math.max(0,route.totalM-progress))} remaining · routing by OSRM`:routeNotice||'Awaiting route';
        $('replace-route').addEventListener('click',()=>{closeModal();openNewDestination();});
        $('retry-route').addEventListener('click',()=>{closeModal();const pos=getPosition();if(pos)fetchRoute(pos,destination);else{waitingForFix=true;render();beginGPS();}});
        $('external-apple').addEventListener('click',()=>openExternal('apple'));
        $('external-waze').addEventListener('click',()=>openExternal('waze'));
        $('stop-navigation').addEventListener('click',()=>{stop();closeModal();});
      }else openNewDestination();
    }
    function openExternal(provider){
      if(!destination)return;
      const pos=`${destination.lat.toFixed(6)},${destination.lon.toFixed(6)}`;
      window.open(provider==='waze'?`https://waze.com/ul?ll=${encodeURIComponent(pos)}&navigate=yes`:`https://maps.apple.com/?daddr=${encodeURIComponent(pos)}&dirflg=d`,'_blank','noopener,noreferrer');
    }
    function openNewDestination(){
      showModal('Where to?','TURN-BY-TURN / ROUTE PLANNER',`
        <p>Search for a destination before setting off. Turn-by-turn directions will appear inside your dashboard.</p>
        <label class="modal-label" for="destination">PLACE OR LATITUDE, LONGITUDE</label>
        <div class="nav-search-row"><input id="destination" class="modal-input" type="search" placeholder="e.g. Putrajaya Sentral" autocomplete="off" maxlength="160"><button class="action-btn primary" id="place-search">SEARCH</button></div>
        <div class="place-results" id="place-results" aria-live="polite"></div>
        <p class="muted-note">Tip: hold your finger on the map to pin any destination, even without place search.</p>
        <div class="modal-actions"><button id="demo-destination" class="action-btn">DEMO: PUTRAJAYA</button><button id="current-apple-nav" class="action-btn">APPLE MAPS ↗</button></div>
        <div class="modal-card"><strong>Experimental routing</strong><a class="modal-link" href="https://github.com/komoot/photon" target="_blank" rel="noopener noreferrer">Photon search</a> and <a class="modal-link" href="https://project-osrm.org/" target="_blank" rel="noopener noreferrer">OSRM routing</a> public community servers require internet, may be rate-limited and offer no uptime guarantees. Traffic, closures and motorcycle restrictions may be missing. Waze / Apple Maps remain available as backup. Never type while riding.</div>`);
      $('place-search').addEventListener('click',()=>placeSearch($('destination').value));
      $('destination').addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();placeSearch(ev.target.value);}});
      $('demo-destination').addEventListener('click',()=>startDestination({lat:2.9357,lon:101.6958},'Putrajaya / Cyberjaya (demo destination)'));
      $('current-apple-nav').addEventListener('click',()=>{const term=$('destination').value.trim();if(!term){toast('Enter a destination first.');return;}window.open(`https://maps.apple.com/?daddr=${encodeURIComponent(term)}&dirflg=d`,'_blank','noopener,noreferrer');});
    }
    function pinDestination(point){
      if(!finitePoint(point))return;
      const title=`${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}`;
      showModal('Navigate to this pin?','MAP / PIN DESTINATION',`
        <p id="pinned-coordinates"></p>
        <div class="modal-actions"><button id="start-pin-route" class="action-btn primary">START NAVIGATION</button><button id="cancel-pin-route" class="action-btn">CANCEL</button></div>
        <p class="muted-note">This routes to the nearest accessible road, not necessarily directly to the precise pin.</p>`);
      $('pinned-coordinates').textContent=title;
      $('start-pin-route').addEventListener('click',()=>startDestination(point,title));
      $('cancel-pin-route').addEventListener('click',closeModal);
    }
    function demoPoint(){
      if(!route||!isDemo())return null;
      demoProgress=Math.min(route.totalM,demoProgress+20);
      const cum=route.cumulative,coords=route.coords;
      let i=1;while(i<cum.length-1&&cum[i]<demoProgress)i++;
      const len=cum[i]-cum[i-1],t=len>0?(demoProgress-cum[i-1])/len:0;
      const a=coords[i-1],b=coords[i];return {lat:a.lat+(b.lat-a.lat)*t,lon:a.lon+(b.lon-a.lon)*t,heading:(Math.atan2((b.lon-a.lon)*Math.cos(a.lat*radians),(b.lat-a.lat))/radians+360)%360};
    }
    $('nav-voice').addEventListener('click',()=>{
      voiceEnabled=!voiceEnabled;localStorage.setItem(VOICE_SETTING,voiceEnabled?'on':'off');
      if(voiceEnabled){if(!canSpeak())toast('This browser does not support speech synthesis.');else{speakPrompt();toast('Voice guidance enabled.');}}
      else{if(canSpeak())window.speechSynthesis.cancel();toast('Voice guidance muted.');}
      render();
    });
    $('nav-end').addEventListener('click',()=>stop());
    render();
    return {openPlanner,handleFix,drawOverlay,pinDestination,demoPoint,stop,
      getState:()=>({active:!!destination,hasRoute:!!route,progress,routeDistance:route?.totalM||0})};
  }
  window.MT25Navigation={create,_test:{haversine,nearestLine,calcCumulative,wordForManeuver,turnSymbol,coordsFromText,routeDistance}};
})();
