/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { of } from "rxjs";
import { FilterValue } from "../../app/core/models/filter_value";
import { MachineServiceInterface, Machines, TokenApplication } from "../../app/services/machine/machine.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockMachineService implements MachineServiceInterface {
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

  handleFilterInput(_$event: Event): void { throw new Error("Method not implemented."); }
  clearFilter(): void { throw new Error("Method not implemented."); }

  deleteAssignMachineToToken() { return of({} as any); }

  postAssignMachineToToken(_args: { service_id?: string; user?: string; serial: string; application: "ssh" | "offline"; machineid: number; resolver: string; count?: number; rounds?: number; }) { return of({} as any); }

  postTokenOption = jest.fn().mockReturnValue(of({} as any));
  getAuthItem = jest.fn().mockReturnValue(
    of({ result: { value: { serial: "", machineid: "", resolver: "" } } })
  );
  postToken = jest.fn().mockReturnValue(of({} as any));
  getMachine = jest.fn().mockReturnValue(
    of({ result: { value: { machines: [ { hostname: "localhost", machineid: "machine1", resolver: "resolver1", serial: "serial1", type: "ssh", applications: [] } ], count: 1 } } })
  );
  deleteToken = jest.fn().mockReturnValue(of({} as any));
  deleteTokenMtid = jest.fn().mockReturnValue(of({} as any));
  onPageEvent = jest.fn();
  onSortEvent = jest.fn();
}
