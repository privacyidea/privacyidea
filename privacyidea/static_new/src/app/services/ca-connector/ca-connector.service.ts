import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';

export type CaConnectors = CaConnector[];
export interface CaConnector {
  connectorname: string;
  templates?: Record<string, any>;
}

@Injectable({
  providedIn: 'root',
})
export class CaConnectorService {
  caConnectorServiceResource = httpResource<PiResponse<CaConnectors>>(() => ({
    url: environment.proxyUrl + '/caconnector/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  caConnectors: WritableSignal<CaConnectors> = linkedSignal({
    source: this.caConnectorServiceResource.value,
    computation: (source, previous) =>
      source?.result?.value ?? previous?.value ?? [],
  });

  constructor(private localService: LocalService) {}
}
