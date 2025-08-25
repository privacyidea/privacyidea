import { httpResource, HttpResourceRef } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService } from "../auth/auth.service";

type SmsGateways = SmsGateway[];

export interface SmsGateway {
  id: number;
  name: string;
  description?: string;
  providermodule: string;
  options: Record<string, string>;
  headers: any;
}

export interface SmsGatewayServiceInterface {
  smsGatewayResource: HttpResourceRef<PiResponse<SmsGateways> | undefined>;
}

@Injectable({
  providedIn: "root"
})
export class SmsGatewayService {
  smsGatewayResource = httpResource<PiResponse<SmsGateways>>(() => ({
    url: environment.proxyUrl + "/smsgateway/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  constructor(private authService: AuthService) {
  }
}
