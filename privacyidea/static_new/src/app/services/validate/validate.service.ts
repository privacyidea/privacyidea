import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {LocalService} from '../local/local.service';

@Injectable({
  providedIn: 'root'
})
export class ValidateService {
  private baseUrl = '/validate/';

  constructor(private http: HttpClient, private localService: LocalService) {
  }

  testToken(token_serial: string, otpOrPinToTest: string, otponly?: string): any {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.baseUrl}check`, {
      "serial": token_serial,
      "pass": otpOrPinToTest,
      "otponly": otponly
    }, {headers})
  }
}
