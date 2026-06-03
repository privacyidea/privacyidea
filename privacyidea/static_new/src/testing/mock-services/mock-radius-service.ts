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
import { signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import {
  RadiusServer,
  RadiusServers,
  RadiusServerServiceInterface
} from "@services/radius-server/radius-server.service";
import { MockHttpResourceRef } from "./mock-utils";

export class MockRadiusService implements RadiusServerServiceInterface {
  radiusServerResource = new MockHttpResourceRef<PiResponse<RadiusServers> | undefined>(undefined);
  radiusServers = signal<RadiusServer[]>([]);
  postRadiusServer = jest.fn(async (): Promise<void> => Promise.resolve());
  testRadiusServer = jest.fn(async (): Promise<boolean> => Promise.resolve(true));
  deleteRadiusServer = jest.fn(async (): Promise<void> => Promise.resolve());
}
