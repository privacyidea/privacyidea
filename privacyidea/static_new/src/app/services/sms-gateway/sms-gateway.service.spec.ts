import { TestBed } from '@angular/core/testing';

import { SmsGatewayService } from './sms-gateway.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('SmsGatewayService', () => {
  let service: SmsGatewayService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SmsGatewayService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
