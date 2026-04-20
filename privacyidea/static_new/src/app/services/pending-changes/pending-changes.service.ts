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
import { Injectable, signal } from "@angular/core";

export interface PendingChangesServiceInterface {
  hasChanges: boolean;
  validChanges: boolean;

  registerHasChanges(fn: () => boolean): void;

  clearAllRegistrations(): void;

  registerSave(fn: () => Promise<boolean>): void;

  save(): Promise<boolean>;

  registerValidChanges(fn: () => boolean): void;
}

@Injectable({ providedIn: "root" })
export class PendingChangesService implements PendingChangesServiceInterface {
  private _hasChangesFn = signal<(() => boolean) | null>(null);
  private _saveFn = signal<(() => Promise<boolean>) | null>(null);
  private _validChanges: () => boolean = signal(true);

  get hasChanges(): boolean {
    const fn = this._hasChangesFn();
    return fn ? fn() : false;
  }

  registerHasChanges(fn: () => boolean): void {
    this._hasChangesFn.set(fn);
  }

  clearAllRegistrations(): void {
    this._hasChangesFn.set(null);
    this._saveFn.set(null);
    this._validChanges = signal(true);
  }

  registerSave(fn: () => Promise<boolean>): void {
    this._saveFn.set(fn);
  }

  async save(): Promise<boolean> {
    const fn = this._saveFn();
    return fn ? fn() : false;
  }

  registerValidChanges(fn: () => boolean): void {
    this._validChanges = fn;
  }

  get validChanges(): boolean {
    return this._validChanges();
  }
}
