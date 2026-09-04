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
import { Type } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { AuthSessionModeService } from "@services/auth-session-mode/auth-session-mode.service";
import { MockAuthSessionModeService } from "@testing/mock-services/mock-auth-session-mode-service";
import { LocalService } from "./local.service";

describe("LocalService", () => {
  let localService: LocalService;
  let modeService: MockAuthSessionModeService;

  function createService(): LocalService {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: AuthSessionModeService as Type<unknown>, useValue: modeService }]
    });
    return TestBed.inject(LocalService);
  }

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    modeService = new MockAuthSessionModeService();
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

  describe("follows the session mode", () => {
    it("writes to sessionStorage outside multi-tab-persistent", () => {
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBeNull();
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("writes to localStorage under multi-tab-persistent", () => {
      modeService.setMode("multi-tab-persistent");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "a-token");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).not.toBeNull();
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("resolves the storage per call rather than capturing it once", () => {
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "in-session");
      modeService.setMode("multi-tab-persistent");
      expect(localService.getData(BEARER_TOKEN_STORAGE_KEY)).toBe("");
      localService.saveData(BEARER_TOKEN_STORAGE_KEY, "in-local");
      expect(localService.getData(BEARER_TOKEN_STORAGE_KEY)).toBe("in-local");
    });
  });
});
