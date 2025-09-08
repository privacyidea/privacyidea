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
import { AuthService, AuthServiceInterface } from "../../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../../content/content.service";
import { HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, computed, inject, linkedSignal, signal } from "@angular/core";
import { TokenService, TokenServiceInterface } from "../token.service";

import { FilterValue } from "../../../core/models/filter_value";
import { PiResponse } from "../../../app.component";
import { Sort } from "@angular/material/sort";
import { ROUTE_PATHS } from "../../../route_paths";

const apiFilter = ["serial", "transaction_id"];
const advancedApiFilter: string[] = [];

export interface Challenges {
  challenges: Challenge[];
  count: number;
  current: number;
  next?: number;
  prev?: number;
}

export interface Challenge {
  challenge: string;
  data: string;
  expiration: string;
  id: number;
  otp_received: boolean;
  otp_valid: boolean;
  received_count: number;
  serial: string;
  timestamp: string;
  transaction_id: string;
}

export interface ChallengesServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  challengesFilter: WritableSignal<FilterValue>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  sort: WritableSignal<Sort>;
  challengesResource: HttpResourceRef<PiResponse<Challenges> | undefined>;
  clearFilter(): void;
  handleFilterInput($event: Event): void;
}

@Injectable({
  providedIn: "root"
})
export class ChallengesService implements ChallengesServiceInterface {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  tokenBaseUrl = this.tokenService.tokenBaseUrl;
  challengesFilter = linkedSignal({
    source: this.contentService.routeUrl,
    computation: () => new FilterValue()
  });
  pageSize = linkedSignal({
    source: this.contentService.routeUrl,
    computation: () => 10
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.challengesFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: () => 0
  });
  sort = signal({ active: "timestamp", direction: "asc" } as Sort);
  private filterParams = computed(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const filterPairs = Array.from(this.challengesFilter().filterMap.entries())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedFilters.includes(key));
    return filterPairs.reduce(
      (acc, { key, value }) => {
        if (key === "serial") {
          acc.serial = `*${value}*`;
        } else {
          acc.params[key] = `*${value}*`;
        }
        return acc;
      },
      { params: {} as Record<string, string>, serial: "" }
    );
  });
  challengesResource = httpResource<PiResponse<Challenges>>(() => {
    if (this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CHALLENGES) {
      return undefined;
    }
    const { params: filterParams, serial } = this.filterParams();
    const url = serial ? `${this.tokenBaseUrl}challenges/${serial}` : `${this.tokenBaseUrl}challenges/`;
    return {
      url,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        pagesize: this.pageSize(),
        page: this.pageIndex() + 1,
        ...(this.sort().active && {
          sortby: this.sort().active,
          sortdir: this.sort().direction || "asc"
        }),
        ...filterParams
      }
    };
  });

  clearFilter(): void {
    this.challengesFilter.set(new FilterValue());
  }
  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.challengesFilter().copyWith({ value: input.value });
    this.challengesFilter.set(newFilter);
  }
}
