import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { HttpClient, HttpParams, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, computed, effect, inject, linkedSignal, signal } from "@angular/core";
import { TableUtilsService, TableUtilsServiceInterface } from "../table-utils/table-utils.service";

import { Observable } from "rxjs";
import { PageEvent } from "@angular/material/paginator";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../app.routes";
import { Sort } from "@angular/material/sort";
import { environment } from "../../../environments/environment";

type TokenApplications = TokenApplication[];

export type Machines = Machine[];

export interface Machine {
  hostname: string[];
  id: string;
  ip: string;
  resolver_name: string;
}

export interface TokenApplication {
  application: string;
  id: number;
  serial: string;
  machine_id?: any;
  resolver?: any;
  type: string;
  options: {
    service_id?: string;
    user?: string;
  };
}

export interface MachineServiceInterface {
  sshApiFilter: string[];
  sshAdvancedApiFilter: string[];
  offlineApiFilter: string[];
  offlineAdvancedApiFilter: string[];
  machines: WritableSignal<Machines | undefined>;
  tokenApplications: WritableSignal<TokenApplications | undefined>;
  selectedApplicationType: WritableSignal<"ssh" | "offline">;
  pageSize: WritableSignal<number>;
  filterValue: WritableSignal<Record<string, string>>;
  filterValueString: WritableSignal<string>;
  filterParams: () => Record<string, string>;
  sort: WritableSignal<Sort>;
  pageIndex: WritableSignal<number>;
  machinesResource: any;
  tokenApplicationResource: any;

  postAssignMachineToToken(args: {
    service_id: string;
    user: string;
    serial: string;
    application: string;
    machineid: string;
    resolver: string;
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
  private readonly http: HttpClient = inject(HttpClient);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  private baseUrl = environment.proxyUrl + "/machine/";
  sshApiFilter = ["serial", "service_id"];
  sshAdvancedApiFilter = ["hostname", "machineid & resolver"];
  offlineApiFilter = ["serial", "count", "rounds"];
  offlineAdvancedApiFilter = ["hostname", "machineid & resolver"];
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
  pageSize = linkedSignal({
    source: this.selectedApplicationType,
    computation: () => 10
  });

  machinesResource = httpResource<PiResponse<Machines>>(() => {
    if (!this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_APPLICATIONS)) {
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
  filterValue: WritableSignal<Record<string, string>> = linkedSignal({
    source: this.selectedApplicationType,
    // This gets also updated by the effect in the constructor, when filterValueString changes.
    computation: () => ({})
  });
  filterValueString: WritableSignal<string> = linkedSignal({
    source: this.filterValue,
    computation: () =>
      Object.entries(this.filterValue())
        .map(([key, value]) => `${key}: ${value}`)
        .join(" ")
  });
  filterParams = computed<Record<string, string>>(() => {
    let allowedKeywords =
      this.selectedApplicationType() === "ssh"
        ? [...this.sshApiFilter, ...this.sshAdvancedApiFilter]
        : [...this.offlineApiFilter, ...this.offlineAdvancedApiFilter];

    const filterPairs = Object.entries(this.filterValue())
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
      filter: this.filterValue(),
      sort: this.sort()
    }),
    computation: () => 0
  });
  tokenApplicationResource = httpResource<PiResponse<TokenApplications>>(() => {
    if (!this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_APPLICATIONS)) {
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
  tokenApplications: WritableSignal<TokenApplications | undefined> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource, previous) => tokenApplicationResource?.result?.value ?? previous?.value
  });

  constructor() {
    effect(() => {
      const recordsFromText = this.tableUtilsService.recordsFromText(this.filterValueString());
      this.filterValue.set(recordsFromText);
    });
  }

  postAssignMachineToToken(args: {
    service_id: string;
    user: string;
    serial: string;
    application: string;
    machineid: string;
    resolver: string;
  }): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.post(`${this.baseUrl}token`, args, { headers });
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
    return this.http.post(
      `${this.baseUrl}tokenoption`,
      { hostname, machineid, resolver, serial, application, mtid },
      { headers }
    );
  }

  getAuthItem(challenge: string, hostname: string, application?: string): Observable<any> {
    const headers = this.authService.getHeaders();
    let params = new HttpParams().set("challenge", challenge).set("hostname", hostname);
    return this.http.get(application ? `${this.baseUrl}authitem/${application}` : `${this.baseUrl}authitem`, {
      headers,
      params
    });
  }

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string
  ): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.post(`${this.baseUrl}token`, { hostname, machineid, resolver, serial, application }, { headers });
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
    return this.http.get<PiResponse<Machines>>(`${this.baseUrl}`, {
      headers,
      params
    });
  }

  deleteToken(serial: string, machineid: string, resolver: string, application: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.delete(`${this.baseUrl}token/${serial}/${machineid}/${resolver}/${application}`, { headers });
  }

  deleteTokenMtid(serial: string, application: string, mtid: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.delete(`${this.baseUrl}token/${serial}/${application}/${mtid}`, { headers });
  }

  onPageEvent(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort): void {
    this.sort.set($event);
  }
}
