import { Injectable } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class SystemService {
  systemConfigResource = httpResource<any>(() => ({
    url: environment.proxyUrl + '/system/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(private localService: LocalService) {}
}
