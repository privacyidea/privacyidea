import {
  fakeAsync,
  flushMicrotasks,
  TestBed,
  tick,
} from '@angular/core/testing';
import { HttpClient, provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { signal } from '@angular/core';
import { TokenService } from './token.service';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';
import { ContentService } from '../content/content.service';
import { PiResponse } from '../../app.component';

class MockLocalService {
  getHeaders = jest
    .fn()
    .mockReturnValue({ Authorization: 'Bearer FAKE_TOKEN' });
}

class MockNotificationService {
  openSnackBar = jest.fn();
}

class MockContentService {
  tokenSerial = signal('');
  selectedContent = signal<'token_overview'>('token_overview');
}

describe('TokenService', () => {
  let tokenService: TokenService;
  let http: HttpClient;
  let postSpy: jest.SpyInstance;
  let localService: MockLocalService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        TokenService,
        { provide: LocalService, useClass: MockLocalService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
      ],
    });

    tokenService = TestBed.inject(TokenService);
    http = TestBed.inject(HttpClient);
    postSpy = jest.spyOn(http, 'post');
    localService = TestBed.inject(LocalService) as any;

    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('toggleActive()', () => {
    it('POSTs to /disable when active=true', () => {
      const backend: PiResponse<boolean> = {
        success: true,
        detail: undefined,
      } as any;

      postSpy.mockReturnValue(of(backend));

      let result!: PiResponse<boolean>;
      tokenService.toggleActive('HOTP1', true).subscribe((r) => (result = r));

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}disable`,
        { serial: 'HOTP1' },
        { headers: localService.getHeaders() },
      );
      expect(result).toEqual(backend);
    });

    it('POSTs to /enable when active=false', () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.toggleActive('HOTP1', false).subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}enable`,
        { serial: 'HOTP1' },
        { headers: localService.getHeaders() },
      );
    });
  });

  it('resetFailCount posts /reset with correct body', () => {
    postSpy.mockReturnValue(of({ success: true } as any));

    tokenService.resetFailCount('HOTP2').subscribe();

    expect(postSpy).toHaveBeenCalledWith(
      `${tokenService.tokenBaseUrl}reset`,
      { serial: 'HOTP2' },
      { headers: localService.getHeaders() },
    );
  });

  describe('pollTokenRolloutState()', () => {
    it('polls until rollout_state !== "clientwait"', fakeAsync(() => {
      const first = {
        result: { value: { tokens: [{ rollout_state: 'clientwait' }] } },
      };
      const second = {
        result: { value: { tokens: [{ rollout_state: 'clientwait' }] } },
      };
      const done = {
        result: { value: { tokens: [{ rollout_state: 'enrolled' }] } },
      };

      jest
        .spyOn(tokenService, 'getTokenDetails')
        .mockReturnValueOnce(of(first as any))
        .mockReturnValueOnce(of(second as any))
        .mockReturnValueOnce(of(done as any));

      const emissions: any[] = [];
      tokenService
        .pollTokenRolloutState({ tokenSerial: 'HOTP3', initDelay: 0 })
        .subscribe((r) => emissions.push(r));

      tick(0);
      tick(2000);
      tick(2000);
      flushMicrotasks();

      expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
      expect(emissions.length).toBe(3);
      expect(emissions[2]).toEqual(done);

      tick(4000);
      expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
    }));
  });
});
