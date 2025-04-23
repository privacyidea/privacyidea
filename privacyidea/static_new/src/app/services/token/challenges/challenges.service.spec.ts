import { TestBed } from '@angular/core/testing';

import { ChallengesService } from './challenges.service';

describe('ChallengesService', () => {
  let service: ChallengesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChallengesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
