import { TestBed } from '@angular/core/testing';

import { RealmService } from './realm.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('RealmService', () => {
  let service: RealmService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    service = TestBed.inject(RealmService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
