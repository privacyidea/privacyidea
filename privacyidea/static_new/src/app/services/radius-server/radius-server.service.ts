import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

export type RadiusServerConfigurations = {
  [key: string]: any;
};

export interface RadiusServerConfiguration {
  name: string;
  description: string;
  dictionary: string;
  port: number;
  retries: number;
  server: string;
  timeout: number;
}

export interface RadiusServerServiceInterface {
  radiusServerConfigurationResource: HttpResourceRef<PiResponse<RadiusServerConfigurations> | undefined>;
  radiusServerConfigurations: WritableSignal<RadiusServerConfiguration[]>;
}

@Injectable({
  providedIn: "root"
})
export class RadiusServerService implements RadiusServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  radiusServerConfigurationResource = httpResource<PiResponse<RadiusServerConfigurations>>(() => ({
    url: environment.proxyUrl + "/radiusserver/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  radiusServerConfigurations: WritableSignal<RadiusServerConfiguration[]> = linkedSignal({
    source: this.radiusServerConfigurationResource.value,
    computation: (source, previous) =>
      Object.entries(source?.result?.value ?? {}).map(([name, properties]) => ({ name, ...properties })) ??
      previous?.value ??
      []
  });
}
