import { httpResource, HttpResourceRef } from '@angular/common/http';
import { Injectable, linkedSignal, WritableSignal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import { LocalService } from '../local/local.service';

export type RemoteServerOptions = RemoteServer[];
export interface RemoteServer {
  url: string;
  id: string;
}

export interface PrivacyideaServerServiceInterface {
  remoteServerResource: HttpResourceRef<
    PiResponse<RemoteServerOptions> | undefined
  >;
  remoteServerOptions: WritableSignal<RemoteServerOptions>;
}

@Injectable({
  providedIn: 'root',
})
export class PrivacyideaServerService
  implements PrivacyideaServerServiceInterface
{
  remoteServerResource = httpResource<PiResponse<RemoteServerOptions>>(() => ({
    url: environment.proxyUrl + '/privacyideaserver/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));
  remoteServerOptions: WritableSignal<RemoteServerOptions> = linkedSignal({
    source: this.remoteServerResource.value,
    computation: (source, previous) =>
      Array.isArray(source?.result?.value)
        ? source.result?.value
        : (previous?.value ?? []),
  });

  constructor(private localService: LocalService) {}
}
