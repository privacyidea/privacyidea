import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';

export type RadiusServerConfigurations = {
  [key: string]: any;
};

export interface RadiusServerConfiguration {
  name: string;
  [key: string]: any; // Allow any additional properties
}

@Injectable({
  providedIn: 'root',
})
export class RadiusServerService {
  radiusServerConfigurationResource = httpResource<
    PiResponse<RadiusServerConfigurations>
  >(() => ({
    url: environment.proxyUrl + '/radiusserver/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  radiusServerConfigurations: WritableSignal<RadiusServerConfiguration[]> =
    linkedSignal({
      source: this.radiusServerConfigurationResource.value,
      computation: (source, previous) =>
        Object.entries(source?.result.value ?? {}).map(
          ([name, properties]) => ({ key: name, ...properties }),
        ) ||
        previous?.value ||
        [],
    });

  constructor(private localService: LocalService) {}
}
