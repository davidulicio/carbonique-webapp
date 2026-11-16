/* Only cache the neutral offline shell and local assets. */
const CACHE = "carbonique-shell-v12";
const SHELL = "/offline-shell/";
const ASSETS = ["/static/hub/offline-state.js","/static/hub/record-resources.js", "/static/hub/vendor/pdfjs/standard_fonts/FoxitDingbats.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixed.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedBold.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedBoldItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitFixedItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerif.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifBold.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifBoldItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSerifItalic.pfb", "/static/hub/vendor/pdfjs/standard_fonts/FoxitSymbol.pfb", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Bold.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-BoldItalic.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Italic.ttf", "/static/hub/vendor/pdfjs/standard_fonts/LiberationSans-Regular.ttf", "/static/hub/monitor.js", "/static/hub/pdf-viewer.js", "/static/hub/vendor/pdfjs/pdf.mjs", "/static/hub/vendor/pdfjs/pdf.worker.mjs", "/static/hub/resources.css", "/static/hub/resources.js", "/static/hub/fonts.css", "/static/hub/fonts/carbonique-1.ttf", "/static/hub/fonts/carbonique-2.ttf", "/static/hub/fonts/carbonique-3.ttf", "/static/hub/fonts/carbonique-4.ttf", "/static/hub/fonts/carbonique-5.ttf", "/static/hub/fonts/carbonique-6.ttf", "/static/hub/fonts/carbonique-7.ttf", "/static/hub/fonts/carbonique-8.ttf", "/static/hub/fonts/carbonique-9.ttf", "/static/hub/app.js","/static/hub/processing-files.js", "/static/hub/storage.js", "/static/hub/style.css", "/static/hub/logo.svg", "/static/hub/icon.svg", "/static/hub/ecoflux-winter.png", "/static/hub/carbonique-icon-32.png", "/static/hub/carbonique-icon-180.png", "/static/hub/carbonique-icon-192.png", "/static/hub/carbonique-icon-512.png", "/manifest.webmanifest", "/static/hub/markup.js", "/static/hub/vendor/purify.es.mjs"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const oldKeys = (await caches.keys()).filter(key => key.startsWith("carbonique-shell-") && key !== CACHE);
    // Previous versions cached the authenticated home response. Drop those copies.
    await Promise.all(oldKeys.map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener("message", event => {
  if (event.data !== "PREPARE_OFFLINE_SHELL") return;
  event.waitUntil((async () => {
    try {
      const response = await fetch(SHELL, {credentials:"omit", cache:"no-store", redirect:"error"});
      if (!response.ok) throw new Error("The offline app could not be downloaded.");
      await (await caches.open(CACHE)).put(SHELL, response);
      event.ports[0]?.postMessage({ok:true});
    } catch {
      event.ports[0]?.postMessage({ok:false, error:"Could not save the offline app. Try again while connected."});
    }
  })());
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/" && event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(async () =>
      (await caches.open(CACHE)).match(SHELL).then(shell => shell || new Response(
        "Open Carbonique online and prepare your sites before going offline.",
        {status:503, headers:{"Content-Type":"text/plain"}},
      )),
    ));
  } else if (ASSETS.includes(url.pathname)) {
    event.respondWith(fetch(event.request).then(async response => {
      if (response.ok) await (await caches.open(CACHE)).put(event.request, response.clone());
      return response;
    }).catch(async () => (await caches.open(CACHE)).match(event.request)));
  }
});
