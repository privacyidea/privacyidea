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
import { HttpClient, HttpParams, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, DOCUMENT, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";

import { PageEvent } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { StringUtils } from "@utils/string.utils";
import { Observable, shareReplay } from "rxjs";

export type TokenApplications = TokenApplication[];

export type AuthItemFields = Record<string, string>;
export type AuthItemResponse = Record<string, AuthItemFields[]>;

export type Machines = Machine[];

export interface Machine {
  hostname: string[];
  id: number;
  ip: string;
  resolver_name: string;
}

export interface TokenApplication {
  application: string;
  hostname: string;
  id: number;
  machine_id?: string;
  options: {
    service_id?: string;
    user?: string;
  };
  resolver?: string;
  serial: string;
  type: string;
}

export interface MachineServiceInterface {
  sshApiFilter: string[];
  offlineApiFilter: string[];
  advancedApiFilter: string[];
  machines: WritableSignal<Machines | undefined>;
  tokenApplications: Signal<TokenApplications | undefined>;
  selectedApplicationType: WritableSignal<"ssh" | "offline">;
  pageSize: WritableSignal<number>;
  machineFilter: WritableSignal<FilterValue>;
  filterParams: () => Record<string, string>;
  sort: WritableSignal<Sort>;
  pageIndex: WritableSignal<number>;
  machinesResource: HttpResourceRef<PiResponse<Machines> | undefined>;
  tokenApplicationResource: HttpResourceRef<PiResponse<TokenApplications> | undefined>;

  handleFilterInput($event: Event): void;

  clearFilter(): void;

  deleteAssignMachineToToken(args: {
    serial: string;
    application: string;
    mtid: string;
  }): Observable<PiResponse<number>>;

  postAssignMachineToToken(args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: "ssh" | "offline";
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }): Observable<PiResponse<number>>;

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string,
    options: Record<string, string>
  ): Observable<PiResponse<{ added: number; deleted: number }>>;

  getAuthItem(
    challenge: string,
    hostname: string,
    application?: string
  ): Observable<PiResponse<AuthItemResponse>>;

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string
  ): Observable<PiResponse<number>>;

  getMachine(args: {
    hostname?: string;
    ip?: string;
    id?: string;
    resolver?: string;
    any?: string;
  }): Observable<PiResponse<Machines>>;

  deleteToken(serial: string, machineid: string, resolver: string, application: string): Observable<PiResponse<number>>;

  deleteTokenById(serial: string, application: string, mtid: string): Observable<PiResponse<number>>;

  getMachineTokens(args: { machineid: number; resolver: string }): Observable<PiResponse<TokenApplications>>;

  onPageEvent(event: PageEvent): void;

  onSortEvent($event: Sort): void;

  toggleFilter(filterKeyword: string): void;

  getFilterIconName(keyword: string): string;

  focusActiveInput(): void;
}

