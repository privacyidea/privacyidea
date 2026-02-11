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
import { signal } from "@angular/core";
import { HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app/app.component";
import { CaConnector, CaConnectors, CaConnectorServiceInterface } from "../../app/services/ca-connector/ca-connector.service";

export class MockCaConnectorService implements CaConnectorServiceInterface {
  caConnectorResource: HttpResourceRef<PiResponse<CaConnectors> | undefined> = {
    value: signal(undefined),
    status: signal(0) as any,
    error: signal(null),
    isLoading: signal(false),
    reload: jest.fn(),
    headers: signal(undefined),
    statusCode: signal(undefined),
    progress: signal(undefined),
    hasValue: function (): this is HttpResourceRef<Exclude<PiResponse<CaConnectors> | undefined, undefined>> {
      return this.value() !== undefined;
    },
    destroy: function (): void {}
  } as any;

  caConnectors = signal<CaConnectors>([]);

  postCaConnector = jest.fn(async (_connector: CaConnector): Promise<void> => {
    return Promise.resolve();
  });

  deleteCaConnector = jest.fn(async (_connectorname: string): Promise<void> => {
    return Promise.resolve();
  });

  getCaSpecificOptions = jest.fn(async (_catype: string, _params: any): Promise<any> => {
    return Promise.resolve({});
  });
}
