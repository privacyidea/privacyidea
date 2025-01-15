import {TestBed} from '@angular/core/testing';

import {ValidateService} from './validate.service';
import {AppComponent} from '../../app.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';

describe('ValidateService', () => {
  let service: ValidateService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    service = TestBed.inject(ValidateService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
