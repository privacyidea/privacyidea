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
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { Challenges, ChallengesServiceInterface } from "@services/token/challenges/challenges.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockChallengesService implements ChallengesServiceInterface {
  apiFilter = ["serial", "transaction_id"];
  advancedApiFilter: string[] = [];
  challengesFilter = signal(new FilterValue());
  pageSize = signal(10);
  pageIndex = signal(0);
  sort = signal<Sort>({ active: "timestamp", direction: "asc" });
  challengesResource = new MockHttpResourceRef<PiResponse<Challenges> | undefined>(
    MockPiResponse.fromValue<Challenges>({ challenges: [], count: 0, current: 0 })
  );
  clearFilter = jest.fn().mockImplementation(() => {
    this.challengesFilter.set(new FilterValue());
  });
  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const input = $event.target as HTMLInputElement;
    this.challengesFilter.set(this.challengesFilter().copyWith({ value: input.value }));
  });
  deleteExpiredChallenges = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<unknown>(true)));
}
