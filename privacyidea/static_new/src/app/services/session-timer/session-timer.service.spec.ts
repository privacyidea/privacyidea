import { TestBed } from '@angular/core/testing';

import { SessionTimerService } from './session-timer.service';
import {AppComponent} from '../../app.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';

describe('SessionTimerService', () => {
  let service: SessionTimerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    service = TestBed.inject(SessionTimerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
