import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class SystemService {
  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  getSystemConfig(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(environment.proxyUrl + '/system/', { headers });
  }
}
