import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpErrorResponse,
  provideHttpClient,
} from '@angular/common/http';
import { of, throwError } from 'rxjs';
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
  let deleteSpy: jest.SpyInstance;
  let localService: MockLocalService;
  let notificationService: MockNotificationService;

  beforeEach(() => {
    TestBed.resetTestingModule();
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
    deleteSpy = jest.spyOn(http, 'delete');
    localService = TestBed.inject(LocalService) as any;
    notificationService = TestBed.inject(NotificationService) as any;

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

    it('notifies user and propagates error on failure', (done) => {
      const error = new HttpErrorResponse({
        error: { result: { error: { message: 'boom' } } },
        status: 500,
      });
      postSpy.mockReturnValue(throwError(() => error));

      tokenService.toggleActive('HOTP1', true).subscribe({
        next: () => {
          fail('expected error');
        },
        error: (err) => {
          expect(err).toBe(error);
          expect(notificationService.openSnackBar).toHaveBeenCalledWith(
            'Failed to toggle active. boom',
          );
          done();
        },
      });
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

  it('deleteToken delegates to HttpClient.delete', () => {
    deleteSpy.mockReturnValue(of({ success: true } as any));

    tokenService.deleteToken('DEL1').subscribe();

    expect(deleteSpy).toHaveBeenCalledWith(`${tokenService.tokenBaseUrl}DEL1`, {
      headers: localService.getHeaders(),
    });
  });

  describe('saveTokenDetail()', () => {
    it('maps "maxfail" to "max_failcount"', () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.saveTokenDetail('SER', 'maxfail', 3).subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}set`,
        { serial: 'SER', max_failcount: 3 },
        { headers: localService.getHeaders() },
      );
    });

    it('passes other keys through unchanged', () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.saveTokenDetail('SER', 'description', 'A token').subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}set`,
        { serial: 'SER', description: 'A token' },
        { headers: localService.getHeaders() },
      );
    });
  });

  describe('setTokenInfos()', () => {
    beforeEach(() => postSpy.mockClear());

    it('routes special keys via /set and others via /info', () => {
      const infos = { hashlib: 'sha1', custom: 'foo' };
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService.setTokenInfos('SER', infos).subscribe();

      expect(postSpy).toHaveBeenNthCalledWith(
        1,
        `${tokenService.tokenBaseUrl}set`,
        { serial: 'SER', hashlib: 'sha1' },
        { headers: localService.getHeaders() },
      );
      expect(postSpy).toHaveBeenNthCalledWith(
        2,
        `${tokenService.tokenBaseUrl}info/SER/custom`,
        { value: 'foo' },
        { headers: localService.getHeaders() },
      );
    });
  });

  describe('assignUser()', () => {
    it('translates empty strings to null', () => {
      postSpy.mockReturnValue(of({ success: true } as any));

      tokenService
        .assignUser({ tokenSerial: 'SER', username: '', realm: '', pin: '123' })
        .subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}assign`,
        { serial: 'SER', user: null, realm: null, pin: '123' },
        { headers: localService.getHeaders() },
      );
    });
  });

  describe('unassignUserFromAll()', () => {
    it('returns an empty array for empty input', (done) => {
      tokenService.unassignUserFromAll([]).subscribe((r) => {
        expect(r).toEqual([]);
        done();
      });
    });
  });

  describe('setTokengroup()', () => {
    it('accepts a single string', () => {
      postSpy.mockReturnValue(of({ success: true } as any));
      tokenService.setTokengroup('SER', 'group1').subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}group/SER`,
        { groups: ['group1'] },
        { headers: localService.getHeaders() },
      );
    });

    it('accepts an object and flattens values', () => {
      postSpy.mockReturnValue(of({ success: true } as any));
      tokenService
        .setTokengroup('SER', { a: 'g1', b: 'g2' } as any)
        .subscribe();

      expect(postSpy).toHaveBeenCalledWith(
        `${tokenService.tokenBaseUrl}group/SER`,
        { groups: ['g1', 'g2'] },
        { headers: localService.getHeaders() },
      );
    });
  });

  describe('pollTokenRolloutState()', () => {
    it('emits error once and stops polling when request fails', async () => {
      jest.useFakeTimers();
      const boom = new HttpErrorResponse({
        error: { result: { error: { message: 'poll-error' } } },
        status: 500,
      });
      jest
        .spyOn(tokenService, 'getTokenDetails')
        .mockReturnValueOnce(throwError(() => boom));

      const errors: any[] = [];
      tokenService
        .pollTokenRolloutState({ tokenSerial: 'SER', initDelay: 0 })
        .subscribe({ error: (e) => errors.push(e) });

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      expect(errors[0]).toBe(boom);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        'Failed to poll token state. poll-error',
      );
    });
    jest.useRealTimers();
  });

  it('polls until rollout_state !== "clientwait"', async () => {
    jest.useFakeTimers();
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

    // wait four ticks but getTokenDetails should be called three times
    jest.runOnlyPendingTimers();
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
    expect(emissions.length).toBe(3);
    expect(emissions[2]).toEqual(done);

    jest.advanceTimersByTime(4000);
    expect(tokenService.getTokenDetails).toHaveBeenCalledTimes(3);
    jest.useRealTimers();
  });
});
