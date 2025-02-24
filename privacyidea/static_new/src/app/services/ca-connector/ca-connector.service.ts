import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';

@Injectable({
  providedIn: 'root',
})
export class CaConnectorService {
  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  getCaConnectorServiceOptions() {
    const headers = this.localService.getHeaders();
    return this.http.get('/caconnector/', { headers });
  }
}
