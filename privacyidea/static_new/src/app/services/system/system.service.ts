import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";

import { environment } from "../../../environments/environment";

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
}

@Injectable({
  providedIn: "root"
})
export class SystemService implements SystemServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  systemConfigResource = httpResource<any>(() => ({
    url: environment.proxyUrl + "/system/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));
}
