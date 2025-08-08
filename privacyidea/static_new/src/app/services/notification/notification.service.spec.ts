import { TestBed } from '@angular/core/testing';

import { NotificationService } from './notification.service';

describe('NotificationService', () => {
  let notificationService: NotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    notificationService = TestBed.inject(NotificationService);
  });

  it('should be created', () => {
    expect(notificationService).toBeTruthy();
  });
});
