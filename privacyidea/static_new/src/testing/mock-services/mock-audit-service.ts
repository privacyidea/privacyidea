/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { FilterValue } from "../../app/core/models/filter_value";
import { Sort } from "@angular/material/sort";
import { Audit, AuditServiceInterface } from "../../app/services/audit/audit.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";
import { PiResponse } from "../../app/app.component";

export class MockAuditService implements AuditServiceInterface {
  apiFilterKeyMap: Record<string, string> = {};
  apiFilter = ["user", "success"];
  advancedApiFilter = ["machineid", "resolver"];
  auditFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams: Signal<Record<string, string>> = signal({});
  pageSize = linkedSignal({ source: this.auditFilter, computation: () => 10 });
  pageIndex = linkedSignal({ source: () => ({ filterValue: this.auditFilter(), pageSize: this.pageSize() }), computation: () => 0 });
  auditResource = new MockHttpResourceRef<PiResponse<Audit> | undefined>(
    MockPiResponse.fromValue<Audit>({ auditcolumns: [], auditdata: [], count: 0, current: 0 })
  );
  sort: WritableSignal<Sort> = signal({ active: "time", direction: "desc" });
  clearFilter = jest.fn().mockImplementation(() => { this.auditFilter.set(new FilterValue()); });
  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.auditFilter.set(new FilterValue({ value: inputElement.value }));
  });
}
