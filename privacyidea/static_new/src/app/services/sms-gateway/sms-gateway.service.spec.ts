import { TestBed } from '@angular/core/testing';

import { SmsGatewayService } from './sms-gateway.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('SmsGatewayService', () => {
  let smsGatewayService: SmsGatewayService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    smsGatewayService = TestBed.inject(SmsGatewayService);
  });

  it('should be created', () => {
    expect(smsGatewayService).toBeTruthy();
  });
});
