import {clearAccount, get} from "./storage.js";

const status = document.querySelector("#sign-out-status");
const account = Number(status.dataset.account);
const session = status.dataset.session;
const event = {account, session, logout:true, nonce:crypto.randomUUID()};
if ("BroadcastChannel" in window) {
  const channel = new BroadcastChannel("carbonique-workspace-session");
  channel.postMessage(event);
  channel.close();
}
try { localStorage.setItem("carbonique-session-event", JSON.stringify(event)); } catch {}
try {
  if (await get("meta", `${account}:session`) === session) {
    await clearAccount(account, session, {preservePending:true});
    status.textContent = "Offline site copies were cleared. Pending records remain with this account.";
  } else {
    status.textContent = "Sign in to the workspace to review offline copies saved by earlier sessions.";
  }
} catch {
  status.textContent = "Offline copies could not be cleared. Sign in to the workspace to manage them.";
}
