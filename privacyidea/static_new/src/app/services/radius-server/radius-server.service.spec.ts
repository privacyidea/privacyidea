import { TestBed } from '@angular/core/testing';

import { RadiusServerService } from './radius-server.service';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('RadiusServerService', () => {
  let radiusServerService: RadiusServerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    radiusServerService = TestBed.inject(RadiusServerService);
  });

  it('should be created', () => {
    expect(radiusServerService).toBeTruthy();
  });
});
