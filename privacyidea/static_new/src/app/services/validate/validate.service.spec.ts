import { TestBed, fakeAsync, tick, waitForAsync } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { ValidateService, ValidateCheckResponse } from './validate.service';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';
import { Base64Service } from '../base64/base64.service';
import { AuthService, AuthResponse } from '../auth/auth.service';

class MockLocalService {
  getHeaders = jest
    .fn()
    .mockReturnValue({ Authorization: 'Bearer FAKE_TOKEN' });
}
class MockNotificationService {
  openSnackBar = jest.fn();
}
class MockBase64Service {
  bytesToBase64 = jest.fn(() => 'b64');
}
class MockAuthService {
  authenticate = jest.fn().mockReturnValue(of({ success: true } as any));
}

describe('ValidateService', () => {
  let validateService: ValidateService;
  let http: HttpClient;
  let postSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;

  let local: MockLocalService;
  let notif: MockNotificationService;
  let b64: MockBase64Service;
  let auth: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        ValidateService,
        { provide: LocalService, useClass: MockLocalService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: Base64Service, useClass: MockBase64Service },
        { provide: AuthService, useClass: MockAuthService },
      ],
    });

    validateService = TestBed.inject(ValidateService);
    http = TestBed.inject(HttpClient);
    postSpy = jest.spyOn(http, 'post');

    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    local = TestBed.inject(LocalService) as unknown as MockLocalService;
    notif = TestBed.inject(
      NotificationService,
    ) as unknown as MockNotificationService;
    b64 = TestBed.inject(Base64Service) as unknown as MockBase64Service;
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  afterEach(() => {
    jest.restoreAllMocks();
    consoleErrorSpy.mockRestore();
  });

  it('should be created', () => {
    expect(validateService).toBeTruthy();
  });

  it('testToken should POST correct payload and return API result', () => {
    const apiResp: ValidateCheckResponse = {
      success: true,
      detail: { message: 'OK' },
    } as unknown as ValidateCheckResponse;
    postSpy.mockReturnValue(of(apiResp));

    let result!: ValidateCheckResponse;
    validateService
      .testToken('HOTP1', '000000', '1')
      .subscribe((r) => (result = r));

    expect(postSpy).toHaveBeenCalledWith(
      expect.stringMatching(/\/validate\/check$/),
      { serial: 'HOTP1', pass: '000000', otponly: '1' },
      { headers: local.getHeaders() },
    );
    expect(result).toEqual(apiResp);
  });

  describe('authenticatePasskey', () => {
    it('should error and notify when WebAuthn is unsupported', async () => {
      let restore: () => void;
      if ('PublicKeyCredential' in window) {
        const spy = jest
          .spyOn(window as any, 'PublicKeyCredential', 'get')
          .mockReturnValue(undefined);
        restore = () => spy.mockRestore();
      } else {
        (window as any).PublicKeyCredential = undefined;
        restore = () => delete (window as any).PublicKeyCredential;
      }

      validateService.authenticatePasskey().subscribe({
        next: () => fail('expected error'),
        error: (err) => {
          expect(err.message).toMatch(/WebAuthn is not supported/i);
          expect(notif.openSnackBar).toHaveBeenCalledWith(
            'WebAuthn is not supported by this browser.',
          );
        },
      });

      restore();
    });

    it('should initialise, collect credentials, then POST /check when isTest=true', async () => {
      const credGet = jest.fn().mockResolvedValue({
        id: 'cred-1',
        response: {
          authenticatorData: new ArrayBuffer(2),
          clientDataJSON: new ArrayBuffer(2),
          signature: new ArrayBuffer(2),
          userHandle: new ArrayBuffer(2),
        },
      });

      const pkc: any = (window as any).PublicKeyCredential ?? {};
      pkc.isConditionalMediationAvailable = jest.fn().mockResolvedValue(true);
      if (!(window as any).PublicKeyCredential) {
        (window as any).PublicKeyCredential = pkc;
      }

      Object.defineProperty(navigator, 'credentials', {
        value: { get: credGet },
        configurable: true,
      });

      const initResp = {
        detail: {
          passkey: {
            challenge: 'abc',
            rpId: 'example.com',
            transaction_id: 'tid-42',
          },
        },
      };
      let capturedCheckBody: any;

      postSpy
        .mockImplementationOnce(() => of(initResp))
        .mockImplementationOnce((url, body) => {
          capturedCheckBody = body;
          return of({ success: true });
        });

      let final!: AuthResponse;
      validateService
        .authenticatePasskey({ isTest: true })
        .subscribe((r) => (final = r as AuthResponse));

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      jest.runOnlyPendingTimers();
      await Promise.resolve();

      expect(postSpy).toHaveBeenCalledTimes(2);
      expect(postSpy.mock.calls[0][0]).toMatch(/\/validate\/initialize$/);
      expect(postSpy.mock.calls[1][0]).toMatch(/\/validate\/check$/);
      expect(capturedCheckBody).toMatchObject({
        transaction_id: 'tid-42',
        credential_id: 'cred-1',
      });

      expect(b64.bytesToBase64).toHaveBeenCalled();
      expect(auth.authenticate).not.toHaveBeenCalled();
      expect(final).toEqual({ success: true });
    });
  });
});
