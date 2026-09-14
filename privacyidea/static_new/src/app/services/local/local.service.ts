/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Injectable } from "@angular/core";
import { AUTH_DATA_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { SessionPersistence } from "@core/session-persistence";
import { environment } from "@env/environment";
import * as CryptoJS from "crypto-js";

const SESSION_KEYS = [BEARER_TOKEN_STORAGE_KEY, AUTH_DATA_STORAGE_KEY];

const STORAGE_PROBE_KEY = "pi_storage_probe";

/**
 * Stands in for a web storage the browser refuses to hand out -- site data blocked, or a
 * sandboxed frame, where even reading `sessionStorage` throws. The session then lives for as
 * long as the page does, which loses a reload but keeps the WebUI usable.
 */
class MemoryStorage implements Storage {
  private readonly entries = new Map<string, string>();

  get length(): number {
    return this.entries.size;
  }

  clear(): void {
    this.entries.clear();
  }

  getItem(key: string): string | null {
    return this.entries.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.entries.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.entries.delete(key);
  }

  setItem(key: string, value: string): void {
    this.entries.set(key, value);
  }
}

const memoryStorage = new MemoryStorage();
const resolved = new Map<SessionPersistence, Storage>();

function storageFor(persistence: SessionPersistence): Storage {
  const cached = resolved.get(persistence);
  if (cached) {
    return cached;
  }
  let storage: Storage;
  try {
    const candidate = persistence === "browser" ? localStorage : sessionStorage;
    // Some browsers hand out the object and refuse the write, so the probe has to write.
    candidate.setItem(STORAGE_PROBE_KEY, "1");
    candidate.removeItem(STORAGE_PROBE_KEY);
    storage = candidate;
  } catch {
    storage = memoryStorage;
  }
  resolved.set(persistence, storage);
  return storage;
}

export interface LocalServiceInterface {
  key: string;

  saveData(key: string, value: string): void;

  getData(key: string): string;

  removeData(key: string): void;

  usePersistence(persistence: SessionPersistence): void;

  inactiveSessionToken(): string;

  clearInactiveSession(): void;

  clearSession(): void;
}

@Injectable({
  providedIn: "root"
})
export class LocalService implements LocalServiceInterface {
  key = environment.secretAESKey;

  // The storage a session is found in is the storage it keeps for the life of the page: the
  // policy value arrives with the /auth response, so it applies to the next login rather than
  // moving a running session from under the tabs that share it.
  private persistence: SessionPersistence = LocalService.findSessionPersistence();

  public saveData(key: string, value: string) {
    this.storage().setItem(key, this.encrypt(value));
  }

  public getData(key: string) {
    const data = this.storage().getItem(key) || "";
    return this.decrypt(data);
  }

  public removeData(key: string) {
    this.storage().removeItem(key);
  }

  /** Points the session at the storage the given persistence selects. */
  public usePersistence(persistence: SessionPersistence): void {
    this.persistence = persistence;
  }

  /**
   * The bearer token the storage this tab does not use still holds, or "" if it holds none.
   * It belongs to another session -- another tab's, or one from before the policy changed -- so
   * only its owner may drop it; see clearInactiveSession().
   */
  public inactiveSessionToken(): string {
    return this.decrypt(this.inactiveStorage().getItem(BEARER_TOKEN_STORAGE_KEY) || "");
  }

  public clearInactiveSession(): void {
    const inactive = this.inactiveStorage();
    SESSION_KEYS.forEach((key) => inactive.removeItem(key));
  }

  /** Clears the session from the storage holding it, and only from that one. */
  public clearSession(): void {
    const storage = this.storage();
    SESSION_KEYS.forEach((key) => storage.removeItem(key));
  }

  private storage(): Storage {
    return storageFor(this.persistence);
  }

  private inactiveStorage(): Storage {
    return storageFor(this.persistence === "browser" ? "tab" : "browser");
  }

  // A tab-scoped session wins over a browser-scoped one, so that narrowing the policy takes
  // effect on the next login even while an older shared session is still on disk.
  private static findSessionPersistence(): SessionPersistence {
    if (storageFor("tab").getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return "tab";
    }
    if (storageFor("browser").getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return "browser";
    }
    return "tab";
  }

  private encrypt(txt: string): string {
    return CryptoJS.AES.encrypt(txt, this.key).toString();
  }

  private decrypt(txtToDecrypt: string) {
    return CryptoJS.AES.decrypt(txtToDecrypt, this.key).toString(CryptoJS.enc.Utf8);
  }
}
