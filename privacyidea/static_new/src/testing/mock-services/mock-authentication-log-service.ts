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
import { computed, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  AuthenticationLogEventType,
  AuthenticationLogPage,
  AuthenticationLogServiceInterface,
  AuthenticationLogStatistics
} from "@services/authentication-log/authentication-log.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

// An empty window: no attempt ended in any classification, so `events` is empty rather than holding zeroed series.
export const emptyStatistics = (bins = 4): AuthenticationLogStatistics => ({
  window: { start_time: "2026-03-01T00:00:00+00:00", end_time: "2026-03-02T00:00:00+00:00", total: 0 },
  bins: {
    count: bins,
    starts: Array.from({ length: bins }, (_, index) => `2026-03-01T${String(index * 6).padStart(2, "0")}:00:00+00:00`)
  },
  events: []
});

export class MockAuthenticationLogService implements AuthenticationLogServiceInterface {
  apiFilter = ["username", "event_type", "serial"];
  advancedApiFilter: string[] = [];
  authenticationLogFilter = signal(new FilterValue());
  filterParams = signal<Record<string, string>>({});
  pageSize = signal(15);
  pageIndex = signal(1);
  sort = signal<Sort>({ active: "timestamp", direction: "desc" });
  timestampFrom = signal<string | null>(null);
  timestampTo = signal<string | null>(null);
  canRead = computed(() => true);
  oldestTimestamp = signal<string | null>(null);
  authenticationLogResource = new MockHttpResourceRef<PiResponse<AuthenticationLogPage> | undefined>(
    MockPiResponse.fromValue<AuthenticationLogPage>({
      auth_logs: [],
      count: 0,
      current: 1,
      prev: null,
      next: null
    })
  );
  // A representative subset spanning all three outcomes; tests may override via eventTypes.set(...).
  eventTypes = signal<AuthenticationLogEventType[]>([
    { name: "LOGIN_SUCCESS", outcome: "success" },
    { name: "CHALLENGE_TRIGGERED", outcome: "pending" },
    { name: "PASSWORD_FAIL", outcome: "failure" },
    { name: "NO_TOKEN", outcome: "failure" },
    { name: "NO_USABLE_TOKEN", outcome: "failure" },
    { name: "USER_UNKNOWN", outcome: "failure" },
    { name: "NOT_AUTHORIZED", outcome: "failure" },
    { name: "UNKNOWN_FAIL_REASON", outcome: "failure" }
  ]);
  eventTypesResource = new MockHttpResourceRef<PiResponse<AuthenticationLogEventType[]> | undefined>(
    MockPiResponse.fromValue<AuthenticationLogEventType[]>([])
  );

  fetchStatistics = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<AuthenticationLogStatistics>(emptyStatistics())));

  clearFilter = jest.fn().mockImplementation(() => {
    this.authenticationLogFilter.set(new FilterValue());
  });
  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.authenticationLogFilter.set(new FilterValue({ value: inputElement.value }));
  });
}
