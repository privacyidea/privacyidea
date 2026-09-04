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
  isMultiTabMode
} from "@services/auth-session-mode/auth-session-mode.service";

const AUTH_SESSION_CHANNEL_NAME = "privacyidea_session";
const HANDSHAKE_TIMEOUT_MS = 250;

export function isCrossTabSyncSupported(): boolean {
  return typeof BroadcastChannel !== "undefined";
}

export function isModeAvailable(mode: AuthSessionMode): boolean {
  if (mode === "multi-tab-ephemeral") {
    return isCrossTabSyncSupported();
  }
  return true;
}

interface SessionPayload {
  token: string;
  authData: string;
}

type AuthSessionSyncMessage =
  | { type: "request" }
  | ({ type: "offer" } & SessionPayload)
  | { type: "logout" }
  | ({ type: "login" } & SessionPayload)
  | ({ type: "mode-changed"; mode: AuthSessionMode } & SessionPayload);

export interface AuthSessionSyncHandler {
  endSession(): void;

  adoptStoredSession(): void;
}

export interface AuthSessionSyncServiceInterface {
  adoptSessionFromOpenTabs(): Promise<void>;

  broadcastLogout(): void;

  broadcastLogin(): void;

  setHandler(handler: AuthSessionSyncHandler): void;
}

@Injectable({
  providedIn: "root"
})
export class AuthSessionSyncService implements AuthSessionSyncServiceInterface {
  private readonly authSessionModeService: AuthSessionModeServiceInterface = inject(AuthSessionModeService);
  private readonly channel = AuthSessionSyncService.openChannel();
  private handler: AuthSessionSyncHandler | null = null;
  private pendingAdoption: ((message: AuthSessionSyncMessage) => void) | null = null;

  constructor() {
    this.channel?.addEventListener("message", (event: MessageEvent<AuthSessionSyncMessage>) =>
      this.handleMessage(event.data)
    );
    this.authSessionModeService.setModeChangeListener((mode) => this.broadcastModeChange(mode));
  }

  adoptSessionFromOpenTabs(): Promise<void> {
    if (!this.channel || this.authSessionModeService.mode() !== "multi-tab-ephemeral") {
      return Promise.resolve();
    }
    const storage = this.authSessionModeService.storage();
    if (storage.getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        this.pendingAdoption = null;
        resolve();
      }, HANDSHAKE_TIMEOUT_MS);
      this.pendingAdoption = (message) => {
        if (message.type !== "offer") {
          return;
        }
        clearTimeout(timer);
        this.pendingAdoption = null;
        storage.setItem(BEARER_TOKEN_STORAGE_KEY, message.token);
        storage.setItem(AUTH_DATA_STORAGE_KEY, message.authData);
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

  setHandler(handler: AuthSessionSyncHandler): void {
    this.handler = handler;
  }

  private broadcastModeChange(mode: AuthSessionMode): void {
    const payload = this.readSession();
    if (payload) {
      this.post({ type: "mode-changed", mode, ...payload });
    }
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

  private acceptRemoteLogin(message: SessionPayload): void {
    if (!isMultiTabMode(this.authSessionModeService.mode())) {
      return;
    }
    const storage = this.authSessionModeService.storage();
    if (storage.getItem(BEARER_TOKEN_STORAGE_KEY) !== null) {
      return;
    }
    this.writeSession(storage, message);
    this.handler?.adoptStoredSession();
  }

  private acceptModeChange(message: { mode: AuthSessionMode } & SessionPayload): void {
    this.authSessionModeService.adoptMode(message.mode);
    this.writeSession(this.authSessionModeService.storage(), message);
    this.handler?.adoptStoredSession();
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
    if (this.handler) {
      this.handler.endSession();
      return;
    }
    const storage = this.authSessionModeService.storage();
    storage.removeItem(BEARER_TOKEN_STORAGE_KEY);
    storage.removeItem(AUTH_DATA_STORAGE_KEY);
  }

  private post(message: AuthSessionSyncMessage): void {
    this.channel?.postMessage(message);
  }

  private static openChannel(): BroadcastChannel | null {
    return isCrossTabSyncSupported() ? new BroadcastChannel(AUTH_SESSION_CHANNEL_NAME) : null;
  }
}
