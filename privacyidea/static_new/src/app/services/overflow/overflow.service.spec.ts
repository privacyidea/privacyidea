import { TestBed } from '@angular/core/testing';

import { OverflowService } from './overflow.service';

describe('OverflowService', () => {
  let overflowService: OverflowService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    overflowService = TestBed.inject(OverflowService);
  });

  it('should be created', () => {
    expect(overflowService).toBeTruthy();
  });
});
