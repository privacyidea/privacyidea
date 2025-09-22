/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;
  let tokenService: jest.Mocked<TokenServiceInterface>;
  let contentService: jest.Mocked<ContentServiceInterface>;
  let mockDialogData: TokenEnrollmentLastStepDialogData;
  let afterClosedSubject: Subject<void>;

  const buildBaseData = (): TokenEnrollmentLastStepDialogData => ({
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
  });

  const detectChangesStable = async () => {
    fixture.detectChanges();
    await Promise.resolve();
    fixture.detectChanges();
  };

  beforeEach(async () => {
    mockDialogData = buildBaseData();

    afterClosedSubject = new Subject<void>();
    const dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(afterClosedSubject.asObservable())
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;

    const tokenServiceMock = {
      stopPolling: jest.fn()
    } as unknown as jest.Mocked<TokenServiceInterface>;

    const contentServiceMock = {
      tokenSelected: jest.fn(),
      containerSelected: jest.fn()
    } as unknown as jest.Mocked<ContentServiceInterface>;

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<TokenEnrollmentLastStepDialogComponent>
    >;
    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<TokenServiceInterface>;
    contentService = TestBed.inject(ContentService) as unknown as jest.Mocked<ContentServiceInterface>;
  });

  it("should create", async () => {
    await detectChangesStable();
    expect(component).toBeTruthy();
  });

  it("should stop polling when the dialog is closed", async () => {
    await detectChangesStable();
    afterClosedSubject.next();
    afterClosedSubject.complete();
    expect(tokenService.stopPolling).toHaveBeenCalled();
  });

  describe("UI display logic", () => {
    it("should show QR code for `hotp` token", async () => {
      await detectChangesStable();
      expect(component.showQRCode()).toBe(true);
    });

    it("should NOT show QR code for `sms` token", async () => {
      component.data.tokentype = { key: "sms", text: "SMS Token", info: "" };
      await detectChangesStable();
      expect(component.showQRCode()).toBe(false);
    });

    it("should show regenerate button for `hotp` token", async () => {
      await detectChangesStable();
      expect(component.showRegenerateButton()).toBe(true);
    });

    it.skip("should NOT show regenerate button for `sms` token", async () => {
      component.data.tokentype = { key: "sms", text: "SMS Token", info: "" };
      await detectChangesStable();
      expect(component.showRegenerateButton()).toBe(false);
    });

    it("should display OTP values for paper tokens", async () => {
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
      (component.data.response.detail as any)["otps"] = { "0": "123456", "1": "654321" };
      (component.data.response.detail as any).googleurl = undefined;

      await detectChangesStable();

      const otpElements = fixture.nativeElement.querySelectorAll(".otp-value");
      expect(otpElements.length).toBe(2);
      expect(otpElements[0].textContent).toContain("123456");
      expect(otpElements[1].textContent).toContain("654321");
    });

    it('should have regenerate button text "QR Code" for `hotp` token', async () => {
      await detectChangesStable();
      expect(component.regenerateButtonText()).toBe("QR Code");
    });

    it('should have regenerate button text "Values" for `paper` token', async () => {
      // This test assumes 'paper' is in REGENERATE_AS_VALUES_TOKEN_TYPES constant
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
      await detectChangesStable();
      expect(component.regenerateButtonText()).toBe("Values");
    });
  });

  describe("User Actions", () => {
    it("tokenSelected() should close the dialog and notify the content service", async () => {
      await detectChangesStable();
      const serial = "test-serial";
      component.tokenSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.tokenSelected).toHaveBeenCalledWith(serial);
    });

    it("containerSelected() should close the dialog and notify the content service", async () => {
      await detectChangesStable();
      const serial = "container-serial";
      component.containerSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.containerSelected).toHaveBeenCalledWith(serial);
    });

    it("regenerateQRCode() should trigger re-enrollment and close the dialog", async () => {
      await detectChangesStable();
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
      it("should open a print window with OTP values", async () => {
        // Prepare paper token state BEFORE the first CD pass
        component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
        (component.data.response.detail as any)["otps"] = { "0": "123456" };
        (component.data.response.detail as any).googleurl = undefined; // no QR for paper
        await detectChangesStable();

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

      it("should do nothing if otp-values element is not found", async () => {
        component.data.tokentype = { key: "paper", text: "Paper Token", info: "" };
        (component.data.response.detail as any)["otps"] = undefined;
        (component.data.response.detail as any).googleurl = undefined;
        await detectChangesStable();

        jest.spyOn(window, "open");
        component.printOtps();
        expect(window.open).not.toHaveBeenCalled();
      });
    });
  });
});