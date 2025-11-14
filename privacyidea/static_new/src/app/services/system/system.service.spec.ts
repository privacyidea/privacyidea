import { TestBed } from '@angular/core/testing';
import { SystemService } from './system.service';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { MockAuthService } from '../../../testing/mock-services/mock-auth-service';

describe('SystemService', () => {
  let service: SystemService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        SystemService
      ]
    });
    service = TestBed.inject(SystemService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});