/* Offline application shell. Map tiles are deliberately not cached or prefetched by the service worker. */
const CACHE = 'mt25-ride-shell-v2';
const SHELL = ['./','./index.html','./styles.css','./app.js','./navigation.js','./manifest.webmanifest','./icons/icon.svg','./icons/icon-192.png','./icons/icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if(url.origin!==self.location.origin || event.request.method!=='GET') return; // No interference with OSM browser cache.
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok && SHELL.some(path=>new URL(path,self.registration.scope).pathname===url.pathname)){
      const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));
    }
    return response;
  }).catch(async()=>{const cached=await caches.match(event.request);return cached||(event.request.mode==='navigate'?caches.match('./index.html'):Response.error());}));
});
