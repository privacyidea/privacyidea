import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";
import { LocalService } from "../local/local.service";
import { Observable } from "rxjs";

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  getSystemConfigResource(): Observable<SystemConfigResponse>;
}

interface SystemConfigResponse {
  result?: {
    value?: Record<string, any>;
    [key: string]: any;
  };
  [key: string]: any;
}

@Injectable({
  providedIn: "root"
})
export class SystemService implements SystemServiceInterface {
  // Usable in signals
  systemConfigResource = httpResource<any>(() => ({
    url: environment.proxyUrl + "/system/",
    method: "GET",
    headers: this.localService.getHeaders()
  }));

  // Usable in observables (if the result needs to be processed immediately)
  private readonly http: HttpClient = inject(HttpClient);
  getSystemConfigResource(): Observable<SystemConfigResponse> {
    const headers = this.localService.getHeaders();
    return this.http.get(`${environment.proxyUrl}/system/`, {headers});
  }

  constructor(private localService: LocalService) {
  }
}
