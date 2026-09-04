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
import { inject, Injectable } from "@angular/core";
import { AUTH_DATA_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import {
  AuthSessionMode,
  AuthSessionModeService,
  AuthSessionModeServiceInterface,
  isAuthSessionMode,
  isCrossTabSyncSupported,
  isMultiTabMode,
  isSharedStorageMode
} from "@services/auth-session-mode/auth-session-mode.service";

const AUTH_SESSION_CHANNEL_NAME = "privacyidea_session";
const TAB_PRESENCE_LOCK_NAME = "privacyidea_session_tab";
const HANDSHAKE_TIMEOUT_MS = 250;

interface SessionPayload {
  token: string;
  authData: string;
}

// Messages arrive from any same-origin context, including another build of this app, so a
// payload is only handed to the storage once both halves are actually strings.
function isSessionPayload(value: unknown): value is SessionPayload {
  const payload = value as Partial<SessionPayload> | null | undefined;
  return typeof payload?.token === "string" && typeof payload?.authData === "string";
}

type AuthSessionSyncMessage =
  | { type: "request" }
  | ({ type: "offer" } & SessionPayload)
  | { type: "logout" }
  | ({ type: "login" } & SessionPayload)
  | ({ type: "mode-changed"; mode: AuthSessionMode } & Partial<SessionPayload>);

export interface AuthSessionSyncHandler {
  endSession(): void;

  adoptStoredSession(): void;

  hasSession(): boolean;
}

export interface AuthSessionSyncServiceInterface {
  adoptSessionFromOpenTabs(): Promise<void>;

  broadcastLogout(): void;

  broadcastLogin(): void;

  addHandler(handler: AuthSessionSyncHandler): () => void;
}

@Injectable({
  providedIn: "root"
})
export class AuthSessionSyncService implements AuthSessionSyncServiceInterface {
  private readonly authSessionModeService: AuthSessionModeServiceInterface = inject(AuthSessionModeService);
  private readonly channel = AuthSessionSyncService.openChannel();
  private readonly handlers = new Set<AuthSessionSyncHandler>();
  private readonly tabPresence = AuthSessionSyncService.holdTabPresence();
  private pendingAdoption: ((message: AuthSessionSyncMessage) => void) | null = null;

  constructor() {
    this.channel?.addEventListener("message", (event: MessageEvent<AuthSessionSyncMessage>) =>
      this.handleMessage(event.data)
    );
    this.authSessionModeService.addModeChangeListener((mode) => this.broadcastModeChange(mode));
  }

  async adoptSessionFromOpenTabs(): Promise<void> {
    if (!this.channel || this.authSessionModeService.mode() !== "multi-tab-ephemeral") {
      return;
    }
    if (this.hasStoredSession()) {
      return;
    }
    // The bootstrap waits on this handshake, so the timeout must not be paid by the first or
    // only tab, where nobody is on the channel to answer it.
    if (!(await this.hasOpenPeers())) {
      return;
    }
    const storage = this.authSessionModeService.storage();
    return new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        this.pendingAdoption = null;
        resolve();
      }, HANDSHAKE_TIMEOUT_MS);
      this.pendingAdoption = (message) => {
        if (message.type !== "offer" || !isSessionPayload(message)) {
          return;
        }
        clearTimeout(timer);
        this.pendingAdoption = null;
        this.writeSession(storage, message);
        resolve();
      };
      this.post({ type: "request" });
    });
  }

  broadcastLogout(): void {
    if (isMultiTabMode(this.authSessionModeService.mode())) {
      this.post({ type: "logout" });
    }
  }

  broadcastLogin(): void {
    if (isMultiTabMode(this.authSessionModeService.mode())) {
      const payload = this.readSession();
      if (payload) {
        this.post({ type: "login", ...payload });
      }
    }
  }

  addHandler(handler: AuthSessionSyncHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  private broadcastModeChange(mode: AuthSessionMode): void {
    // Posted even without a payload: the mode is already persisted, so a tab that never hears
    // about it keeps reading the other Storage than the one the stored mode names.
    this.post({ type: "mode-changed", mode, ...(this.readSession() ?? {}) });
  }

  private handleMessage(message: AuthSessionSyncMessage): void {
    switch (message.type) {
      case "request":
        this.offerSession();
        return;
      case "offer":
        this.pendingAdoption?.(message);
        return;
      case "logout":
        this.acceptRemoteLogout();
        return;
      case "login":
        this.acceptRemoteLogin(message);
        return;
      case "mode-changed":
        this.acceptModeChange(message);
        return;
    }
  }

  private acceptRemoteLogin(message: unknown): void {
    const mode = this.authSessionModeService.mode();
    if (!isMultiTabMode(mode) || this.handlers.size === 0 || !isSessionPayload(message)) {
      return;
    }
    if (!isSharedStorageMode(mode) && this.hasAdoptedSession()) {
      return;
    }
    this.writeSession(this.authSessionModeService.storage(), message);
    this.adoptStoredSession();
  }

  private acceptModeChange(message: { mode: AuthSessionMode } & Partial<SessionPayload>): void {
    if (!isAuthSessionMode(message.mode)) {
      return;
    }
    const keepsOwnSession = !isMultiTabMode(message.mode) && !isSharedStorageMode(this.authSessionModeService.mode());
    this.authSessionModeService.adoptMode(message.mode);
    if (keepsOwnSession) {
      return;
    }
    if (isSessionPayload(message)) {
      this.writeSession(this.authSessionModeService.storage(), message);
    }
    this.adoptStoredSession();
  }

  private hasStoredSession(): boolean {
    return this.readSession() !== null;
  }

  private hasAdoptedSession(): boolean {
    return [...this.handlers].some((handler) => handler.hasSession());
  }

  private adoptStoredSession(): void {
    this.handlers.forEach((handler) => handler.adoptStoredSession());
  }

  private readSession(): SessionPayload | null {
    const storage = this.authSessionModeService.storage();
    const token = storage.getItem(BEARER_TOKEN_STORAGE_KEY);
    const authData = storage.getItem(AUTH_DATA_STORAGE_KEY);
    return token !== null && authData !== null ? { token, authData } : null;
  }

  private writeSession(storage: Storage, payload: SessionPayload): void {
    storage.setItem(BEARER_TOKEN_STORAGE_KEY, payload.token);
    storage.setItem(AUTH_DATA_STORAGE_KEY, payload.authData);
  }

  private offerSession(): void {
    if (this.authSessionModeService.mode() !== "multi-tab-ephemeral") {
      return;
    }
    const payload = this.readSession();
    if (payload) {
      this.post({ type: "offer", ...payload });
    }
  }

  private acceptRemoteLogout(): void {
    if (!isMultiTabMode(this.authSessionModeService.mode())) {
      return;
    }
    this.handlers.forEach((handler) => handler.endSession());
  }

  private post(message: AuthSessionSyncMessage): void {
    this.channel?.postMessage(message);
  }

  private static openChannel(): BroadcastChannel | null {
    return isCrossTabSyncSupported() ? new BroadcastChannel(AUTH_SESSION_CHANNEL_NAME) : null;
  }

  // A shared lock the browser releases on its own when the tab goes away, which makes the
  // number of its holders the number of open tabs.
  private static holdTabPresence(): Promise<void> {
    const locks = globalThis.navigator?.locks;
    if (!locks?.request) {
      return Promise.resolve();
    }
    return new Promise<void>((held) => {
      locks
        .request(TAB_PRESENCE_LOCK_NAME, { mode: "shared" }, () => {
          held();
          return new Promise<never>(() => undefined);
        })
        .catch(() => held());
    });
  }

  private async hasOpenPeers(): Promise<boolean> {
    const locks = globalThis.navigator?.locks;
    if (!locks?.query) {
      return true;
    }
    await this.tabPresence;
    try {
      const held = (await locks.query()).held ?? [];
      return held.filter((lock) => lock.name === TAB_PRESENCE_LOCK_NAME).length > 1;
    } catch {
      return true;
    }
  }
}
