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
import { AUTH_DATA_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { AuthSessionModeService } from "@services/auth-session-mode/auth-session-mode.service";
import { MockAuthSessionModeService } from "@testing/mock-services/mock-auth-session-mode-service";
import {
  AuthSessionSyncHandler,
  AuthSessionSyncService,
  isCrossTabSyncSupported,
  isModeAvailable
} from "./auth-session-sync.service";

interface Envelope {
  type: string;
  mode?: string;
  token?: string;
  authData?: string;
}

class FakeBroadcastChannel {
  private static open = new Map<string, FakeBroadcastChannel[]>();
  private listeners: ((event: MessageEvent<Envelope>) => void)[] = [];
  readonly sent: Envelope[] = [];
  readonly received: Envelope[] = [];

  constructor(readonly name: string) {
    const peers = FakeBroadcastChannel.open.get(name) ?? [];
    peers.push(this);
    FakeBroadcastChannel.open.set(name, peers);
  }

  static reset(): void {
    FakeBroadcastChannel.open.clear();
  }

  addEventListener(type: string, callback: (event: MessageEvent<Envelope>) => void): void {
    if (type === "message") {
      this.listeners.push(callback);
    }
  }

  private deliver(data: Envelope): void {
    this.received.push(data);
    this.listeners.forEach((listener) => listener({ data } as MessageEvent<Envelope>));
  }

  postMessage(data: Envelope): void {
    this.sent.push(data);
    (FakeBroadcastChannel.open.get(this.name) ?? [])
      .filter((peer) => peer !== this)
      .forEach((peer) => peer.deliver(data));
  }
}

describe("AuthSessionSyncService", () => {
  let modeService: MockAuthSessionModeService;
  let handler: AuthSessionSyncHandler;
  let otherTab: FakeBroadcastChannel;

  function createService(): AuthSessionSyncService {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: AuthSessionModeService as Type<unknown>, useValue: modeService }]
    });
    const service = TestBed.inject(AuthSessionSyncService);
    handler = { endSession: jest.fn(), adoptStoredSession: jest.fn() };
    service.setHandler(handler);
    return service;
  }

  function answerRequestsWith(token: string, authData: string): void {
    otherTab.addEventListener("message", (event) => {
      if (event.data.type === "request") {
        otherTab.postMessage({ type: "offer", token, authData });
      }
    });
  }

  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    FakeBroadcastChannel.reset();
    (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel = FakeBroadcastChannel;
    otherTab = new FakeBroadcastChannel("privacyidea_session");
    modeService = new MockAuthSessionModeService();
  });

  afterEach(() => {
    delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
  });

  describe("availability", () => {
    it("reports support while BroadcastChannel exists", () => {
      expect(isCrossTabSyncSupported()).toBe(true);
    });

    it("reports no support without it", () => {
      delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
      expect(isCrossTabSyncSupported()).toBe(false);
    });

    it("offers multi-tab-ephemeral only where the channel exists", () => {
      expect(isModeAvailable("multi-tab-ephemeral")).toBe(true);
      delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
      expect(isModeAvailable("multi-tab-ephemeral")).toBe(false);
    });

    it("always offers the other two modes", () => {
      delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
      expect(isModeAvailable("single-tab")).toBe(true);
      expect(isModeAvailable("multi-tab-persistent")).toBe(true);
    });
  });

  describe("adoptSessionFromOpenTabs", () => {
    it("adopts a session offered by a running tab", async () => {
      modeService.mode.set("multi-tab-ephemeral");
      const service = createService();
      answerRequestsWith("handed-over", "auth-data");
      await service.adoptSessionFromOpenTabs();
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("handed-over");
      expect(sessionStorage.getItem(AUTH_DATA_STORAGE_KEY)).toBe("auth-data");
    });

    it("asks nothing outside multi-tab-ephemeral", async () => {
      modeService.mode.set("single-tab");
      const service = createService();
      await service.adoptSessionFromOpenTabs();
      expect(otherTab.received).toHaveLength(0);
    });

    it("keeps its own session instead of asking", async () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "mine");
      const service = createService();
      answerRequestsWith("theirs", "auth-data");
      await service.adoptSessionFromOpenTabs();
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("mine");
    });

    it("resolves without a session when nobody answers", async () => {
      jest.useFakeTimers();
      modeService.mode.set("multi-tab-ephemeral");
      const service = createService();
      const pending = service.adoptSessionFromOpenTabs();
      jest.advanceTimersByTime(250);
      await pending;
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBeNull();
      jest.useRealTimers();
    });
  });

  describe("answering another tab", () => {
    it("offers its session on request", () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      createService();
      otherTab.postMessage({ type: "request" });
      expect(otherTab.received).toContainEqual({ type: "offer", token: "token", authData: "data" });
    });

    it("stays silent in single-tab", () => {
      modeService.mode.set("single-tab");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      createService();
      otherTab.postMessage({ type: "request" });
      expect(otherTab.received).toHaveLength(0);
    });

    it("stays silent without a session of its own", () => {
      modeService.mode.set("multi-tab-ephemeral");
      createService();
      otherTab.postMessage({ type: "request" });
      expect(otherTab.received).toHaveLength(0);
    });
  });

  describe("logout", () => {
    it("broadcasts in the shared modes", () => {
      modeService.mode.set("multi-tab-persistent");
      createService().broadcastLogout();
      expect(otherTab.received).toContainEqual({ type: "logout" });
    });

    it("does not broadcast in single-tab", () => {
      modeService.mode.set("single-tab");
      createService().broadcastLogout();
      expect(otherTab.received).toHaveLength(0);
    });

    it("ends the session when another tab logs out", () => {
      modeService.mode.set("multi-tab-ephemeral");
      createService();
      otherTab.postMessage({ type: "logout" });
      expect(handler.endSession).toHaveBeenCalled();
    });

    it("ignores a remote logout in single-tab", () => {
      modeService.mode.set("single-tab");
      createService();
      otherTab.postMessage({ type: "logout" });
      expect(handler.endSession).not.toHaveBeenCalled();
    });
  });

  describe("login", () => {
    it("broadcasts the session in a shared mode", () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      createService().broadcastLogin();
      expect(otherTab.received).toContainEqual({ type: "login", token: "token", authData: "data" });
    });

    it("does not broadcast in single-tab", () => {
      modeService.mode.set("single-tab");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      createService().broadcastLogin();
      expect(otherTab.received).toHaveLength(0);
    });

    it("signs in a tab that has no session yet", () => {
      modeService.mode.set("multi-tab-ephemeral");
      createService();
      otherTab.postMessage({ type: "login", token: "token", authData: "data" });
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("token");
      expect(handler.adoptStoredSession).toHaveBeenCalled();
    });

    it("leaves a tab that is already signed in alone", () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "mine");
      createService();
      otherTab.postMessage({ type: "login", token: "theirs", authData: "data" });
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("mine");
      expect(handler.adoptStoredSession).not.toHaveBeenCalled();
    });
  });

  describe("mode change from another tab", () => {
    it("takes over mode and session", () => {
      modeService.mode.set("single-tab");
      createService();
      otherTab.postMessage({ type: "mode-changed", mode: "multi-tab-persistent", token: "t", authData: "d" });
      expect(modeService.adoptMode).toHaveBeenCalledWith("multi-tab-persistent");
      expect(localStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("t");
      expect(handler.adoptStoredSession).toHaveBeenCalled();
    });

    it("replaces a session the receiving tab already had", () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "old");
      createService();
      otherTab.postMessage({ type: "mode-changed", mode: "single-tab", token: "new", authData: "d" });
      expect(sessionStorage.getItem(BEARER_TOKEN_STORAGE_KEY)).toBe("new");
    });

    it("broadcasts its own change through the registered listener", () => {
      modeService.mode.set("multi-tab-ephemeral");
      sessionStorage.setItem(BEARER_TOKEN_STORAGE_KEY, "token");
      sessionStorage.setItem(AUTH_DATA_STORAGE_KEY, "data");
      createService();
      const listener = modeService.setModeChangeListener.mock.calls[0][0] as (mode: string) => void;
      listener("multi-tab-persistent");
      expect(otherTab.received).toContainEqual({
        type: "mode-changed",
        mode: "multi-tab-persistent",
        token: "token",
        authData: "data"
      });
    });
  });
});
