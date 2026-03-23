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
import { computed, Injectable, Signal, signal, WritableSignal } from "@angular/core";

export interface VersioningServiceInterface {
  rawVersion: WritableSignal<string>;
  version: Signal<string>;
  getVersion(): string;
}

@Injectable({
  providedIn: "root"
})
export class VersioningService implements VersioningServiceInterface {
  rawVersion = signal("");
  version = computed(() => {
    // Extract major.minor.patch from rawVersion
    const match = this.rawVersion().match(/^(\d+\.\d+(?:\.\d+)?)/);
    return match ? match[1] : "";
  });

  getVersion(): string {
    return this.version();
  }
}
