import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {LocalService} from '../local/local.service';

@Injectable({
  providedIn: 'root'
})
export class ValidateService {
  private baseUrl = 'http://127.0.0.1:5000/validate/';

  constructor(private http: HttpClient, private localStore: LocalService) {
  }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'PI-Authorization': this.localStore.getData('bearer_token') || ''
    });
  }

  testToken(serial: string, otpOrPinToTest: string, otponly?: string): any {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}check`, {
      "serial": serial,
      "pass": otpOrPinToTest,
      "otponly": otponly
    }, {headers})
  }
}
