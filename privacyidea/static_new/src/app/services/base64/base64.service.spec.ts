import { TestBed } from '@angular/core/testing';

import { Base64Service } from './base64.service';

describe('Base64Service', () => {
  let base64Service: Base64Service;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    base64Service = TestBed.inject(Base64Service);
  });

  it('should be created', () => {
    expect(base64Service).toBeTruthy();
  });
});
