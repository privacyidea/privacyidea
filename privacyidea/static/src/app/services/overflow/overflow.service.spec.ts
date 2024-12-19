import { TestBed } from '@angular/core/testing';

import { OverflowService } from './overflow.service';

describe('OverflowService', () => {
  let service: OverflowService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OverflowService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
