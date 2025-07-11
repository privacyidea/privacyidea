import { TestBed } from '@angular/core/testing';

import { ContainerService } from './container.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('ContainerService', () => {
  let containerService: ContainerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    containerService = TestBed.inject(ContainerService);
  });

  it('should be created', () => {
    expect(containerService).toBeTruthy();
  });
});
