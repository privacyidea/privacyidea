import { Injectable } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';

type SmsGateways = SmsGateway[];
export interface SmsGateway {
  id: number;
  name: string;
  description?: string;
  providermodule: string;
  options: Record<string, string>;
  headers: any;
}

@Injectable({
  providedIn: 'root',
})
export class SmsGatewayService {
  smsGatewayResource = httpResource<PiResponse<SmsGateways>>(() => ({
    url: environment.proxyUrl + '/smsgateway/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(private localService: LocalService) {}
}
