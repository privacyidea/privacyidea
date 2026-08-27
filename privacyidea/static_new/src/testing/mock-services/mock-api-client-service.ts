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
  ApiClient,
  ApiClientServiceInterface,
  IssuedApiKey,
  RememberedDevice
} from "@services/api-client/api-client.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockApiClientService implements ApiClientServiceInterface {
  apiClientResource = new MockHttpResourceRef<PiResponse<ApiClient[]> | undefined>(
    MockPiResponse.fromValue<ApiClient[]>([])
  );

  apiClients = signal<ApiClient[]>([]);
  lastIssuedKey = signal<IssuedApiKey | null>(null);

  dismissIssuedKey = jest.fn(() => {
    this.lastIssuedKey.set(null);
  });

  createClient = jest.fn(async (): Promise<void> => Promise.resolve());
  updateClient = jest.fn(async (): Promise<void> => Promise.resolve());
  rotateClient = jest.fn(async (): Promise<void> => Promise.resolve());
  deleteClient = jest.fn(async (): Promise<void> => Promise.resolve());

  getRememberedDevices = jest.fn(async (): Promise<RememberedDevice[]> => Promise.resolve([]));
  revokeDevice = jest.fn(async (): Promise<void> => Promise.resolve());
  revokeAllForClient = jest.fn(async (): Promise<number> => Promise.resolve(0));
  revokeAllInRealmAcrossClients = jest.fn(async (): Promise<number> => Promise.resolve(0));
}
