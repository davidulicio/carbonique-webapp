/* Only cache the neutral application shell and local assets. Never cache API replies. */
const CACHE = "carbonique-shell-v11";
const ASSETS = ["/static/hub/offline-state.js","/static/hub/record-resources.js", "/static/hub/vendor/pdfjs/standard_fonts/FoxitDingbats.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixed.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedBold.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedBoldItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerif.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifBold.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifBoldItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSymbol.pfb", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Bold.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-BoldItalic.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Italic.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Regular.ttf", "/static/hub/monitor.js", "/static/hub/pdf-viewer.js", "/static/hub/vendor/pdfjs/pdf.mjs", "/static/hub/vendor/pdfjs/pdf.worker.mjs", "/static/hub/resources.css", "/static/hub/resources.js", "/static/hub/fonts.css", "/static/hub/fonts/carbonique-1.ttf", "/static/hub/fonts/carbonique-2.ttf", "/static/hub/fonts/carbonique-3.ttf", "/static/hub/fonts/carbonique-4.ttf", "/static/hub/fonts/carbonique-5.ttf", "/static/hub/fonts/carbonique-6.ttf", "/static/hub/fonts/carbonique-7.ttf", "/static/hub/fonts/carbonique-8.ttf", "/static/hub/fonts/carbonique-9.ttf", "/static/hub/app.js","/static/hub/processing-files.js", "/static/hub/storage.js", "/static/hub/style.css", "/static/hub/logo.svg", "/static/hub/icon.svg", "/static/hub/ecoflux-winter.png", "/static/hub/carbonique-icon-32.png", "/static/hub/carbonique-icon-180.png", "/static/hub/carbonique-icon-192.png", "/static/hub/carbonique-icon-512.png", "/manifest.webmanifest"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const cache=await caches.open(CACHE);
    const oldKeys=(await caches.keys()).filter(key=>key.startsWith("carbonique-shell-")&&key!==CACHE);
    // Keep the already prepared neutral shell when upgrading the assets.
    // Site records and pending operations remain in account-scoped IndexedDB.
    if(!await cache.match("/")){
      for(const key of oldKeys.reverse()){
        const shell=await (await caches.open(key)).match("/");
        if(shell){await cache.put("/",shell);break;}
      }
    }
    await Promise.all(oldKeys.map(key=>caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener("message", event => {
  if (event.data === "CACHE_SHELL") event.waitUntil(caches.open(CACHE).then(async cache => {
    const response = await fetch("/", {credentials: "same-origin"});
    if (!response.ok || new URL(response.url).pathname !== "/") throw new Error("Sign in again before preparing the app for offline use.");
    await cache.put("/", response);
    event.ports[0]?.postMessage({ok:true});
  }).catch(error => event.ports[0]?.postMessage({ok:false,error:error.message})));
  if (event.data === "CLEAR_SHELL") event.waitUntil(caches.open(CACHE).then(cache => cache.delete("/")));
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/" && event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).then(async response => {
      if (response.ok && new URL(response.url).pathname === "/") (await caches.open(CACHE)).put("/", response.clone());
      return response;
    }).catch(async () => (await caches.match("/")) || new Response("Open Carbonique online and prepare your sites before going offline.", {status: 503, headers: {"Content-Type": "text/plain"}})));
  } else if (ASSETS.includes(url.pathname)) {
    event.respondWith(fetch(event.request).then(async response => {
      if (response.ok) await (await caches.open(CACHE)).put(event.request, response.clone());
      return response;
    }).catch(() => caches.match(event.request)));
  }
});
