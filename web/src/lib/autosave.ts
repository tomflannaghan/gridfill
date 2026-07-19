/** Auto-save the current document to browser storage (IndexedDB, since a
 * document's embedded image can be several megabytes — too large for
 * `localStorage`'s ~5-10MB quota) so reopening the page resumes exactly where
 * the user left off, without an explicit Save. Best-effort: storage failures
 * (unavailable, blocked, private browsing) are swallowed rather than
 * surfaced — the explicit `.cwd` Save remains the source of truth.
 */

import type { Cwd } from "../model/cwd.ts";

export interface AutosaveRecord {
  doc: Cwd;
  fileName: string | null;
}

/** A minimal async key-value store, so the IndexedDB-backed default can be
 * swapped for an in-memory fake in tests. */
export interface KeyValueStore {
  get(key: string): Promise<unknown>;
  set(key: string, value: unknown): Promise<void>;
  delete(key: string): Promise<void>;
}

const DB_NAME = "gridfill-autosave";
const STORE_NAME = "document";
const KEY = "current";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE_NAME);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error as Error);
  });
}

function idbGet(key: string): Promise<unknown> {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const req = db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME).get(key);
        req.onsuccess = () => {
          db.close();
          resolve(req.result);
        };
        req.onerror = () => {
          db.close();
          reject(req.error as Error);
        };
      }),
  );
}

function idbPut(key: string, value: unknown): Promise<void> {
  return openDb().then(
    (db) =>
      new Promise<void>((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readwrite");
        tx.objectStore(STORE_NAME).put(value, key);
        tx.oncomplete = () => {
          db.close();
          resolve();
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error as Error);
        };
      }),
  );
}

function idbDelete(key: string): Promise<void> {
  return openDb().then(
    (db) =>
      new Promise<void>((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readwrite");
        tx.objectStore(STORE_NAME).delete(key);
        tx.oncomplete = () => {
          db.close();
          resolve();
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error as Error);
        };
      }),
  );
}

const indexedDbStore: KeyValueStore = { get: idbGet, set: idbPut, delete: idbDelete };

/** Persist `doc` as the document to resume next time. */
export async function saveAutosave(
  doc: Cwd,
  fileName: string | null,
  store: KeyValueStore = indexedDbStore,
): Promise<void> {
  try {
    await store.set(KEY, { doc, fileName } satisfies AutosaveRecord);
  } catch {
    // Autosave is best-effort; ignore storage failures.
  }
}

/** Load the previously auto-saved document, if any. */
export async function loadAutosave(
  store: KeyValueStore = indexedDbStore,
): Promise<AutosaveRecord | null> {
  try {
    const value = await store.get(KEY);
    return (value as AutosaveRecord | undefined) ?? null;
  } catch {
    return null;
  }
}

/** Clear the auto-saved document (e.g. once it's been explicitly closed). */
export async function clearAutosave(store: KeyValueStore = indexedDbStore): Promise<void> {
  try {
    await store.delete(KEY);
  } catch {
    // Autosave is best-effort; ignore storage failures.
  }
}
