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
import { AUTH_DATA_STORAGE_KEY, AUTH_SESSION_MODE_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import {
  AuthSessionMode,
  AuthSessionModeService,
  isAuthSessionMode,
  isMultiTabMode
} from "./auth-session-mode.service";

describe("AuthSessionModeService", () => {
  let authService: MockAuthService;
  const originalDefault = environment.defaultAuthSessionMode;

  function createService(stored?: AuthSessionMode | string): AuthSessionModeService {
    if (stored !== undefined) {
      localStorage.setItem(AUTH_SESSION_MODE_STORAGE_KEY, stored);
    }
    TestBed.resetTestingModule();
    authService = new MockAuthService();
    TestBed.configureTestingModule({
      providers: [{ provide: AuthService as Type<unknown>, useValue: authService }]
    });
    return TestBed.inject(AuthSessionModeService);
  }

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    environment.defaultAuthSessionMode = originalDefault;
  });

  afterEach(() => {
    environment.defaultAuthSessionMode = originalDefault;
  });

  describe("resolving the active mode", () => {
    it("falls back to the deployment default when nothing is stored", () => {
      environment.defaultAuthSessionMode = "multi-tab-ephemeral";
      expect(createService().mode()).toBe("multi-tab-ephemeral");
    });

    it("prefers a stored mode over the deployment default", () => {
      environment.defaultAuthSessionMode = "single-tab";
      expect(createService("multi-tab-persistent").mode()).toBe("multi-tab-persistent");
    });

    it("ignores a stored value that is not a known mode", () => {
      environment.defaultAuthSessionMode = "single-tab";
      expect(createService("something-else").mode()).toBe("single-tab");
    });
  });

  describe("storage selection", () => {
    it("uses localStorage only for multi-tab-persistent", () => {
      expect(createService("multi-tab-persistent").storage()).toBe(localStorage);
    });

    it("uses sessionStorage for the other modes", () => {
      expect(createService("single-tab").storage()).toBe(sessionStorage);
      localStorage.clear();
      expect(createService("multi-tab-ephemeral").storage()).toBe(sessionStorage);
    });
  });

  describe("startup cleanup", () => {
    it("drops a session left in localStorage when the mode does not use it", () => {
      localStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "stale");
      localStorage.setItem(AUTH_DATA_STORAGE_KEY, "stale");
      createService("single-tab");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
      expect(localStorage.getItem(AUTH_DATA_STORAGE_KEY)).toBeNull();
    });

    it("drops a session left in sessionStorage under multi-tab-persistent", () => {
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "stale");
      createService("multi-tab-persistent");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("keeps the session that the active mode does use", () => {
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "keep");
      createService("single-tab");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("keep");
    });
  });

  describe("setMode", () => {
    it("does nothing unless an admin is signed in", () => {
      const service = createService("single-tab");
      authService.role.set("user");
      service.setMode("multi-tab-persistent");
      expect(service.mode()).toBe("single-tab");
      expect(localStorage.getItem(AUTH_SESSION_MODE_STORAGE_KEY)).toBe("single-tab");
    });

    it("does nothing while nobody is signed in", () => {
      const service = createService("single-tab");
      authService.isAuthenticated.set(false);
      service.setMode("multi-tab-persistent");
      expect(service.mode()).toBe("single-tab");
    });

    it("stores the new mode for a signed-in admin", () => {
      const service = createService("single-tab");
      service.setMode("multi-tab-ephemeral");
      expect(service.mode()).toBe("multi-tab-ephemeral");
      expect(localStorage.getItem(AUTH_SESSION_MODE_STORAGE_KEY)).toBe("multi-tab-ephemeral");
    });

    it("moves the running session into the storage of the new mode", () => {
      const service = createService("single-tab");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      service.setMode("multi-tab-persistent");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("token");
      expect(localStorage.getItem(AUTH_DATA_STORAGE_KEY)).toBe("data");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("leaves the session in place when both modes share a storage", () => {
      const service = createService("single-tab");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      service.setMode("multi-tab-ephemeral");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("token");
    });

    it("notifies the registered listener", () => {
      const service = createService("single-tab");
      const listener = jest.fn();
      service.addModeChangeListener(listener);
      service.setMode("multi-tab-ephemeral");
      expect(listener).toHaveBeenCalledWith("multi-tab-ephemeral");
    });

    it("does not notify the listener when the change is rejected", () => {
      const service = createService("single-tab");
      const listener = jest.fn();
      service.addModeChangeListener(listener);
      authService.isAuthenticated.set(false);
      service.setMode("multi-tab-ephemeral");
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe("setDefaultMode", () => {
    it("writes the deployment default as an explicit choice", () => {
      environment.defaultAuthSessionMode = "single-tab";
      const service = createService("multi-tab-persistent");
      service.setDefaultMode();
      expect(service.mode()).toBe("single-tab");
      expect(localStorage.getItem(AUTH_SESSION_MODE_STORAGE_KEY)).toBe("single-tab");
    });
  });

  describe("adoptMode", () => {
    it("takes over the mode without notifying the listener", () => {
      const service = createService("single-tab");
      const listener = jest.fn();
      service.addModeChangeListener(listener);
      service.adoptMode("multi-tab-persistent");
      expect(service.mode()).toBe("multi-tab-persistent");
      expect(listener).not.toHaveBeenCalled();
    });

    it("discards the session held in the previous storage", () => {
      const service = createService("single-tab");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "own");
      service.adoptMode("multi-tab-persistent");
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
    });

    it("applies even without a signed-in admin", () => {
      const service = createService("single-tab");
      authService.isAuthenticated.set(false);
      service.adoptMode("multi-tab-ephemeral");
      expect(service.mode()).toBe("multi-tab-ephemeral");
    });
  });

  describe("guards", () => {
    it("recognises the three known modes", () => {
      expect(isAuthSessionMode("single-tab")).toBe(true);
      expect(isAuthSessionMode("multi-tab-ephemeral")).toBe(true);
      expect(isAuthSessionMode("multi-tab-persistent")).toBe(true);
    });

    it("rejects anything else", () => {
      expect(isAuthSessionMode("per-tab")).toBe(false);
      expect(isAuthSessionMode(null)).toBe(false);
      expect(isAuthSessionMode(undefined)).toBe(false);
      expect(isAuthSessionMode(1)).toBe(false);
    });

    it("treats both multi-tab modes as shared", () => {
      expect(isMultiTabMode("single-tab")).toBe(false);
      expect(isMultiTabMode("multi-tab-ephemeral")).toBe(true);
      expect(isMultiTabMode("multi-tab-persistent")).toBe(true);
    });
  });
});
