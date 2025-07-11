import { TestBed } from '@angular/core/testing';

import { LoadingService } from './loading-service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('LocalService', () => {
  let loadingService: LoadingService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    loadingService = TestBed.inject(LoadingService);
  });

  it('should be created', () => {
    expect(loadingService).toBeTruthy();
  });
});
