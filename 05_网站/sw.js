const CACHE = 'chempredict-v4-4.4.0';
const ASSETS = [
  './', './index.html', './index-v44.html', './styles-v44.css', './model-v44.js', './app-v44.js',
  './assets/registries.js', './assets/model_artifact.js', './manifest.webmanifest', './icon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)),
  )));
});

self.addEventListener('fetch', (event) => {
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
