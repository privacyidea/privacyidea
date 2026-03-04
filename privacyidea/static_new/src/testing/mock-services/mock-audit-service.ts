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
import { linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { Audit, AuditServiceInterface } from "../../app/services/audit/audit.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";
import { PiResponse } from "../../app/app.component";
import { FilterValue } from "src/app/core/models/filter_value/filter_value";

export class MockAuditService implements AuditServiceInterface {
  apiFilterKeyMap: Record<string, string> = {};
  apiFilter = ["user", "success"];
  advancedApiFilter = ["machineid", "resolver"];
  auditFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams: Signal<Record<string, string>> = signal({});
  pageSize = linkedSignal({ source: this.auditFilter, computation: () => 10 });
  pageIndex = linkedSignal({
    source: () => ({ filterValue: this.auditFilter(), pageSize: this.pageSize() }),
    computation: () => 0
  });
  auditResource = new MockHttpResourceRef<PiResponse<Audit> | undefined>(
    MockPiResponse.fromValue<Audit>({ auditcolumns: [], auditdata: [], count: 0, current: 0 })
  );
  sort: WritableSignal<Sort> = signal({ active: "time", direction: "desc" });
  clearFilter = jest.fn().mockImplementation(() => {
    this.auditFilter.set(new FilterValue());
  });
  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.auditFilter.set(new FilterValue({ value: inputElement.value }));
  });
}
