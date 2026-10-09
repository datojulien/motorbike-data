/* MT-25 Ride · v3.0 — full-screen navigation with foreground trip computer. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const EARTH_M = 6371008.8;
  const TILE_SIZE = 256;
  const STORE = 'mt25-ride-trip-v1';
  const PREFS = 'mt25-ride-prefs-v1';
  const MAX_POINTS = 14000;
  const DEMO = new URLSearchParams(location.search).has('demo');
  const PREVIEW = new URLSearchParams(location.search).has('preview');
  const defaultCenter = {lat: 2.925, lon: 101.689}; // General Cyberjaya area; not a home address.
  const samplesForDemo = [
    [2.9165,101.6662], [2.9197,101.6679], [2.9222,101.6712],
    [2.9252,101.6742], [2.9285,101.6785], [2.9310,101.6825],
    [2.9340,101.6859], [2.9362,101.6910], [2.9351,101.6946],
    [2.9339,101.6989], [2.9319,101.7027]
  ];
  const makeTrip = () => ({distanceM:0, elapsedS:0, maxKmh:0, points:[], lastAccepted:null});
  function parseJSON(s, fallback){try{const v=JSON.parse(s);return v??fallback;}catch{return fallback;}}
  function loadTrip(){
    const saved = parseJSON(localStorage.getItem(STORE), null);
    if(!saved || !Number.isFinite(saved.distanceM) || !Number.isFinite(saved.elapsedS)) return makeTrip();
    return {...makeTrip(),distanceM:Math.max(0,saved.distanceM),elapsedS:Math.max(0,saved.elapsedS),maxKmh:Math.max(0,saved.maxKmh||0),
      points:Array.isArray(saved.points)?saved.points.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lon)).slice(-MAX_POINTS):[],
      lastAccepted:null};
  }
  const prefs = parseJSON(localStorage.getItem(PREFS), {}) || {};
  let trip = loadTrip();
  let rideActive = false;
  let isDemo = false;
  let GPSwatch = null;
  let hasGPS = false;
  let lastFixAt = 0;
  let rawFix = null;
  let currentPosition = null;
  let currentSpeed = null;
  let currentHeading = null;
  let gpsAccuracy = null;
  let lastTimerTick = Date.now();
  let lastSave = 0;
  let wakeLock = null;
  let theme = prefs.theme === 'day' ? 'day' : 'night';
  let mapZoom = 14;
  let mapCenter = {...defaultCenter};
  let followPosition = true;
  let mapTiles = new Map();
  let tileErrors = 0;
  let pointer = null;
  let toastTimer = null;
  let demoInterval = null;
  let demoStep = 0;
  let routeRefreshAt = 0;
  let navigation = null;
  let startNewSegment = false;
  let navFullscreen = false;
  let tripOverlayOpen = false;

  // This is a view change within the SAME foreground web app, not iOS background execution.
  function setNavigationView(fullscreen){
    navFullscreen=!!fullscreen && !!navigation?.getState().active;
    document.documentElement.classList.toggle('navigation-fullscreen',navFullscreen);
    $('nav-view-controls').hidden=!navFullscreen;
    $('nav-fullscreen-footer').hidden=!navFullscreen;
    $('nav-expand').hidden=navFullscreen;
    if(!navFullscreen){tripOverlayOpen=false;$('nav-trip-panel').hidden=true;}
    $('nav-trip-toggle').setAttribute('aria-expanded',String(tripOverlayOpen));
    // Switching to map-only changes its dimensions; redraw after layout completes.
    requestAnimationFrame(()=>{if(navFullscreen){followPosition=true;mapZoom=Math.max(mapZoom,15);if(currentPosition)mapCenter={...currentPosition};}drawMap();});
  }
  function renderNavTrip(){
    $('nav-mini-distance').textContent=`${n1(trip.distanceM/1000)} km`;
    $('nav-mini-time').textContent=fmtTime(trip.elapsedS);
    $('nav-mini-speed').textContent=Number.isFinite(currentSpeed)?`${Math.round(currentSpeed)} km/h`:'-- km/h';
    $('nav-mini-average').textContent=`${trip.elapsedS>0?Math.round(trip.distanceM/1000/(trip.elapsedS/3600)):0} km/h`;
    $('nav-record-status').textContent=rideActive?'RECORDING':'PAUSED';
    $('nav-record-indicator').classList.toggle('paused',!rideActive);
    $('nav-trip-record').textContent=rideActive?'PAUSE TRIP RECORDING':'RESUME TRIP RECORDING';
  }

  function setTheme(next){
    theme=next==='day'?'day':'night';
    document.documentElement.dataset.theme=theme;
    $('theme-btn').innerHTML = `<svg><use href="#i-${theme==='night'?'sun':'moon'}"/></svg>`;
    $('theme-btn').setAttribute('aria-label', theme==='night'?'Switch to daytime colors':'Switch to nighttime colors');
    localStorage.setItem(PREFS,JSON.stringify({theme}));
  }
  function clock(){const n=new Date(); $('clock').textContent=`${String(n.getHours()).padStart(2,'0')}:${String(n.getMinutes()).padStart(2,'0')}`;}
  const n1=n=>Number(n).toFixed(1);
  function fmtTime(seconds){
    const s=Math.floor(seconds), hrs=Math.floor(s/3600), mins=Math.floor((s%3600)/60);
    return hrs ? `${String(hrs).padStart(2,'0')}:${String(mins).padStart(2,'0')}` : `${String(mins).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;
  }
  function haversine(a,b){
    const rad=Math.PI/180, dLat=(b.lat-a.lat)*rad, dLon=(b.lon-a.lon)*rad;
    const q=Math.sin(dLat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dLon/2)**2;
    return 2*EARTH_M*Math.atan2(Math.sqrt(q),Math.sqrt(1-q));
  }
  function direction(deg){
    if(!Number.isFinite(deg)) return '––';
    return ['N','NE','E','SE','S','SW','W','NW'][Math.round(((deg%360)+360)%360/45)%8];
  }
  function toast(message){
    const node=$('toast');node.textContent=message;node.classList.add('show');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.classList.remove('show'),3400);
  }
  function saveTrip(force=false){
    if(isDemo)return;
    if(!force && Date.now()-lastSave<4000)return;
    try {localStorage.setItem(STORE,JSON.stringify(trip));lastSave=Date.now();}
    catch {toast('Phone storage full: export your ride soon.');}
  }
  function setGPSStatus(state,msg){
    $('gps-pill-text').textContent=msg;
    const dot=$('gps-pill').querySelector('.dot');
    dot.className='dot '+(state==='ok'?'':state==='error'?'dot-bad':'dot-muted');
  }
  function renderInstrument(){
    const kmh=Number.isFinite(currentSpeed)?Math.max(0,Math.min(220,currentSpeed)):null;
    $('speed-number').textContent=kmh===null?'--':String(Math.round(kmh));
    const arc=405*Math.min(kmh??0,160)/160;
    $('ring-value').style.strokeDashoffset=String(405-arc);
    $('trip-distance').textContent=n1(trip.distanceM/1000);
    $('trip-time').textContent=fmtTime(trip.elapsedS);
    $('trip-average').textContent=trip.elapsedS>=1?String(Math.round((trip.distanceM/1000)/(trip.elapsedS/3600))):'0';
    $('trip-max').textContent=String(Math.round(trip.maxKmh));
    $('heading-label').textContent=direction(currentHeading);
    $('gps-accuracy').textContent=Number.isFinite(gpsAccuracy)?`± ${Math.round(gpsAccuracy)} m`:'ACCURACY —';
    const btn=$('ride-btn');btn.classList.toggle('is-riding',rideActive);
    $('ride-btn-text').textContent=rideActive?'PAUSE RIDE':trip.elapsedS>0?'RESUME RIDE':'START RIDE';
    btn.querySelector('use').setAttribute('href',rideActive?'#i-pause':'#i-play');
    $('ride-hint').textContent=rideActive?'RECORDING GPS':'GPS-BASED RECORDING';
    renderNavTrip();
  }
  function addTicks(){
    const el=$('ring-ticks'),cx=160,cy=156,r=130;
    // Semicircle: 180° to 360°, 17 tick marks, ends at y=156.
    for(let i=0;i<=16;i++){
      const a=(180+i*180/16)*Math.PI/180,major=i%4===0;
      const x1=cx+(r-(major?17:12))*Math.cos(a), y1=cy+(r-(major?17:12))*Math.sin(a);
      const x2=cx+(r-(major?7:6))*Math.cos(a), y2=cy+(r-(major?7:6))*Math.sin(a);
      const t=document.createElementNS('http://www.w3.org/2000/svg','line');
      t.setAttribute('x1',x1.toFixed(1));t.setAttribute('y1',y1.toFixed(1));t.setAttribute('x2',x2.toFixed(1));t.setAttribute('y2',y2.toFixed(1));
      if(major)t.classList.add('major');el.appendChild(t);
    }
  }
  async function holdScreen(){
    if((!rideActive&&!navigation?.getState().active)||document.hidden||!('wakeLock'in navigator)||wakeLock)return;
    try {wakeLock=await navigator.wakeLock.request('screen');wakeLock.addEventListener('release',()=>{wakeLock=null;});}
    catch { /* Wake Lock can be denied by Low Power Mode or system policy. */ }
  }
  async function releaseScreen(){if(wakeLock){try{await wakeLock.release();}catch{}wakeLock=null;}}
  function whenGPSFails(err){
    const denied=err && err.code===1;
    setGPSStatus('error',denied?'LOCATION DENIED':'GPS UNAVAILABLE');
    $('position-status').textContent=denied?'Enable Location in iPhone Settings':'Waiting for GPS signal';
    currentSpeed=null;renderInstrument();
    if(denied){rideActive=false;releaseScreen();if(GPSwatch!==null){navigator.geolocation.clearWatch(GPSwatch);GPSwatch=null;}renderInstrument();toast('Allow location for this web app in iPhone Settings.');}
  }
  function beginGPS(){
    if(isDemo)return true;
    if(!window.isSecureContext){toast('GPS needs HTTPS. Install through GitHub Pages, or use demo mode.');return false;}
    if(!('geolocation'in navigator)){toast('Geolocation is unavailable in this browser.');return false;}
    if(GPSwatch!==null)return true;
    setGPSStatus('wait','GETTING GPS FIX');
    GPSwatch=navigator.geolocation.watchPosition(updatePosition,whenGPSFails,{enableHighAccuracy:true,maximumAge:1000,timeout:20000});
    return true;
  }
  function processFix(fix){
    const now=fix.time||Date.now(),lat=fix.lat,lon=fix.lon,accuracy=fix.accuracy;
    if(!Number.isFinite(lat)||!Number.isFinite(lon))return;
    currentPosition={lat,lon};gpsAccuracy=accuracy;lastFixAt=Date.now();hasGPS=true;
    const rawSpeed=Number.isFinite(fix.speed)&&fix.speed>=0?fix.speed*3.6:null;
    let candidate=rawSpeed;
    if(candidate===null && rawFix){
      const seconds=(now-rawFix.time)/1000;
      if(seconds>0.3 && seconds<30 && accuracy<60 && rawFix.accuracy<60){
        const delta=haversine(rawFix,{lat,lon});
        candidate=delta<3?0:delta/seconds*3.6;
      }
    }
    if(Number.isFinite(candidate) && candidate>=0 && candidate<230){
      currentSpeed=currentSpeed===null?candidate:0.62*candidate+0.38*currentSpeed;
      if(currentSpeed<2)currentSpeed=0;
    } else if(Date.now()-now>12000) currentSpeed=null;
    currentHeading=Number.isFinite(fix.heading)&&fix.heading>=0?fix.heading:null;
    rawFix={lat,lon,time:now,accuracy};
    $('position-status').textContent=isDemo?'Simulated ride · not GPS':accuracy>65?'Weak GPS signal':'Satellite position acquired';
    setGPSStatus(accuracy>65?'wait':'ok',isDemo?'DEMO GPS':accuracy>65?'GPS LOW ACCURACY':'GPS CONNECTED');
    $('coords-text').textContent=`${Math.abs(lat).toFixed(4)}°${lat<0?'S':'N'} · ${Math.abs(lon).toFixed(4)}°${lon<0?'W':'E'}`;
    $('map-empty').hidden=true;
    $('map-marker').hidden=false;
    $('map-message').textContent=isDemo?'SIMULATED LOCATION':'LIVE GPS · NORTH UP';
    if(rideActive && Number.isFinite(currentSpeed)) trip.maxKmh=Math.max(trip.maxKmh,currentSpeed);
    if(rideActive && Number.isFinite(accuracy) && accuracy<=65){
      const last=trip.lastAccepted;
      if(!last){
        trip.lastAccepted={lat,lon,time:now};
        trip.points.push({lat,lon,ele:fix.altitude,time:now,gap:startNewSegment});startNewSegment=false;
      }else{
        const meters=haversine(last,{lat,lon}), dt=(now-last.time)/1000;
        const rate=dt>0?meters/dt*3.6:Infinity;
        // Reject GPS wander, teleportation and stale gaps. This is an estimate, not bike telemetry.
        if(dt>=0.4 && dt<31 && meters>=7 && rate<195){
          trip.distanceM+=meters;
          trip.lastAccepted={lat,lon,time:now};
          if(trip.points.length>=MAX_POINTS){toast('Track point limit reached. Export this ride before continuing.');trip.points.shift();}
          trip.points.push({lat,lon,ele:fix.altitude,time:now});
          saveTrip();
        }else if(dt>=31){trip.lastAccepted={lat,lon,time:now};trip.points.push({lat,lon,ele:fix.altitude,time:now,gap:true});}
      }
    }
    if(followPosition)mapCenter={lat,lon};
    navigation?.handleFix({lat,lon},accuracy,currentSpeed);
    drawMap();renderInstrument();
  }
  function updatePosition(p){
    if(isDemo)return;
    const c=p.coords;
    processFix({lat:c.latitude,lon:c.longitude,speed:c.speed,heading:c.heading,accuracy:c.accuracy,altitude:c.altitude,time:p.timestamp});
  }
  function startRide(){
    if(rideActive){
      rideActive=false;trip.lastAccepted=null;saveTrip(true);if(!navigation?.getState().active)releaseScreen();renderInstrument();toast('Ride paused. Trip saved on this iPhone.');return;
    }
    if(!isDemo && !beginGPS())return;
    rideActive=true;trip.lastAccepted=null;startNewSegment=trip.points.length>0;lastTimerTick=Date.now();
    holdScreen();renderInstrument();toast(isDemo?'Simulation started':'Ride started · GPS recording enabled');
  }
  function tick(){
    clock();
    const now=Date.now();
    if(rideActive && !document.hidden){
      trip.elapsedS+=Math.min(Math.max((now-lastTimerTick)/1000,0),2);
      saveTrip();
    }
    lastTimerTick=now;
    if(!isDemo && lastFixAt && now-lastFixAt>30000){setGPSStatus('error','GPS SIGNAL LOST');currentSpeed=null;}
    renderInstrument();
  }
  function initializeDemo(){
    if(GPSwatch!==null){navigator.geolocation.clearWatch(GPSwatch);GPSwatch=null;}
    isDemo=true;$('demo-badge').hidden=false;releaseScreen();
    trip=makeTrip();trip.distanceM=8700;trip.elapsedS=1164;trip.maxKmh=92;
    demoStep=0;
    const pts=interpolateDemoPath();
    trip.points=pts.slice(0,60).map((p,i)=>({...p,ele:40,time:Date.now()-(60-i)*1000}));
    const last=trip.points[trip.points.length-1];
    currentSpeed=64;currentHeading=71;
    processFix({...last,speed:64/3.6,heading:71,accuracy:5,time:Date.now()});
    if(demoInterval)clearInterval(demoInterval);
    demoInterval=setInterval(()=>{
      if(!isDemo || !rideActive)return;
      demoStep=(demoStep+1)%pts.length;
      const navDemo=navigation?.demoPoint();
      const p=navDemo||pts[(demoStep+60)%pts.length];
      processFix({...p,speed:(59+10*Math.sin(demoStep/8))/3.6,heading:navDemo?.heading??(70+20*Math.cos(demoStep/11)),accuracy:4,time:Date.now()});
    },1200);
    renderInstrument();toast('Simulation only — no real position or trip is recorded.');
  }
  function interpolateDemoPath(){
    const out=[];
    for(let i=0;i<samplesForDemo.length-1;i++){
      const a=samplesForDemo[i],b=samplesForDemo[i+1];
      for(let j=0;j<8;j++){const t=j/8;out.push({lat:a[0]+(b[0]-a[0])*t,lon:a[1]+(b[1]-a[1])*t});}
    }
    return out;
  }
  function endDemo(){
    navigation?.stop(false);
    isDemo=false;rideActive=false;if(demoInterval){clearInterval(demoInterval);demoInterval=null;}
    $('demo-badge').hidden=true;trip=loadTrip();rawFix=null;hasGPS=false;currentSpeed=null;currentHeading=null;gpsAccuracy=null;currentPosition=null;lastFixAt=0;
    mapCenter={...defaultCenter};followPosition=true;
    $('coords-text').textContent='WAITING FOR LOCATION';$('map-empty').hidden=false;$('map-marker').hidden=true;
    $('position-status').textContent='Location permission required';setGPSStatus('wait','GPS NOT STARTED');renderInstrument();drawMap();toast('Demo off. Your saved real-world trip is restored.');
  }

  // Lightweight Web Mercator slippy map. No external JS/CDN dependency.
  function projected(lat,lon,z){
    const scale=TILE_SIZE*2**z;
    const s=Math.sin(Math.max(-85.05,Math.min(85.05,lat))*Math.PI/180);
    return {x:(lon+180)/360*scale, y:(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*scale};
  }
  function unproject(x,y,z){
    const scale=TILE_SIZE*2**z;
    return {lon:x/scale*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/scale)))*180/Math.PI};
  }
  function drawMap(){
    const area=$('map-area'),layers=$('map-tiles'),rect=area.getBoundingClientRect();
    const w=rect.width,h=rect.height;if(w<1||h<1)return;
    const center=projected(mapCenter.lat,mapCenter.lon,mapZoom);
    const topLeft={x:center.x-w/2,y:center.y-h/2};
    const firstX=Math.floor(topLeft.x/TILE_SIZE),lastX=Math.ceil((topLeft.x+w)/TILE_SIZE);
    const firstY=Math.floor(topLeft.y/TILE_SIZE),lastY=Math.ceil((topLeft.y+h)/TILE_SIZE);
    const world=2**mapZoom, keep=new Set();
    for(let tx=firstX;tx<=lastX;tx++)for(let ty=firstY;ty<=lastY;ty++){
      if(ty<0||ty>=world)continue;
      const xWrapped=((tx%world)+world)%world,key=`${mapZoom}/${tx}/${ty}`,sx=Math.round(tx*TILE_SIZE-topLeft.x),sy=Math.round(ty*TILE_SIZE-topLeft.y);
      let tile=mapTiles.get(key);
      if(!tile && !PREVIEW){
        tile=new Image();tile.alt='';tile.draggable=false;tile.decoding='async';
        tile.addEventListener('error',()=>{tileErrors++;if(tileErrors===1)$('map-message').textContent='MAP TILES UNAVAILABLE — CHECK INTERNET';});
        tile.src=`https://tile.openstreetmap.org/${mapZoom}/${xWrapped}/${ty}.png`;
        layers.appendChild(tile);mapTiles.set(key,tile);
      }
      if(tile){tile.style.left=`${sx}px`;tile.style.top=`${sy}px`;keep.add(key);}
    }
    for(const [key,tile] of mapTiles){if(!keep.has(key)){tile.remove();mapTiles.delete(key);}}
    if(currentPosition){
      const p=projected(currentPosition.lat,currentPosition.lon,mapZoom);
      const marker=$('map-marker');marker.style.left=`${p.x-topLeft.x}px`;marker.style.top=`${p.y-topLeft.y}px`;
      $('marker-arrow').style.transform=`rotate(${Number.isFinite(currentHeading)?currentHeading:0}deg)`;
    }
    // Avoid redrawing thousands of track points more than necessary.
    navigation?.drawOverlay({projected,topLeft,w,h,zoom:mapZoom});
    const svg=$('route-overlay');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
    if(trip.points.length){
      let chunks=[],chunk=[];
      for(const pt of trip.points){
        const p=projected(pt.lat,pt.lon,mapZoom);
        const x=p.x-topLeft.x,y=p.y-topLeft.y;
        if(pt.gap){if(chunk.length>1)chunks.push(chunk);chunk=[];}
        if(x>-w && x<w*2 && y>-h && y<h*2){chunk.push(`${x.toFixed(1)},${y.toFixed(1)}`);}
      }
      if(chunk.length>1)chunks.push(chunk);
      const existing=svg.querySelectorAll('polyline');existing.forEach(node=>node.remove());
      for(const c of chunks){const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');line.setAttribute('fill','none');line.setAttribute('points',c.join(' '));svg.appendChild(line);}
    }else{svg.replaceChildren();}
  }
  function initMapInteractions(){
    const area=$('map-area');
    let longPress=null,pressX=0,pressY=0;
    function clearPress(){if(longPress){clearTimeout(longPress);longPress=null;}}
    area.addEventListener('pointerdown',ev=>{
      if(ev.target.closest('button,a,.nav-guidance,.map-top,.map-bottom'))return;
      clearPress();pressX=ev.clientX;pressY=ev.clientY;
      // Hold a finger for 650 ms to pin a map location. Dragging cancels the press.
      if(ev.pointerType==='touch'||ev.pointerType==='pen')longPress=setTimeout(()=>{
        longPress=null;const rect=area.getBoundingClientRect(),center=projected(mapCenter.lat,mapCenter.lon,mapZoom);
        const point=unproject(center.x+(pressX-rect.left-rect.width/2),center.y+(pressY-rect.top-rect.height/2),mapZoom);
        pointer=null;area.classList.remove('dragging');navigation?.pinDestination(point);
      },650);
      pointer={x:ev.clientX,y:ev.clientY,center:projected(mapCenter.lat,mapCenter.lon,mapZoom)};
      area.setPointerCapture(ev.pointerId);area.classList.add('dragging');
    });
    area.addEventListener('pointermove',ev=>{
      if(Math.hypot(ev.clientX-pressX,ev.clientY-pressY)>9)clearPress();
      if(!pointer)return;
      const next=unproject(pointer.center.x-(ev.clientX-pointer.x),pointer.center.y-(ev.clientY-pointer.y),mapZoom);
      mapCenter=next;followPosition=false;drawMap();
    });
    for(const evt of ['pointerup','pointercancel','lostpointercapture'])area.addEventListener(evt,()=>{clearPress();pointer=null;area.classList.remove('dragging');});
    function zoom(amount){mapZoom=Math.max(3,Math.min(18,mapZoom+amount));drawMap();}
    $('zoom-in').addEventListener('click',()=>zoom(1));$('zoom-out').addEventListener('click',()=>zoom(-1));
    $('recenter').addEventListener('click',()=>{
      if(!currentPosition){toast('Start GPS to center the map on your position.');return;}
      followPosition=true;mapCenter={...currentPosition};drawMap();
    });
    let lastPinch=null;
    area.addEventListener('touchstart',ev=>{if(ev.touches.length===2){clearPress();lastPinch=Math.hypot(ev.touches[0].clientX-ev.touches[1].clientX,ev.touches[0].clientY-ev.touches[1].clientY);pointer=null;}},{passive:true});
    area.addEventListener('touchmove',ev=>{if(ev.touches.length!==2||lastPinch===null)return;const dist=Math.hypot(ev.touches[0].clientX-ev.touches[1].clientX,ev.touches[0].clientY-ev.touches[1].clientY);if(Math.abs(dist-lastPinch)>44){zoom(dist>lastPinch?1:-1);lastPinch=dist;}},{passive:true});
    area.addEventListener('touchend',()=>{lastPinch=null;},{passive:true});
  }
  function showModal(title,kicker,content){
    $('modal-title').textContent=title;$('modal-kicker').textContent=kicker;
    $('modal-body').innerHTML=content;$('modal-backdrop').hidden=false;
  }
  function closeModal(){ $('modal-backdrop').hidden=true; }
  function musicModal(){
    showModal('Your riding soundtrack','AUDIO / HELMET',`
      <p>Control music with your Bluetooth helmet buttons, Siri or the music app itself. iOS does not let this webpage operate the playback controls of a separate music app.</p>
      <div class="modal-actions"><button class="action-btn primary" id="apple-music">APPLE MUSIC ↗</button><button class="action-btn" id="spotify-music">SPOTIFY ↗</button></div>
      <div class="modal-card"><strong>Suggested setup</strong>Pair your helmet intercom to this iPhone 13, start your playlist before the ride, then return to the dashboard. Use physical helmet controls rather than touch gestures on the road.</div>`);
    $('apple-music').addEventListener('click',()=>window.open('https://music.apple.com/my','_blank','noopener,noreferrer'));
    $('spotify-music').addEventListener('click',()=>window.open('https://open.spotify.com/','_blank','noopener,noreferrer'));
  }
  function safeFilename(){
    const d=new Date(),date=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    return `MT25-Ride-${date}`;
  }
  function downloadFile(filename,content,mime){
    const file=new File([content],filename,{type:mime});
    if(navigator.canShare?.({files:[file]})){
      navigator.share({files:[file],title:'MT-25 Ride export'}).catch(err=>{if(err.name!=='AbortError')fallbackDownload();});
    }else fallbackDownload();
    function fallbackDownload(){const url=URL.createObjectURL(file);const a=document.createElement('a');a.href=url;a.download=filename;a.style.display='none';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);}
  }
  const xmlEsc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  function exportGPX(){
    if(!trip.points.length){toast('No GPS points yet. Start a ride first.');return;}
    const xml=['<?xml version="1.0" encoding="UTF-8"?>','<gpx version="1.1" creator="MT-25 Ride" xmlns="http://www.topografix.com/GPX/1/1">',`<trk><name>${xmlEsc(safeFilename())}</name><trkseg>`];
    for(const p of trip.points){if(p.gap)xml.push('</trkseg><trkseg>');xml.push(`<trkpt lat="${p.lat.toFixed(7)}" lon="${p.lon.toFixed(7)}">${Number.isFinite(p.ele)?`<ele>${p.ele.toFixed(1)}</ele>`:''}<time>${new Date(p.time).toISOString()}</time></trkpt>`);}
    xml.push('</trkseg></trk></gpx>');downloadFile(`${safeFilename()}.gpx`,xml.join('\n'),'application/gpx+xml');
  }
  function exportCSV(){
    if(!trip.points.length){toast('No GPS points yet. Start a ride first.');return;}
    const lines=['timestamp,latitude,longitude,altitude_m,segment_gap'];
    for(const p of trip.points)lines.push(`${new Date(p.time).toISOString()},${p.lat.toFixed(7)},${p.lon.toFixed(7)},${Number.isFinite(p.ele)?p.ele.toFixed(1):''},${p.gap?'1':'0'}`);
    downloadFile(`${safeFilename()}.csv`,lines.join('\n'),'text/csv');
  }
  function tripModal(){
    showModal('Trip computer','RIDE / LOGBOOK',`
      <div class="modal-stats">
        <div><small>DISTANCE</small><b>${n1(trip.distanceM/1000)} km</b></div>
        <div><small>ELAPSED TIME</small><b>${fmtTime(trip.elapsedS)}</b></div>
        <div><small>AVERAGE</small><b>${trip.elapsedS?Math.round(trip.distanceM/1000/(trip.elapsedS/3600)):0} km/h</b></div>
        <div><small>TOP SPEED</small><b>${Math.round(trip.maxKmh)} km/h</b></div>
      </div>
      <p>${trip.points.length} location points ${isDemo?'(simulation — not exportable as a real trip)':'saved locally on this iPhone'}.</p>
      <div class="modal-actions"><button id="export-gpx" class="action-btn primary" ${isDemo?'disabled':''}>EXPORT GPX ↓</button><button id="export-csv" class="action-btn" ${isDemo?'disabled':''}>EXPORT CSV ↓</button></div>
      <button id="reset-trip" class="action-btn danger full">RESET TRIP & REMOVE TRACK</button>
      <p class="muted-note" style="margin-top:11px">GPX is suitable for opening your route in compatible map applications. Exports may reveal where you travel, so share them carefully.</p>`);
    $('export-gpx').addEventListener('click',exportGPX);
    $('export-csv').addEventListener('click',exportCSV);
    $('reset-trip').addEventListener('click',()=>{
      if(!confirm('Reset trip distance, speed and route? This cannot be undone.'))return;
      trip=makeTrip();lastSave=0;rideActive=false;currentSpeed=isDemo?64:currentSpeed;if(!navigation?.getState().active)releaseScreen();saveTrip(true);drawMap();renderInstrument();closeModal();toast('Trip cleared.');
    });
  }
  function settingsModal(){
    showModal('Dashboard settings','RIDE / CONTROLS',`
      <div class="modal-card"><strong>Display</strong>
        <label class="checkbox-line"><input type="checkbox" id="day-checkbox" ${theme==='day'?'checked':''}> Use high-contrast daytime theme</label>
        <p class="muted-note">The dashboard requests Screen Wake Lock during rides if iOS permits it. Low Power Mode or heat can override it.</p>
      </div>
      <div class="modal-card"><strong>Test without leaving home</strong>
        <p class="muted-note">Demo shows a fictional ride around Cyberjaya. It never records your location and will not overwrite your saved trip.</p>
        <button class="action-btn full demo-toggle" id="demo-btn">${isDemo?'EXIT DEMO':'START DEMO MODE'}</button>
      </div>
      <div class="modal-card"><strong>Privacy and connectivity</strong>
        <p class="muted-note">Trip recordings stay on this iPhone. The map uses OpenStreetMap, place search uses Photon, and routes use OSRM. Searching sends the search text; routing sends only the current point and selected destination to those services, not your trip history.</p>
        <p class="muted-note">The full-screen map leaves the trip computer running inside this open web app, but iOS may suspend both when the phone is locked or another app is opened. GPS needs permission and HTTPS. Foreground route guidance uses internet to plan or reroute. Tiles cannot be bulk-downloaded from OSM. Routing services are community demos: no service or traffic guarantee.</p>
      </div>
      <p class="muted-note">MT-25 Ride v3.0 · A GPS trip computer, not a vehicle diagnostic display. RPM, actual fuel level and gear position aren't available from the iPhone alone.</p>`);
    $('day-checkbox').addEventListener('change',e=>setTheme(e.target.checked?'day':'night'));
    $('demo-btn').addEventListener('click',()=>{closeModal();isDemo?endDemo():initializeDemo();});
  }
  function initEvents(){
    $('theme-btn').addEventListener('click',()=>setTheme(theme==='night'?'day':'night'));
    $('settings-btn').addEventListener('click',settingsModal);
    $('ride-btn').addEventListener('click',startRide);
    $('nav-btn').addEventListener('click',()=>navigation?.getState().active?setNavigationView(true):navigation?.openPlanner());
    $('nav-expand').addEventListener('click',()=>setNavigationView(true));
    $('nav-dashboard').addEventListener('click',()=>setNavigationView(false));
    $('nav-route-menu').addEventListener('click',()=>navigation?.openPlanner());
    $('nav-trip-toggle').addEventListener('click',()=>{
      tripOverlayOpen=!tripOverlayOpen;
      $('nav-trip-panel').hidden=!tripOverlayOpen;
      $('nav-trip-toggle').setAttribute('aria-expanded',String(tripOverlayOpen));
      renderNavTrip();
    });
    $('nav-trip-record').addEventListener('click',startRide);
    $('music-btn').addEventListener('click',musicModal);
    $('trips-btn').addEventListener('click',tripModal);
    $('modal-close').addEventListener('click',closeModal);
    $('modal-backdrop').addEventListener('click',e=>{if(e.target===$('modal-backdrop'))closeModal();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
    document.addEventListener('visibilitychange',()=>{
      lastTimerTick=Date.now();
      if(!document.hidden && (rideActive||navigation?.getState().active))holdScreen();
      if(document.hidden){trip.lastAccepted=null;startNewSegment=trip.points.length>0;saveTrip(true);}
    });
    window.addEventListener('pagehide',()=>saveTrip(true));
    let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(drawMap,100);});
  }
  function init(){
    navigation=window.MT25Navigation.create({
      getPosition:()=>currentPosition,getAccuracy:()=>gpsAccuracy,getSpeed:()=>currentSpeed,
      beginGPS,isDemo:()=>isDemo,drawMap,showModal,closeModal,toast,
      onNavState:active=>{
        if(active){
          // Navigation automatically records the ride without requiring the dashboard to stay visible.
          // If the rider later pauses manually, the trip stays paused until resumed.
          if(!rideActive)startRide();
          setNavigationView(true);
          holdScreen();
        }else{
          setNavigationView(false);
          if(!rideActive)releaseScreen();
        }
      }
    });
    setTheme(theme);clock();addTicks();initEvents();initMapInteractions();if(PREVIEW)document.documentElement.classList.add('preview-map');drawMap();
    renderInstrument();setInterval(tick,1000);
    if(DEMO)initializeDemo();
    if('serviceWorker'in navigator && (location.protocol==='https:' || location.hostname==='localhost')){
      navigator.serviceWorker.register('./sw.js').catch(()=>{});
    }
  }
  init();
})();
