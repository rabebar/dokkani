const CACHE = 'dokkani-v3';
const STATIC_ASSETS = ['/', '/shop', '/cart', '/static/manifest.json'];

const CACHE_PATTERNS = [
  /\/static\//,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/,
  /\/category\//,
  /\/subcategory\//
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if(e.request.method !== 'GET') return;
  
  const url = new URL(e.request.url);
  const shouldCache = CACHE_PATTERNS.some(p => p.test(url.href));
  
  e.respondWith(
    caches.match(e.request).then(cached => {
      if(cached) return cached;
      
      return fetch(e.request).then(res => {
        if(!res || res.status !== 200) return res;
        
        if(shouldCache) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => cached);
    })
  );
});