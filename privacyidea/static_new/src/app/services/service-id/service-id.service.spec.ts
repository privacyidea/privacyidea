import { TestBed } from '@angular/core/testing';

import { ServiceIdService } from './service-id.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('ServiceIdService', () => {
  let service: ServiceIdService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ServiceIdService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
