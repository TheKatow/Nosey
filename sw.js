const CACHE_NAME = 'nosey-cache-v1';
const STATIC_ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

// Installation du Service Worker et mise en cache du shell statique
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Nettoyage des anciens caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Stratégie de requête : Network-First pour fiches.json, Cache-First pour les assets
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Pour la base de données fiches.json : toujours chercher sur le réseau pour la fraîcheur
  if (url.pathname.includes('fiches.json')) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  // Pour les autres fichiers statiques : Cache d'abord, puis Réseau
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      return cachedResponse || fetch(e.request);
    })
  );
});