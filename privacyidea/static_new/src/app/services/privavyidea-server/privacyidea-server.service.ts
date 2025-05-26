import {
  computed,
  Injectable,
  linkedSignal,
  WritableSignal,
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';

export type RemoteServerOptions = RemoteServer[];
export interface RemoteServer {
  url: string;
  id: string;
}

@Injectable({
  providedIn: 'root',
})
export class PrivacyideaServerService {
  remoteServerResource = httpResource<PiResponse<RemoteServerOptions>>(() => ({
    url: environment.proxyUrl + '/privacyideaserver/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));
  remoteServerOptions: WritableSignal<RemoteServerOptions> = linkedSignal({
    source: this.remoteServerResource.value,
    computation: (source, previous) =>
      Array.isArray(source?.result?.value)
        ? source.result.value
        : (previous?.value ?? []),
  });

  constructor(private localService: LocalService) {}
}
