import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { ReactiveFormsModule } from '@angular/forms';
import { TokenEnrollmentFirstStepDialogComponent } from './token-enrollment-first-step-dialog.component';
import { provideHttpClient } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

describe('TokenEnrollmentFirstStepDialogComponent', () => {
  let component: TokenEnrollmentFirstStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentFirstStepDialogComponent>;
  const dialogRefMock = {
    close: jest.fn(),
  } as unknown as jest.Mocked<
    MatDialogRef<TokenEnrollmentFirstStepDialogComponent, string | null>
  >;

  const dialogDataStub = {
    enrollmentResponse: {
      detail: {
        rollout_state: 'enrolled',
        serial: '1234567890',
        threadid: 1,
        passkey_registration: null,
        u2fRegisterRequest: null,
        pushurl: {
          description: 'Push URL',
          img: 'push.png',
          value: 'https://example.com/push',
          value_b32: 'B32VALUE',
        },
        googleurl: {
          description: 'Google URL',
          img: 'google.png',
          value: 'https://example.com/google',
          value_b32: 'B32VALUE',
        },
        otpkey: {
          description: 'OTP Key',
          img: 'otp.png',
          value: 'otpprotocol://example.com/otpkey',
          value_b32: 'B32VALUE',
        },
        motpurl: {
          description: 'MOTP URL',
          img: 'motp.png',
          value: 'motpprotocol://example.com/motpkey',
          value_b32: 'B32VALUE',
        },
        tiqrenroll: {
          description: 'Tiqr Enroll URL',
          img: 'tiqr.png',
          value: 'tiqr://example.com/enroll',
          value_b32: 'B32VALUE',
        },
      },
    },
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: dialogDataStub },
      ],
      imports: [
        MatFormFieldModule,
        MatAutocompleteModule,
        ReactiveFormsModule,
        TokenEnrollmentFirstStepDialogComponent,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentFirstStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
