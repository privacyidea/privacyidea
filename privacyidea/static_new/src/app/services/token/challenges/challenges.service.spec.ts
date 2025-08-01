import { TestBed } from '@angular/core/testing';

import { ChallengesService } from './challenges.service';
import { provideHttpClient } from '@angular/common/http';

describe('ChallengesService', () => {
  let challengesService: ChallengesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    challengesService = TestBed.inject(ChallengesService);
  });

  it('should be created', () => {
    expect(challengesService).toBeTruthy();
  });
});
