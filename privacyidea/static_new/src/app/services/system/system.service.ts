import { Injectable } from '@angular/core';
import { HttpClient, httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class SystemService {
  systemConfigResource = httpResource<any>(() => ({
    url: environment.proxyUrl + '/system/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  getSystemConfig(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(environment.proxyUrl + '/system/', { headers });
  }
}
