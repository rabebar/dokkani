const CACHE = 'dokkani-v5-core-categories';

const STATIC_CACHE_PATTERNS = [
  /\/static\//,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/
];

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if(e.request.method !== 'GET') return;
  
  const url = new URL(e.request.url);
  const isDynamicPage =
    e.request.mode === 'navigate' ||
    url.pathname === '/' ||
    url.pathname === '/shop' ||
    url.pathname.startsWith('/category/') ||
    url.pathname.startsWith('/subcategory/') ||
    url.pathname.startsWith('/api/');

  if(isDynamicPage) {
    e.respondWith(fetch(e.request, { cache: 'no-store' }));
    return;
  }

  const shouldCache = STATIC_CACHE_PATTERNS.some(p => p.test(url.href));

  if(!shouldCache) return;
  
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
