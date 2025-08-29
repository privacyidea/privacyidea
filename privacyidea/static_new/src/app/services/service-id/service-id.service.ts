import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

type ServiceIds = {
  [key: string]: _ServiceId;
};

interface _ServiceId {
  description: string;
  id: number;
}

export interface ServiceId {
  name: string;
  description: string;
  id: number;
}

export interface ServiceIdServiceInterface {
  serviceIdResource: HttpResourceRef<PiResponse<ServiceIds> | undefined>;
  serviceIds: WritableSignal<ServiceId[]>;
}

@Injectable({
  providedIn: "root"
})
export class ServiceIdService implements ServiceIdServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  serviceIdResource = httpResource<PiResponse<ServiceIds>>(() => ({
    url: environment.proxyUrl + "/serviceid/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  serviceIds: WritableSignal<ServiceId[]> = linkedSignal({
    source: this.serviceIdResource.value,
    computation: (source, previous) => {
      const value = source?.result?.value;
      if (!value) {
        return previous?.value ?? [];
      }
      return Object.entries(value).map(([name, { description, id }]) => ({
        name,
        description,
        id
      }));
    }
  });
}
