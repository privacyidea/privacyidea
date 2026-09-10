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
import { TestBed } from "@angular/core/testing";
import { AUTH_DATA_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { LocalService } from "./local.service";

describe("LocalService", () => {
  let localService: LocalService;

  function createService(): LocalService {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [] });
    return TestBed.inject(LocalService);
  }

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    localService = createService();
  });

  it("should be created", () => {
    expect(localService).toBeTruthy();
  });

  it("stores a value that reads back unchanged", () => {
    localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
    expect(localService.getData(BEARER_TOKEN_STORAGE_KEY)).toBe("a-token");
  });

  it("does not keep the value in clear text", () => {
    localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
    expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBe("a-token");
  });

  it("returns an empty string for a key that was never written", () => {
    expect(localService.getData("absent")).toBe("");
  });

  it("removes a stored value", () => {
    localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
    localService.removeData(BEARER_TOKEN_STORAGE_KEY);
    expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
  });

  describe("follows the session persistence the server sends", () => {
    it("keeps a tab session out of localStorage", () => {
      localService.usePersistence("tab");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBeNull();
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("puts a browser session in localStorage, where the other tabs find it", () => {
      localService.usePersistence("browser");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBeNull();
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("drops what the other storage held, so no stale session is left to find", () => {
      localService.usePersistence("browser");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "old-token");
      localService.saveData(AUTH_DATA_STORAGE_KEY, "old-data");

      localService.usePersistence("tab");

      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
      expect(localStorage.getItem(AUTH_DATA_STORAGE_KEY)).toBeNull();
    });
  });

  describe("finds an existing session on construction", () => {
    it("uses the browser session when this tab has none of its own", () => {
      localService.usePersistence("browser");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "shared-token");

      expect(createService().getData(BEARER_TOKEN_STORAGE_KEY)).toBe("shared-token");
    });

    it("prefers the tab's own session over a browser session left on disk", () => {
      localService.usePersistence("browser");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "stale-token");
      // Written straight to sessionStorage: usePersistence would have cleared the other one.
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)!);
      localStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "other");

      const fresh = createService();
      fresh.saveData(BEARER_TOKEN_STORAGE_KEY, "tab-token");

      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBeNull();
      expect(fresh.getData(BEARER_TOKEN_STORAGE_KEY)).toBe("tab-token");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("other");
    });
  });

  it("clears the session from both storages", () => {
    localService.usePersistence("browser");
    localService.saveData(BEARER_TOKEN_STORAGE_KEY, "in-local");
    sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "in-session");

    localService.clearSession();

    expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem(AUTH_DATA_STORAGE_KEY)).toBeNull();
  });
});
