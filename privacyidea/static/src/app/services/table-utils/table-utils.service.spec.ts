import { TestBed } from '@angular/core/testing';

import { TableUtilsService } from './table-utils.service';

describe('TableUtilsService', () => {
  let service: TableUtilsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TableUtilsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
