import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ServiceIdService {
  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  getServiceIdOptions(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(environment.proxyUrl + '/serviceid/', { headers });
  }
}
