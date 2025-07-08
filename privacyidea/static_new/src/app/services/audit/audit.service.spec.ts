import { TestBed } from '@angular/core/testing';

import { AuditService } from './audit.service';
import { provideHttpClient } from '@angular/common/http';

describe('AuditService', () => {
  let auditService: AuditService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    auditService = TestBed.inject(AuditService);
  });

  it('should be created', () => {
    expect(auditService).toBeTruthy();
  });
});
