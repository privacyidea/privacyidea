import { TestBed } from '@angular/core/testing';

import { CaConnectorService } from './ca-connector.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('CaConnectorService', () => {
  let service: CaConnectorService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CaConnectorService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
