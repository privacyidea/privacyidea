import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { of, throwError } from 'rxjs';

import { EnrollPasskeyComponent } from './enroll-passkey.component';
import {
  TokenService,
  BasicEnrollmentOptions,
  EnrollmentResponse,
  EnrollmentResponseDetail,
} from '../../../../services/token/token.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';

class MockTokenService {
  tokenTypeOptions = () => [{ key: 'passkey', text: 'Passkey Token' }];
  enrollToken = jasmine.createSpy('enrollToken');
  deleteToken = jasmine.createSpy('deleteToken').and.returnValue(of({}));
}

class MockNotificationService {
  openSnackBar = jasmine.createSpy('openSnackBar');
}

class MockBase64Service {
  base64URLToBytes = (s: string) => new Uint8Array(s.length);
  bytesToBase64 = (b: Uint8Array) => 'base64string';
}

class MockMatDialog {
  open = jasmine
    .createSpy('open')
    .and.returnValue({
      close: jasmine.createSpy('close'),
    } as MatDialogRef<any>);
}

describe('EnrollPasskeyComponent', () => {
  let component: EnrollPasskeyComponent;
  let fixture: ComponentFixture<EnrollPasskeyComponent>;
  let mockTokenService: MockTokenService;
  let mockNotificationService: MockNotificationService;
  let mockMatDialog: MockMatDialog;
  let mockNavigatorCredentials: jasmine.Spy;

  beforeEach(async () => {
    mockTokenService = new MockTokenService();
    mockNotificationService = new MockNotificationService();
    mockMatDialog = new MockMatDialog();

    await TestBed.configureTestingModule({
      imports: [EnrollPasskeyComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: mockTokenService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: Base64Service, useClass: MockBase64Service },
        { provide: MatDialog, useValue: mockMatDialog },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPasskeyComponent);
    component = fixture.componentInstance;

    // Mock navigator.credentials.create
    mockNavigatorCredentials = spyOn(navigator.credentials, 'create');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit aditionalFormFieldsChange with an empty object on init', (done) => {
    component.aditionalFormFieldsChange.subscribe((controls) => {
      expect(controls).toEqual({});
      done();
    });
    component.ngOnInit();
  });

  it('should emit clickEnrollChange with onClickEnroll function on init', (done) => {
    component.clickEnrollChange.subscribe((func) => {
      expect(func).toBe(component.onClickEnroll);
      done();
    });
    component.ngOnInit();
  });

  describe('onClickEnroll', () => {
    const basicOptions: BasicEnrollmentOptions = {
      type: 'passkey',
      description: 'test',
      user: 'u',
      pin: 'p',
    };
    const mockStep1Response: EnrollmentResponse = {
      detail: {
        serial: 'serial123',
        transaction_id: 'tx123',
        passkey_registration: {
          rp: { id: 'localhost', name: 'Test RP' },
          user: { id: 'dXNlcg==', name: 'testUser', displayName: 'Test User' }, // "user" base64url encoded
          challenge: 'randomChallengeString', // Will be converted by base64Service mock
          pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
          excludeCredentials: [],
          authenticatorSelection: { userVerification: 'preferred' },
          timeout: 60000,
          attestation: 'direct',
          extensions: {},
        },
      } as EnrollmentResponseDetail,
      result: { status: true, value: {} },
    };

    it('should handle browser not supporting WebAuthn', () => {
      (navigator.credentials as any).create = undefined; // Simulate no support
      const result = component.onClickEnroll(basicOptions);
      result?.subscribe({
        error: (err) =>
          expect(err.message).toContain('Passkey/WebAuthn is not supported'),
      });
      expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith(
        jasmine.stringMatching(/not supported by this browser/),
      );
      (navigator.credentials as any).create = mockNavigatorCredentials; // Restore
    });

    it('should handle step 1 (initial enroll) failure', fakeAsync(() => {
      mockTokenService.enrollToken.and.returnValue(
        throwError(() => new Error('Step 1 failed')),
      );
      component.onClickEnroll(basicOptions)?.subscribe({
        error: () => {}, // Expected error
      });
      tick();
      expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith(
        jasmine.stringMatching(
          /Passkey registration process failed: Step 1 failed/,
        ),
      );
    }));

    it('should handle successful multi-step enrollment', fakeAsync(() => {
      mockTokenService.enrollToken.and.callFake((options: any) => {
        if (options.type === 'passkey' && !options.transaction_id) {
          // Step 1
          return of(mockStep1Response);
        } else {
          // Step 3
          return of({
            result: { status: true, value: {} },
            detail: { serial: 'serial123', rollout_state: 'finished' },
          } as EnrollmentResponse);
        }
      });
      mockNavigatorCredentials.and.returnValue(
        Promise.resolve({
          id: 'credentialId',
          rawId: new ArrayBuffer(8),
          response: {
            clientDataJSON: new ArrayBuffer(8),
            attestationObject: new ArrayBuffer(8),
          },
          authenticatorAttachment: 'platform',
          getClientExtensionResults: () => ({ credProps: true }),
        }),
      );

      component.onClickEnroll(basicOptions)?.subscribe();
      tick();

      expect(mockTokenService.enrollToken).toHaveBeenCalledTimes(2);
      expect(mockNavigatorCredentials).toHaveBeenCalled();
      expect(mockMatDialog.open).toHaveBeenCalled();
      // Add more specific assertions for dialog closing and final response if needed
    }));

    // Add more tests for:
    // - navigator.credentials.create returning null or rejecting
    // - Step 3 (final enroll) failing and token deletion succeeding/failing
  });
});
