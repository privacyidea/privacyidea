import { TestBed } from '@angular/core/testing';

import { LocalService } from './local.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('LocalService', () => {
  let localService: LocalService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    localService = TestBed.inject(LocalService);
  });

  it('should be created', () => {
    expect(localService).toBeTruthy();
  });
});
