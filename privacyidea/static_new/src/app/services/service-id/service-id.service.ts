import { httpResource, HttpResourceRef } from '@angular/common/http';
import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import { LocalService } from '../local/local.service';

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
  providedIn: 'root',
})
export class ServiceIdService implements ServiceIdServiceInterface {
  serviceIdResource = httpResource<PiResponse<ServiceIds>>(() => ({
    url: environment.proxyUrl + '/serviceid/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));
  serviceIds: WritableSignal<ServiceId[]> = linkedSignal({
    source: this.serviceIdResource.value,
    computation: (source, previous) => {
      const value = source?.result?.value;
      if (!value) {
        return previous?.value ?? [];
      }
      const array = Object.entries(value).map(
        ([name, { description, id }]) => ({
          name,
          description,
          id,
        }),
      );
      return array;
    },
  });

  constructor(private localService: LocalService) {}
}
