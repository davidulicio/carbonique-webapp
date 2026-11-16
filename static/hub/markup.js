import DOMPurify from "./vendor/purify.es.mjs";

export function rich(text) {
  return DOMPurify.sanitize(text || "", {
    ALLOWED_TAGS: ["p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "a", "code",
      "pre", "blockquote", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td"],
    ALLOWED_ATTR: ["href", "title"],
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:)/i,
    ALLOW_DATA_ATTR: false,
    ALLOW_ARIA_ATTR: false,
  });
}

export function setMarkup(element, markup) {
  element.innerHTML = DOMPurify.sanitize(markup, {
    USE_PROFILES: {html: true, svg: true},
    ADD_ATTR: ["target"],
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed"],
    FORBID_ATTR: ["action", "formaction", "srcset"],
    RETURN_TRUSTED_TYPE: true,
  });
}

const workerPaths = new Set(["/sw.js", "/static/hub/vendor/pdfjs/pdf.worker.mjs"]);
const workerPolicy = globalThis.trustedTypes?.createPolicy("carbonique-worker", {
  createScriptURL(path) {
    if (!workerPaths.has(path)) throw new TypeError("Unexpected Carbonique worker URL.");
    return path;
  },
});

export function workerURL(path) {
  if (!workerPaths.has(path)) throw new TypeError("Unexpected Carbonique worker URL.");
  return workerPolicy?.createScriptURL(path) ?? path;
}
