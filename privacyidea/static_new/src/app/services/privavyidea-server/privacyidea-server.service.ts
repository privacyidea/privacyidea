import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";

import { PiResponse } from "../../app.component";
import { environment } from "../../../environments/environment";

export type RemoteServerOptions = RemoteServer[];

export interface RemoteServer {
  url: string;
  id: string;
  name: string;
}

export interface PrivacyideaServerServiceInterface {
  remoteServerResource: HttpResourceRef<PiResponse<RemoteServerOptions> | undefined>;
  remoteServerOptions: WritableSignal<RemoteServerOptions>;
}

@Injectable({
  providedIn: "root"
})
export class PrivacyideaServerService implements PrivacyideaServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  remoteServerResource = httpResource<PiResponse<RemoteServerOptions>>(() => ({
    url: environment.proxyUrl + "/privacyideaserver/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  remoteServerOptions: WritableSignal<RemoteServerOptions> = linkedSignal({
    source: this.remoteServerResource.value,
    computation: (source, previous) => {
      let servers = previous?.value ?? [];
      if (source?.result?.value) {
        let response = source.result.value;
        servers = Object.entries(response).map(([server, options]) => {
          return {
            name: server,
            url: options.url,
            id: options.id
          };
        });
      }
      return servers;
    }
  });
}
