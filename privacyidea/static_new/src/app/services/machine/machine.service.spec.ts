import { TestBed } from '@angular/core/testing';

import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MachineService } from './machine.service';

describe('LocalService', () => {
  let service: MachineService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    service = TestBed.inject(MachineService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
