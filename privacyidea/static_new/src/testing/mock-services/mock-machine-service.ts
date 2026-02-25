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

import { WritableSignal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { Observable, of } from "rxjs";
import {
  MachineServiceInterface,
  Machines,
  TokenApplication,
  TokenApplications
} from "../../app/services/machine/machine.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";
import { PiResponse } from "../../app/app.component";
import { FilterValue } from "src/app/core/models/filter_value/filter_value";

export class MockMachineService implements MachineServiceInterface {
  getMachineTokens(args: { machineid: number; resolver: string }): Observable<PiResponse<TokenApplications>> {
    throw new Error("Method not implemented.");
  }
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  filterValue: WritableSignal<Record<string, string>> = signal({});
  sshApiFilter: string[] = [];
  offlineApiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  machines: WritableSignal<Machines> = signal<Machines>([]);
  tokenApplications: WritableSignal<TokenApplication[]> = signal([]);
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
  pageSize = signal(10);
  machineFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams = signal<Record<string, string>>({});
  sort: WritableSignal<Sort> = signal({ active: "", direction: "" });
  pageIndex = signal(0);
  machinesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Machines>([]));
  tokenApplicationResource = new MockHttpResourceRef(MockPiResponse.fromValue([]));

  handleFilterInput(_$event: Event): void {
    throw new Error("Method not implemented.");
  }
  clearFilter(): void {
    throw new Error("Method not implemented.");
  }

  deleteAssignMachineToToken() {
    return of({} as any);
  }

  postAssignMachineToToken(_args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: "ssh" | "offline";
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }) {
    return of({} as any);
  }

  postTokenOption = jest.fn().mockReturnValue(of({} as any));
  getAuthItem = jest.fn().mockReturnValue(of({ result: { value: { serial: "", machineid: "", resolver: "" } } }));
  postToken = jest.fn().mockReturnValue(of({} as any));
  getMachine = jest.fn().mockReturnValue(
    of({
      result: {
        value: {
          machines: [
            {
              hostname: "localhost",
              machineid: "machine1",
              resolver: "resolver1",
              serial: "serial1",
              type: "ssh",
              applications: []
            }
          ],
          count: 1
        }
      }
    })
  );
  deleteToken = jest.fn().mockReturnValue(of({} as any));
  deleteTokenById = jest.fn().mockReturnValue(of({} as any));
  onPageEvent = jest.fn();
  onSortEvent = jest.fn();
}
