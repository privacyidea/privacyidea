import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class SmsGatewayService {
  smsGatewayResource = httpResource<any>(() => ({
    url: environment.proxyUrl + '/smsgateway/',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));

  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  getSmsGatewayOptions(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(environment.proxyUrl + '/smsgateway/', { headers });
  }
}
