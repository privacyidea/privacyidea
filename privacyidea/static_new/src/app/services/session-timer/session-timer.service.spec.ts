import { TestBed } from '@angular/core/testing';

import { SessionTimerService } from './session-timer.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('SessionTimerService', () => {
  let sessionTimerService: SessionTimerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    sessionTimerService = TestBed.inject(SessionTimerService);
  });

  it('should be created', () => {
    expect(sessionTimerService).toBeTruthy();
  });
});
