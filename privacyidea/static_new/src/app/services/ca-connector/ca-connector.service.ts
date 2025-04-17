import { Injectable } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class CaConnectorService {
  caConnectorServiceResource = httpResource<any>(() => ({
    url: environment.proxyUrl + '/caconnector/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(private localService: LocalService) {}
}
