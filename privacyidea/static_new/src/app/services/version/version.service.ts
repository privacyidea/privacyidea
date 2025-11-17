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
import { Injectable, signal, WritableSignal } from "@angular/core";
import { ROUTE_PATHS } from "../../route_paths";

export interface VersioningServiceInterface {
  version: WritableSignal<string>;
  getVersion(): string;
}

@Injectable({
  providedIn: "root"
})
export class VersioningService implements VersioningServiceInterface {
  version = signal("");

  getVersion(): string {
    return this.version();
  }
}
