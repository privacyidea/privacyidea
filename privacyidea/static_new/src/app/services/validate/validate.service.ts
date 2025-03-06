import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ValidateService {
  private baseUrl = environment.proxyUrl + '/validate/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  testToken(
    tokenSerial: string,
    otpOrPinToTest: string,
    otponly?: string,
  ): any {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.baseUrl}check`,
      {
        serial: tokenSerial,
        pass: otpOrPinToTest,
        otponly: otponly,
      },
      { headers },
    );
  }
}
