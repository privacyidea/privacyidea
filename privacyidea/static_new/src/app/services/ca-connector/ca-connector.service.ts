import { httpResource, HttpResourceRef } from '@angular/common/http';
import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import { LocalService } from '../local/local.service';

export type CaConnectors = CaConnector[];
export interface CaConnector {
  connectorname: string;
  templates?: Record<string, any>;
}

export interface CaConnectorServiceInterface {
  caConnectorServiceResource: HttpResourceRef<
    PiResponse<CaConnectors> | undefined
  >;
  caConnectors: WritableSignal<CaConnectors>;
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
