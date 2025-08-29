import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialogRef, MAT_DIALOG_DATA } from "@angular/material/dialog";
import { Subject } from "rxjs";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";
import {
  TokenEnrollmentLastStepDialogComponent,
  TokenEnrollmentLastStepDialogData
} from "./token-enrollment-last-step-dialog.component";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;
  let tokenService: jest.Mocked<TokenServiceInterface>;
  let contentService: jest.Mocked<ContentServiceInterface>;
  let mockDialogData: TokenEnrollmentLastStepDialogData;
  let afterClosedSubject: Subject<void>;

  beforeEach(async () => {
    // Reset mock data for each test to prevent state leakage between tests
    mockDialogData = {
      tokentype: { key: "hotp", text: "HOTP Token", info: "" },
      response: {
        detail: {
          serial: "HOTP123456",
          googleurl: {
            img: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60eADwAAAABJRU5ErkJggg==",
            value: "otpauth://hotp/test",
            description: "test url"
          }
        }
      },
      serial: signal<string | null>(null),
      enrollToken: jest.fn(),
      user: { username: "testuser" } as UserData,
      userRealm: "testrealm",
      onlyAddToRealm: false
    };

    afterClosedSubject = new Subject<void>();
    const dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(afterClosedSubject.asObservable())
    };

    const tokenServiceMock = {
      stopPolling: jest.fn()
    };

    const contentServiceMock = {
      tokenSelected: jest.fn(),
      containerSelected: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;
    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<TokenServiceInterface>;
    contentService = TestBed.inject(ContentService) as unknown as jest.Mocked<ContentServiceInterface>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should stop polling when the dialog is closed", () => {
    afterClosedSubject.next();
    afterClosedSubject.complete();
    expect(tokenService.stopPolling).toHaveBeenCalled();
  });

  describe("UI display logic", () => {
    it("should show QR code for `hotp` token", () => {
      expect(component.showQRCode()).toBe(true);
    });

    it("should NOT show QR code for `sms` token", () => {
      component.data.tokentype = { key: "sms", text: "SMS Token", info: "" };
      fixture.detectChanges();
      expect(component.showQRCode()).toBe(false);
    });

    it("should show regenerate button for `hotp` token", () => {
      expect(component.showRegenerateButton()).toBe(true);
    });

    it.skip("should NOT show regenerate button for `sms` token", () => {
      component.data.tokentype = { key: "sms", text: "SMS Token", info: "" };
      fixture.detectChanges();
      expect(component.showRegenerateButton()).toBe(false);
    });

    it("should display OTP values for paper tokens", () => {
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
      component.data.response.detail["otps"] = { "0": "123456", "1": "654321" };
      fixture.detectChanges();

      const otpElements = fixture.nativeElement.querySelectorAll(".otp-value");
      expect(otpElements.length).toBe(2);
      expect(otpElements[0].textContent).toContain("123456");
      expect(otpElements[1].textContent).toContain("654321");
    });

    it('should have regenerate button text "QR Code" for `hotp` token', () => {
      expect(component.regenerateButtonText()).toBe("QR Code");
    });

    it('should have regenerate button text "Values" for `paper` token', () => {
      // This test assumes 'paper' is in REGENERATE_AS_VALUES_TOKEN_TYPES constant
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
      fixture.detectChanges();
      expect(component.regenerateButtonText()).toBe("Values");
    });
  });

  describe("User Actions", () => {
    it("tokenSelected() should close the dialog and notify the content service", () => {
      const serial = "test-serial";
      component.tokenSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.tokenSelected).toHaveBeenCalledWith(serial);
    });

    it("containerSelected() should close the dialog and notify the content service", () => {
      const serial = "container-serial";
      component.containerSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.containerSelected).toHaveBeenCalledWith(serial);
    });

    it("regenerateQRCode() should trigger re-enrollment and close the dialog", () => {
      const serial = component.data.response.detail.serial;
      const enrollSpy = component.data.enrollToken;
      const serialSignalSpy = jest.spyOn(component.data.serial, "set");

      component.regenerateQRCode();

      expect(serialSignalSpy).toHaveBeenCalledWith(serial);
      expect(enrollSpy).toHaveBeenCalled();
      expect(serialSignalSpy).toHaveBeenCalledWith(null);
      expect(dialogRef.close).toHaveBeenCalled();
    });

    describe("printOtps()", () => {
      it("should open a print window with OTP values", () => {
        // Setup for paper token
        component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
        component.data.response.detail["otps"] = { "0": "123456" };
        component.data.response.detail.googleurl = undefined; // Paper tokens don't have QR codes
        fixture.detectChanges();

        // Mock window.open
        const mockPrintWindow = {
          document: {
            open: jest.fn(),
            write: jest.fn(),
            close: jest.fn()
          },
          focus: jest.fn(),
          print: jest.fn(),
          close: jest.fn()
        };
        jest.spyOn(window, "open").mockReturnValue(mockPrintWindow as any);

        component.printOtps();

        expect(window.open).toHaveBeenCalledWith("", "_blank", "width=800,height=600");
        expect(mockPrintWindow.document.open).toHaveBeenCalled();
        expect(mockPrintWindow.document.write).toHaveBeenCalled();
        expect(mockPrintWindow.document.close).toHaveBeenCalled();
        expect(mockPrintWindow.focus).toHaveBeenCalled();
        expect(mockPrintWindow.print).toHaveBeenCalled();
        expect(mockPrintWindow.close).toHaveBeenCalled();
      });

      it("should do nothing if otp-values element is not found", () => {
        // Ensure no OTP data exists, so the element won't be in the DOM
        component.data.response.detail["otps"] = undefined;
        fixture.detectChanges();

        jest.spyOn(window, "open");
        component.printOtps();
        expect(window.open).not.toHaveBeenCalled();
      });
    });
  });
});