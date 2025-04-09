import { TestBed } from '@angular/core/testing';

import { ContainerService } from './container.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('ContainerService', () => {
  let service: ContainerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    service = TestBed.inject(ContainerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
