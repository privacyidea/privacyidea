import { httpResource, HttpResourceRef } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";
import { AuthService } from "../auth/auth.service";

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
}

@Injectable({
  providedIn: "root"
})
export class SystemService implements SystemServiceInterface {
  systemConfigResource = httpResource<any>(() => ({
    url: environment.proxyUrl + "/system/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  constructor(private authService: AuthService) {
  }
}
