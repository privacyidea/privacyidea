import { TestBed } from '@angular/core/testing';

import { SystemService } from './system.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('SystemService', () => {
  let systemService: SystemService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    systemService = TestBed.inject(SystemService);
  });

  it('should be created', () => {
    expect(systemService).toBeTruthy();
  });
});
