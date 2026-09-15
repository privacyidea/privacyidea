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

import { Signal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  MachineServiceInterface,
  Machines,
  TokenApplication,
  TokenApplications
} from "@services/machine/machine.service";
import { of } from "rxjs";
import { Debouncer } from "@utils/debounce.utils";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockMachineService implements MachineServiceInterface {
  getMachineTokens = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<TokenApplications>([])));
  baseUrl = "environment.mockProxyUrl + '/machine/'";
  filterValue = signal<Record<string, string>>({});
  sshApiFilterKeys: string[] = [];
  offlineApiFilterKeys: string[] = [];
  apiFilterKeys: string[] = [];
  advancedApiFilterKeys: string[] = [];
  hiddenApiFilterKeys: string[] = [];
  apiFilterKeyMap: Record<string, string> = {};
  exactMatchKeys = new Set<string>();
  allFilterKeys: Signal<string[]> = signal([
    ...this.apiFilterKeys,
    ...this.advancedApiFilterKeys,
    ...this.hiddenApiFilterKeys
  ]);
  machines = signal<Machines>([]);
  tokenApplications = signal<TokenApplication[]>([]);
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
  pageSize = signal(10);
  activeFilter = signal(new FilterValue());
  filterDebouncer = new Debouncer(this.activeFilter);
  filterDraft = this.activeFilter;
  filterParams = signal<Record<string, string>>({});
  sort = signal<Sort>({ active: "", direction: "" });
  pageIndex = signal(0);
  machinesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Machines>([]));
  tokenApplicationResource = new MockHttpResourceRef(MockPiResponse.fromValue([]));

  filterFromInput = jest.fn();
  handleFilterInput = jest.fn();
  applyFilterInput = jest.fn();
  setFilter = jest.fn().mockImplementation((filter: FilterValue) => {
    this.activeFilter.set(filter);
  });
  updateFilter = jest.fn().mockImplementation((computeFilter: (current: FilterValue) => FilterValue) => {
    this.activeFilter.set(computeFilter(this.activeFilter()));
  });
  clearFilter = jest.fn();

  deleteAssignMachineToToken() {
    return of(MockPiResponse.fromValue<number>(0));
  }

  postAssignMachineToToken() {
    return of(MockPiResponse.fromValue<number>(0));
  }

  postTokenOption = jest.fn().mockReturnValue(of(MockPiResponse.fromValue({ added: 0, deleted: 0 })));
  getAuthItem = jest.fn().mockReturnValue(of({ result: { value: { serial: "", machineid: "", resolver: "" } } }));
  postToken = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<number>(0)));
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
  deleteToken = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<number>(0)));
  deleteTokenById = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<number>(0)));
  onPageEvent = jest.fn();
  onSortEvent = jest.fn();
  toggleFilter = jest.fn();
  getFilterIconName = jest.fn().mockReturnValue("filter_list");
  focusActiveInput = jest.fn();
}
