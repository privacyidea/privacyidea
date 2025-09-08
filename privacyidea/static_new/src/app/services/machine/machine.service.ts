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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { HttpClient, HttpParams, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { TableUtilsService, TableUtilsServiceInterface } from "../table-utils/table-utils.service";
import { FilterValue } from "../../core/models/filter_value";
import { Observable, shareReplay } from "rxjs";
import { PageEvent } from "@angular/material/paginator";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { Sort } from "@angular/material/sort";
import { environment } from "../../../environments/environment";
import { TokenService, TokenServiceInterface } from "../token/token.service";

export type TokenApplications = TokenApplication[];

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
  handleFilterInput($event: Event): void;
  clearFilter(): void;
  sshApiFilter: string[];
  sshAdvancedApiFilter: string[];
  offlineApiFilter: string[];
  offlineAdvancedApiFilter: string[];
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

  deleteAssignMachineToToken(args: { serial: string; application: string; mtid: string }): Observable<any>;

  postAssignMachineToToken(args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: "ssh" | "offline";
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }): Observable<any>;

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string
  ): Observable<any>;

  getAuthItem(challenge: string, hostname: string, application?: string): Observable<any>;

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string
  ): Observable<any>;

  getMachine(args: {
    hostname?: string;
    ip?: string;
    id?: string;
    resolver?: string;
    any?: string;
  }): Observable<PiResponse<Machines>>;

  deleteToken(serial: string, machineid: string, resolver: string, application: string): Observable<any>;

  deleteTokenMtid(serial: string, application: string, mtid: string): Observable<any>;

  onPageEvent(event: PageEvent): void;

  onSortEvent($event: Sort): void;
}

@Injectable({
  providedIn: "root"
})
export class MachineService implements MachineServiceInterface {
  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.machineFilter().copyWith({ value: input.value });
    this.machineFilter.set(newFilter);
  }
  clearFilter(): void {
    this.machineFilter.set(new FilterValue());
  }
  private readonly http: HttpClient = inject(HttpClient);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  private baseUrl = environment.proxyUrl + "/machine/";
  sshApiFilter = ["serial", "service_id"];
  sshAdvancedApiFilter = ["hostname", "machineid & resolver"];
  offlineApiFilter = ["serial", "count", "rounds"];
  offlineAdvancedApiFilter = ["hostname", "machineid & resolver"];

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

  // signal<"ssh" | "offline">("ssh");
  pageSize = linkedSignal({
    source: () => ({
      selectedApplicationType: this.selectedApplicationType,
      tokenApplicationResource: this.tokenService.tokenDetailResource.value
    }),
    computation: () => 10
  });

  machinesResource = httpResource<PiResponse<Machines>>(() => {
    if (
      !(
        this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_APPLICATIONS) ||
        this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_DETAILS)
      ) ||
      !this.authService.actionAllowed("machinelist")
    ) {
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

  machines: WritableSignal<Machines | undefined> = linkedSignal({
    source: this.machinesResource.value,
    computation: (machinesResource, previous) => machinesResource?.result?.value ?? previous?.value
  });
  machineFilter: WritableSignal<FilterValue> = linkedSignal({
    source: () => ({
      selectedApplicationType: this.selectedApplicationType,
      tokenDetailResource: this.tokenService.tokenDetailResource.value
    }),
    computation: (source) => {
      const tokenSerial = source.tokenDetailResource()?.result?.value?.tokens[0]?.serial;
      if (!tokenSerial) {
        return new FilterValue();
      }
      return new FilterValue({ value: `serial:${tokenSerial}` });
    }
  });
  filterParams = computed<Record<string, string>>(() => {
    let allowedKeywords =
      this.selectedApplicationType() === "ssh"
        ? [...this.sshApiFilter, ...this.sshAdvancedApiFilter]
        : [...this.offlineApiFilter, ...this.offlineAdvancedApiFilter];
    const filterPairs = Array.from(this.machineFilter().filterMap.entries())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedKeywords.includes(key));

    if (filterPairs.length === 0) {
      return {};
    }
    let params: any = {};
    filterPairs.forEach(({ key, value }) => {
      if (["serial"].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (["hostname", "machineid", "resolver"].includes(key)) {
        params[key] = value;
      }
      if (this.selectedApplicationType() === "ssh" && ["service_id"].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (this.selectedApplicationType() === "offline" && ["count", "rounds"].includes(key)) {
        params[key] = value;
      }
    });
    return params;
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
      tokenApplicationResource: this.tokenService.tokenDetailResource.value
    }),
    computation: () => 0
  });
  tokenApplicationResource = httpResource<PiResponse<TokenApplications>>(() => {
    if (
      !(
        this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_APPLICATIONS) ||
        this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_DETAILS)
      ) ||
      !this.authService.actionAllowed("tokenlist")
    ) {
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
  tokenApplications: Signal<TokenApplications | undefined> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource, previous) => tokenApplicationResource?.result?.value ?? previous?.value
  });

  postAssignMachineToToken(args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: string;
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.post(`${this.baseUrl}token`, args, { headers }).pipe(shareReplay(1));
  }

  deleteAssignMachineToToken(args: { serial: string; application: string; mtid: string }): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete(`${this.baseUrl}token/${args.serial}/${args.application}/${args.mtid}`, { headers })
      .pipe(shareReplay(1));
  }

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string
  ): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.baseUrl}tokenoption`, { hostname, machineid, resolver, serial, application, mtid }, { headers })
      .pipe(shareReplay(1));
  }

  getAuthItem(challenge: string, hostname: string, application?: string): Observable<any> {
    const headers = this.authService.getHeaders();
    let params = new HttpParams().set("challenge", challenge).set("hostname", hostname);
    return this.http
      .get(application ? `${this.baseUrl}authitem/${application}` : `${this.baseUrl}authitem`, {
        headers,
        params
      })
      .pipe(shareReplay(1));
  }

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string
  ): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.baseUrl}token`, { hostname, machineid, resolver, serial, application }, { headers })
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

  deleteToken(serial: string, machineid: string, resolver: string, application: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete(`${this.baseUrl}token/${serial}/${machineid}/${resolver}/${application}`, { headers })
      .pipe(shareReplay(1));
  }

  deleteTokenMtid(serial: string, application: string, mtid: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.delete(`${this.baseUrl}token/${serial}/${application}/${mtid}`, { headers }).pipe(shareReplay(1));
  }

  onPageEvent(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort): void {
    this.sort.set($event);
  }
}
