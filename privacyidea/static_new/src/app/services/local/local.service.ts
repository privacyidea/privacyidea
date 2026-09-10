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

export interface LocalServiceInterface {
  key: string;

  saveData(key: string, value: string): void;

  getData(key: string): string;

  removeData(key: string): void;

  usePersistence(persistence: SessionPersistence): void;

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
  private storage: Storage = LocalService.findSessionStorage();

  public saveData(key: string, value: string) {
    this.storage.setItem(key, this.encrypt(value));
  }

  public getData(key: string) {
    const data = this.storage.getItem(key) || "";
    return this.decrypt(data);
  }

  public removeData(key: string) {
    this.storage.removeItem(key);
  }

  /**
   * Point the session at the storage the given persistence selects. Whatever the other storage
   * still holds is dropped, so a login never leaves a second, stale session behind for
   * findSessionStorage() to pick up later.
   */
  public usePersistence(persistence: SessionPersistence): void {
    const target = persistence === "browser" ? localStorage : sessionStorage;
    const other = target === localStorage ? sessionStorage : localStorage;
    SESSION_KEYS.forEach((key) => other.removeItem(key));
    this.storage = target;
  }

  /** Clears the session from both storages: it may sit in either one after a policy change. */
  public clearSession(): void {
    SESSION_KEYS.forEach((key) => {
      sessionStorage.removeItem(key);
      localStorage.removeItem(key);
    });
  }

  // A tab-scoped session wins over a browser-scoped one, so that narrowing the policy takes
  // effect on the next login even while an older shared session is still on disk.
  private static findSessionStorage(): Storage {
    if (sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return sessionStorage;
    }
    if (localStorage.getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return localStorage;
    }
    return sessionStorage;
  }

  private encrypt(txt: string): string {
    return CryptoJS.AES.encrypt(txt, this.key).toString();
  }

  private decrypt(txtToDecrypt: string) {
    return CryptoJS.AES.decrypt(txtToDecrypt, this.key).toString(CryptoJS.enc.Utf8);
  }
}
