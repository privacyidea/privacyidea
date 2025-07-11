import { TestBed } from '@angular/core/testing';

import { TableUtilsService } from './table-utils.service';
import { AppComponent } from '../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('TableUtilsService', () => {
  let tableUtilsService: TableUtilsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    tableUtilsService = TestBed.inject(TableUtilsService);
  });

  it('should be created', () => {
    expect(tableUtilsService).toBeTruthy();
  });
});
