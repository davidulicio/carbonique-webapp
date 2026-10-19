const DB_NAME = "carbonique-hub-v1";
let opening;
function database() {
  if (!opening) opening = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      for (const name of ["meta", "snapshots", "outbox", "downloads"]) request.result.createObjectStore(name);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  return opening;
}
async function transact(store, mode, callback) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    let result;
    const req = callback(tx.objectStore(store));
    if (req) req.onsuccess = () => { result = req.result; };
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("Local storage transaction aborted."));
  });
}
export const get = (store, key) => transact(store, "readonly", s => s.get(key));
export const put = (store, key, value) => transact(store, "readwrite", s => s.put(value, key));
export const remove = (store, key) => transact(store, "readwrite", s => s.delete(key));
export const all = store => transact(store, "readonly", s => s.getAll());
export async function clearDevice() {
  const db = await database();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(["meta", "snapshots", "outbox", "downloads"], "readwrite");
    for (const name of tx.objectStoreNames) tx.objectStore(name).clear();
    tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
  });
}
