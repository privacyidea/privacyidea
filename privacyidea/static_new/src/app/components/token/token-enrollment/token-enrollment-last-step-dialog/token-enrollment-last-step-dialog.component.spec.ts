import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { provideHttpClient } from "@angular/common/http";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  const dialogRefMock = {
    close: jest.fn(),
    afterClosed: jest.fn(() => of(null))
  } as unknown as jest.Mocked<
    MatDialogRef<TokenEnrollmentLastStepDialogComponent, string | null>
  >;

  /*export interface PiResponse<Value, Detail = undefined> {
  id: number;
  jsonrpc: string;
  detail: Detail;
  result?: {
    authentication?: 'CHALLENGE' | 'POLL' | 'PUSH';
    status: boolean;
    value?: Value;
    error?: {
      code: number;
      message: string;
    };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;
}
*/
  const dialogDataStub = {
    response: {
      id: 1,
      detail: {
        rollout_state: "enrolled",
        serial: "1234567890",
        threadid: 1,
        passkey_registration: null,
        u2fRegisterRequest: null,
        pushurl: {
          description: "Push URL",
          img: "push.png",
          value: "https://example.com/push",
          value_b32: "B32VALUE"
        },
        googleurl: {
          description: "Google URL",
          img: "google.png",
          value: "https://example.com/google",
          value_b32: "B32VALUE"
        },
        otpkey: {
          description: "OTP Key",
          img: "otp.png",
          value: "otpprotocol://example.com/otpkey",
          value_b32: "B32VALUE"
        },
        motpurl: {
          description: "MOTP URL",
          img: "motp.png",
          value: "motpprotocol://example.com/motpkey",
          value_b32: "B32VALUE"
        },
        tiqrenroll: {
          description: "Tiqr Enroll URL",
          img: "tiqr.png",
          value: "tiqr://example.com/enroll",
          value_b32: "B32VALUE"
        }
      }
    }
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: dialogDataStub }
      ],
      imports: [TokenEnrollmentLastStepDialogComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
