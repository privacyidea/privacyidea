import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { DialogService } from './dialog.service';

describe('ApplicationService', () => {
  let dialogService: DialogService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    dialogService = TestBed.inject(DialogService);
  });

  it('should be created', () => {
    expect(dialogService).toBeTruthy();
  });
});
