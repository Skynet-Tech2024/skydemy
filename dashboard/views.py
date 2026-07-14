from django.http import HttpResponse
from django.views.decorators.cache import never_cache

@never_cache
def service_worker(request):
    content = '''
// Service Worker for SKYDEMY PWA
const CACHE_NAME = 'skydemy-v1';
const urlsToCache = [
    '/',
    '/static/images/logo.png',
    '/static/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        return caches.delete(name);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => response || fetch(event.request))
    );
});
'''
    return HttpResponse(content.strip(), content_type='application/javascript')