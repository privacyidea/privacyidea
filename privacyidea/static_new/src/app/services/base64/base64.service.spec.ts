import { TestBed } from '@angular/core/testing';

import { Base64Service } from './base64.service';

describe('Base64Service', () => {
  let service: Base64Service;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Base64Service);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
