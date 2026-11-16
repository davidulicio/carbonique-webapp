const loginButton = document.querySelector("#passkey-sign-in");
const registration = document.querySelector("#passkey-register");
const status = document.querySelector("#passkey-status");
const serverToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

async function post(path, body) {
  const headers = {"X-CSRFToken": serverToken};
  if (typeof body === "string") headers["Content-Type"] = "application/json";
  const response = await fetch(path, {method:"POST", headers, body, credentials:"same-origin"});
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || "Could not complete the passkey request. Reload and try again.");
  return result;
}

async function ceremony(control, body, create) {
  const submit = create ? control.querySelector("button") : control;
  submit.disabled = true;
  status.textContent = create ? "Waiting for passkey setup…" : "Waiting for your passkey…";
  try {
    const {id, options} = await post(control.dataset.options, body);
    const label = create ? body.get("label") : undefined;
    if (create) body.delete("password");
    const credential = await (create
      ? navigator.credentials.create({publicKey: PublicKeyCredential.parseCreationOptionsFromJSON(options)})
      : navigator.credentials.get({publicKey: PublicKeyCredential.parseRequestOptionsFromJSON(options)}));
    if (!credential) throw new Error("No passkey was selected.");
    const result = await post(control.dataset.complete, JSON.stringify({id, label, credential: credential.toJSON()}));
    location.assign(result.redirect);
  } catch (error) {
    status.textContent = error instanceof DOMException
      ? "The passkey request did not finish. Try again or use your password."
      : error.message;
  } finally {
    submit.disabled = false;
  }
}

const browserSupports = (method) => window.isSecureContext &&
  typeof window.PublicKeyCredential?.[method] === "function" &&
  typeof PublicKeyCredential.prototype.toJSON === "function";
if (loginButton && browserSupports("parseRequestOptionsFromJSON")) {
  loginButton.hidden = false;
  loginButton.addEventListener("click", () => ceremony(loginButton, undefined, false));
}
if (registration) {
  if (browserSupports("parseCreationOptionsFromJSON")) {
    registration.hidden = false;
    registration.addEventListener("submit", event => {
      event.preventDefault();
      const body = new FormData(registration);
      registration.elements.password.value = "";
      void ceremony(registration, body, true);
    });
  } else {
    status.textContent = "Use a browser that supports passkeys to add a new one.";
  }
}
