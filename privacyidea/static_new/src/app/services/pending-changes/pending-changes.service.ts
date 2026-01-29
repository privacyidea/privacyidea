/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

@Injectable({ providedIn: "root" })
export class PendingChangesService {
  private _hasChangesFn = signal<(() => boolean) | null>(null);
  private _saveFn = signal<(() => Promise<void> | void) | null>(null);

  get hasChanges(): boolean {
    const fn = this._hasChangesFn();
    return fn ? fn() : false;
  }

  registerHasChanges(fn: () => boolean): void {
    this._hasChangesFn.set(fn);
  }

  unregisterHasChanges(): void {
    this._hasChangesFn.set(null);
    this._saveFn.set(null);
  }

  registerSave(fn: () => Promise<void> | void): void {
    this._saveFn.set(fn);
  }

  save(): Promise<void> | void {
    const fn = this._saveFn();
    return fn ? fn() : undefined;
  }
}
