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
import { computed, inject, Injectable, Injector, Signal, signal } from "@angular/core";
import { AUTH_DATA_STORAGE_KEY, AUTH_SESSION_MODE_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";

export const AUTH_SESSION_MODES = ["single-tab", "multi-tab-ephemeral", "multi-tab-persistent"] as const;

export type AuthSessionMode = (typeof AUTH_SESSION_MODES)[number];

export function isAuthSessionMode(value: unknown): value is AuthSessionMode {
  return AUTH_SESSION_MODES.some((mode) => mode === value);
}

export function isMultiTabMode(mode: AuthSessionMode): boolean {
  return mode !== "single-tab";
}

export function isSharedStorageMode(mode: AuthSessionMode): boolean {
  return mode === "multi-tab-persistent";
}

export function isCrossTabSyncSupported(): boolean {
  return typeof BroadcastChannel !== "undefined";
}

export function isModeAvailable(mode: AuthSessionMode): boolean {
  if (mode === "multi-tab-ephemeral") {
    return isCrossTabSyncSupported();
  }
  return true;
}

const SESSION_KEYS = [BEARER_TOKEN_STORAGE_KEY, AUTH_DATA_STORAGE_KEY];

export interface AuthSessionModeServiceInterface {
  readonly mode: Signal<AuthSessionMode>;

  readonly storage: Signal<Storage>;

  setMode(mode: AuthSessionMode): boolean;

  setDefaultMode(): void;

  addModeChangeListener(listener: (mode: AuthSessionMode) => void): () => void;

  adoptMode(mode: AuthSessionMode): void;
}

@Injectable({
  providedIn: "root"
})
export class AuthSessionModeService implements AuthSessionModeServiceInterface {
  private readonly defaultMode: AuthSessionMode = environment.defaultAuthSessionMode;

  private readonly storedMode = signal<AuthSessionMode | null>(AuthSessionModeService.readStoredMode());

  private readonly modeChangeListeners = new Set<(mode: AuthSessionMode) => void>();

  // Resolved lazily: the auth service reaches this one through the sync service, so an
  // eager inject() here would be a circular dependency.
  private readonly injector = inject(Injector);

  readonly mode: Signal<AuthSessionMode> = computed(() => {
    const mode = this.storedMode() ?? this.defaultMode;
    return isModeAvailable(mode) ? mode : "single-tab";
  });

  readonly storage: Signal<Storage> = computed(() =>
    isSharedStorageMode(this.mode()) ? localStorage : sessionStorage
  );

  constructor() {
    this.claimSessionFromInactiveStorage();
  }

  setMode(mode: AuthSessionMode): boolean {
    if (!isModeAvailable(mode) || !this.changeAllowed()) {
      return false;
    }
    if (mode === this.storedMode()) {
      return true;
    }
    const previousStorage = this.storage();
    localStorage.setItem(AUTH_SESSION_MODE_STORAGE_KEY, mode);
    this.storedMode.set(mode);
    this.moveSession(previousStorage, this.storage());
    this.modeChangeListeners.forEach((listener) => listener(mode));
    return true;
  }

  addModeChangeListener(listener: (mode: AuthSessionMode) => void): () => void {
    this.modeChangeListeners.add(listener);
    return () => {
      this.modeChangeListeners.delete(listener);
    };
  }

  private changeAllowed(): boolean {
    const authService = this.injector.get(AuthService);
    return authService.isAuthenticated() && authService.role() === "admin";
  }

  adoptMode(mode: AuthSessionMode): void {
    const previousStorage = this.storage();
    const previousStorageWasShared = isSharedStorageMode(this.mode());
    this.storedMode.set(mode);
    if (previousStorageWasShared) {
      SESSION_KEYS.forEach((key) => previousStorage.removeItem(key));
      return;
    }
    this.moveSession(previousStorage, this.storage());
  }

  setDefaultMode(): void {
    this.setMode(this.defaultMode);
  }

  private moveSession(from: Storage, to: Storage): void {
    if (from === to) {
      return;
    }
    SESSION_KEYS.forEach((key) => {
      const value = from.getItem(key);
      if (value !== null) {
        to.setItem(key, value);
      }
      from.removeItem(key);
    });
  }

  private claimSessionFromInactiveStorage(): void {
    const active = this.storage();
    const inactive = active === localStorage ? sessionStorage : localStorage;
    const claimable = active === sessionStorage && active.getItem(BEARER_TOKEN_STORAGE_KEY) === null;
    SESSION_KEYS.forEach((key) => {
      const value = inactive.getItem(key);
      if (claimable && value !== null) {
        active.setItem(key, value);
      }
      inactive.removeItem(key);
    });
  }

  private static readStoredMode(): AuthSessionMode | null {
    const stored = localStorage.getItem(AUTH_SESSION_MODE_STORAGE_KEY);
    return isAuthSessionMode(stored) ? stored : null;
  }
}
