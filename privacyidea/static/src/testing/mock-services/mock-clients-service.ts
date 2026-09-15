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
import { PiResponse } from "@app/app.component";
import { ClientsDict, ClientsServiceInterface } from "@services/clients/clients.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";

export class MockClientsService implements ClientsServiceInterface {
  clientsResource = new MockHttpResourceRef<PiResponse<ClientsDict> | undefined>(undefined);
  requestClientsForAutocomplete = jest.fn();

  setClients(dict: ClientsDict): void {
    this.clientsResource.set(MockPiResponse.fromValue<ClientsDict>(dict));
  }
}