@Injectable()
export class MachineService implements MachineServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly document: Document = inject(DOCUMENT);
  private readonly http = inject(HttpClient);
  private baseUrl = environment.proxyUrl + "/machine/";
  sshApiFilter = ["serial", "service_id"];
  offlineApiFilter = ["serial", "count", "rounds"];
  advancedApiFilter = ["hostname", "machineid & resolver"];

  selectedApplicationType = linkedSignal({
    source: this.tokenService.tokenDetailResource.value,
    computation: (tokenDetailResource) => {
      const tokenType = tokenDetailResource?.result?.value?.tokens[0]?.tokentype;
      if (tokenType === "hotp" || tokenType === "passkey") {
        return "offline";
      }
      return "ssh";
    }
  });

  pageSize = linkedSignal({
    source: () => ({
      selectedApplicationType: this.selectedApplicationType,
      tokenApplicationResource: this.tokenService.tokenDetailResourceValue
    }),
    computation: () => 10
  });

  machineFilter: WritableSignal<FilterValue> = linkedSignal({
    source: () => ({
      selectedApplicationType: this.selectedApplicationType(),
      tokenDetailResource: this.tokenService.tokenDetailResource.hasValue()
        ? this.tokenService.tokenDetailResource.value()
        : undefined
    }),
    computation: (source) => {
      const tokenSerial = source.tokenDetailResource?.result?.value?.tokens[0]?.serial;
      if (!tokenSerial) {
        return new FilterValue();
      }
      return new FilterValue({ value: `serial:${tokenSerial}` });
    }
  });

  filterParams = computed<Record<string, string>>(() => {
    const isSSH = this.selectedApplicationType() === "ssh";
    const allowed = isSSH
      ? [...this.sshApiFilter, ...this.advancedApiFilter]
      : [...this.offlineApiFilter, ...this.advancedApiFilter];

    const wrapKeys = new Set(isSSH ? ["serial", "service_id"] : ["serial"]);
    const plainKeys = new Set(
      isSSH ? ["hostname", "machineid", "resolver"] : ["hostname", "machineid", "resolver", "count", "rounds"]
    );

    const entries = Array.from(this.machineFilter().filterMap.entries())
      .filter(([key]) => allowed.includes(key))
      .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
      .filter(([, v]) => StringUtils.validFilterValue(v))
      .map(([key, v]) => [key, wrapKeys.has(key) ? `*${v}*` : v] as const)
      .filter(([key]) => wrapKeys.has(key) || plainKeys.has(key));

    return Object.fromEntries(entries) as Record<string, string>;
  });

  sort = linkedSignal({
    source: this.selectedApplicationType,
    computation: () => ({ active: "serial", direction: "asc" }) as Sort
  });

  pageIndex = linkedSignal({
    source: () => ({
      application: this.selectedApplicationType(),
      filter: this.machineFilter(),
      sort: this.sort(),
      tokenApplicationResource: this.tokenService.tokenDetailResourceValue
    }),
    computation: () => 0
  });

  machinesResource = httpResource<PiResponse<Machines>>(() => {
    // Do not load machines if the action is not allowed.
    if (!this.authService.actionAllowed("machinelist")) {
      return undefined;
    }
    // Only load machines on the token applications or token details routes.
    const onAllowedRoute =
      this.contentService.onTokensApplications() ||
      this.contentService.onTokenDetails() ||
      this.contentService.onConfigurationMachines();

    if (!onAllowedRoute) {
      return undefined;
    }

    return {
      url: `${this.baseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        any: ""
      }
    };
  });

  tokenApplicationResource = httpResource<PiResponse<TokenApplications>>(() => {
    // Do not load applications if the action is not allowed.
    if (!this.authService.actionAllowed("tokenlist")) {
      return undefined;
    }
    // Only load token applications on the token applications or token details routes.
    const onAllowedRoute = this.contentService.onTokensApplications() || this.contentService.onTokenDetails();

    if (!onAllowedRoute) {
      return undefined;
    }

    const params = {
      application: this.selectedApplicationType(),
      page: this.pageIndex() + 1,
      pagesize: this.pageSize(),
      sortby: this.sort()?.active || "serial",
      sortdir: this.sort()?.direction || "asc",
      ...this.filterParams()
    };

    return {
      url: this.baseUrl + "token",
      method: "GET",
      headers: this.authService.getHeaders(),
      params: params
    };
  });

  machines: WritableSignal<Machines | undefined> = linkedSignal({
    source: () => ({
      value: this.machinesResource.hasValue() ? this.machinesResource.value() : undefined,
      isLoading: this.machinesResource.isLoading(),
      error: this.machinesResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return undefined;
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? previous?.value : undefined;
      return value;
    }
  });

  tokenApplications: Signal<TokenApplications | undefined> = linkedSignal({
    source: () => ({
      value: this.tokenApplicationResource.hasValue() ? this.tokenApplicationResource.value() : undefined,
      isLoading: this.tokenApplicationResource.isLoading(),
      error: this.tokenApplicationResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return undefined;
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? previous?.value : undefined;
      return value;
    }
  });

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.machineFilter().copyWith({ value: input.value });
    this.machineFilter.set(newFilter);
  }

  clearFilter(): void {
    this.machineFilter.set(new FilterValue());
  }

  deleteAssignMachineToToken(args: {
    serial: string;
    application: string;
    mtid: string;
  }): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete<PiResponse<number>>(
        `${this.baseUrl}token/${encodeURIComponent(args.serial)}/${encodeURIComponent(args.application)}/${encodeURIComponent(args.mtid)}`,
        { headers }
      )
      .pipe(shareReplay(1));
  }

  postAssignMachineToToken(args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: string;
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http.post<PiResponse<number>>(`${this.baseUrl}token`, args, { headers }).pipe(shareReplay(1));
  }

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string,
    options: Record<string, string>
  ): Observable<PiResponse<{ added: number; deleted: number }>> {
    const headers = this.authService.getHeaders();
    const body: Record<string, string> = { hostname, machineid, resolver, serial, application, mtid, ...options };
    return this.http
      .post<PiResponse<{ added: number; deleted: number }>>(`${this.baseUrl}tokenoption`, body, { headers })
      .pipe(shareReplay(1));
  }

  getAuthItem(
    challenge: string,
    hostname: string,
    application?: string
  ): Observable<PiResponse<AuthItemResponse>> {
    const headers = this.authService.getHeaders();
    const params = new HttpParams().set("challenge", challenge).set("hostname", hostname);
    return this.http
      .get<PiResponse<AuthItemResponse>>(
        application ? `${this.baseUrl}authitem/${encodeURIComponent(application)}` : `${this.baseUrl}authitem`,
        {
          headers,
          params
        }
      )
      .pipe(shareReplay(1));
  }

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string
  ): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<number>>(`${this.baseUrl}token`, { hostname, machineid, resolver, serial, application }, { headers })
      .pipe(shareReplay(1));
  }

  getMachine(args: {
    hostname?: string;
    ip?: string;
    id?: string;
    resolver?: string;
    any?: string;
  }): Observable<PiResponse<Machines>> {
    const { hostname, ip, id, resolver, any } = args;
    const headers = this.authService.getHeaders();
    let params = new HttpParams();
    if (hostname !== undefined) params = params.set("hostname", hostname);
    if (ip !== undefined) params = params.set("ip", ip);
    if (id !== undefined) params = params.set("id", id);
    if (resolver !== undefined) params = params.set("resolver", resolver);
    if (any !== undefined) params = params.set("any", any);
    return this.http
      .get<PiResponse<Machines>>(`${this.baseUrl}`, {
        headers,
        params
      })
      .pipe(shareReplay(1));
  }

  deleteToken(serial: string, machineid: string, resolver: string, application: string): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete<PiResponse<number>>(
        `${this.baseUrl}token/${encodeURIComponent(serial)}/${encodeURIComponent(machineid)}/${encodeURIComponent(resolver)}/${encodeURIComponent(application)}`,
        { headers }
      )
      .pipe(shareReplay(1));
  }

  deleteTokenById(serial: string, application: string, id: string): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete<PiResponse<number>>(
        `${this.baseUrl}token/${encodeURIComponent(serial)}/${encodeURIComponent(application)}/${encodeURIComponent(id)}`,
        { headers }
      )
      .pipe(shareReplay(1));
  }

  getMachineTokens(args: { machineid: number; resolver: string }): Observable<PiResponse<TokenApplications>> {
    const headers = this.authService.getHeaders();
    const params = new HttpParams().set("machineid", args.machineid).set("resolver", args.resolver);
    return this.http
      .get<PiResponse<TokenApplications>>(`${this.baseUrl}token`, {
        headers,
        params
      })
      .pipe(shareReplay(1));
  }

  onPageEvent(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort): void {
    this.sort.set($event);
  }

  toggleFilter(filterKeyword: string): void {
    let newValue;
    if (filterKeyword === "machineid & resolver") {
      const current = this.machineFilter();
      const hasMachineId = current.hasKey("machineid");
      const hasResolver = current.hasKey("resolver");

      if (hasMachineId && hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (!hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: current });
      } else {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
      }
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.machineFilter()
      });
    }
    this.machineFilter.set(newValue);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "machineid & resolver") {
      const current = this.machineFilter();
      const selected = current.hasKey("machineid") && current.hasKey("resolver");
      return selected ? "filter_alt_off" : "filter_alt";
    }
    const isSelected = this.machineFilter().hasKey(keyword);
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  focusActiveInput(): void {
    const type = this.selectedApplicationType();
    const id = type === "ssh" ? "ssh-filter-input" : "offline-filter-input";
    setTimeout(() => {
      const el = this.document.getElementById(id) as HTMLInputElement | null;
      el?.focus();
    });
  }
}
