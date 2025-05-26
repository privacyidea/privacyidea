import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';

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

@Injectable({
  providedIn: 'root',
})
export class ServiceIdService {
  serviceIdResource = httpResource<PiResponse<ServiceIds>>(() => ({
    url: environment.proxyUrl + '/serviceid/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));
  serviceIds: WritableSignal<ServiceId[]> = linkedSignal({
    source: this.serviceIdResource.value,
    computation: (source, previous) => {
      const value = source?.result.value;
      console.log('value', value);
      console.log('previous', previous?.value);
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
      console.log('list', array);
      return array;
    },
  });

  constructor(private localService: LocalService) {}
}
