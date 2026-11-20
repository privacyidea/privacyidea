/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TokenEnrollmentDialogData, TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { EnrollmentDialogHarness } from "@testing/enrollment-dialog-harness";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let harness: EnrollmentDialogHarness;
  let component: TokenEnrollmentLastStepDialogComponent;

  const createResponse = (): EnrollmentResponse => ({
    type: "totp",
    detail: {
      type: "totp",
      serial: "1234567890",
      googleurl: {
        description: "Google Authenticator URL",
        img: "",
        value: "otpauth://totp/Example:user?secret=ABCDEF1234567890&issuer=Example"
      }
    },
    result: { status: true }
  });
  const createDialogData = (): Partial<TokenEnrollmentDialogData> => ({
    tokenType: "totp",
    userRealm: "test-realm",
    onlyAddToRealm: false,
    enrollParameters: {
      data: {} as unknown as TokenEnrollmentData,
      mapper: {} as unknown as BaseApiPayloadMapper
    }
  });

  const regeneratedResponse: EnrollmentResponse = {
    type: "totp",
    detail: {
      type: "totp",
      serial: "1234567890",
      googleurl: {
        description: "Google Authenticator URL",
        img: "regenerated-img",
        value: "otpauth://totp/Example:user?secret=REGENERATED&issuer=Example"
      }
    },
    result: { status: true }
  };

  const setup = async (
    response: EnrollmentResponse = createResponse(),
    data: Partial<TokenEnrollmentDialogData> = createDialogData()
  ): Promise<void> => {
    TestBed.resetTestingModule();
    harness = new EnrollmentDialogHarness();
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ...harness.providers,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();
    harness.open(response, data);
    component = harness.step<TokenEnrollmentLastStepDialogComponent>();
  };

  beforeEach(async () => {
    await setup();
  });

  it("is the step shown once the enrollment is done", () => {
    expect(component).toBeInstanceOf(TokenEnrollmentLastStepDialogComponent);
    expect(component.headerState).toBe("done");
  });

  it("should render title for normal enrollment", () => {
    expect(component["rollover"]).toBe(false);
    expect(component.title()).toBe("Token Successfully Enrolled");
    expect(harness.element.querySelector("h3")?.textContent).toContain("Token Successfully Enrolled");
  });

  it("shows the container the token was added to", async () => {
    const response = createResponse();
    response.detail = { ...response.detail, container_serial: "SMPH0001" };
    await setup(response);

    expect(harness.element.textContent).toContain("SMPH0001");
  });

  it("should render the enrollment data when showEnrollData is not set", () => {
    expect(harness.element.querySelector("app-token-enrollment-data")).toBeTruthy();
  });

  it("should not render the QR code when showEnrollData is false", async () => {
    await setup(
      {
        type: "push",
        result: { status: true },
        detail: {
          type: "push",
          serial: "PIPU0001",
          pushurl: {
            description: "Push URL",
            img: "data:image/png;base64,qr",
            value: "otpauth://pipush/PIPU0001"
          }
        }
      },
      { ...createDialogData(), showEnrollData: false, tokenType: "push" }
    );

    expect(harness.element.querySelector("app-token-enrollment-data")).toBeNull();
    expect(harness.element.querySelector('img[alt="QR Code"]')).toBeNull();
    expect(harness.element.querySelector("app-token-enrolled-text")).toBeTruthy();
    expect(component.title()).toBe("Token Successfully Enrolled");
    expect(harness.footerButton("Close")).toBeTruthy();
  });

  it("should report a regenerated QR code to the flow", () => {
    const enrollmentData = harness.fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regeneratedResponse);

    expect(harness.flow.dialogData()?.response).toBe(regeneratedResponse);
  });

  it("should render title for rollover", async () => {
    await setup(createResponse(), { ...createDialogData(), rollover: true });

    expect(component["rollover"]).toBe(true);
    expect(component.title()).toBe("Token Successfully Rolled Over");
  });

  it("keeps the close button enabled while the passphrase is not saved", () => {
    component.onCloseConfirmationChange("The passphrase is shown only once.");
    harness.fixture.detectChanges();

    expect(harness.footerButton("Close")?.disabled).toBe(false);
  });

  it("offers only the close button", () => {
    expect(harness.footerButtons().map((button) => button.textContent?.trim())).toEqual(["Close"]);
  });

  describe("closing", () => {
    const passphraseWarning = "The passphrase is shown only once.";
    let dialogService: MockDialogService;

    beforeEach(() => {
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      dialogService.openDialog.mockClear();
    });

    const answerConfirmation = (confirmed: boolean) => {
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(confirmed));
      dialogService.openDialog.mockReturnValue(confirmationRef);
    };

    it("closes right away when nothing would be lost", () => {
      harness.footerButton("Close")?.click();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).toHaveBeenCalled();
    });

    it("stays open when closing without the passphrase is not confirmed", () => {
      component.onCloseConfirmationChange(passphraseWarning);
      answerConfirmation(false);

      harness.footerButton("Close")?.click();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ message: passphraseWarning }) })
      );
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });

    it("closes once closing without the passphrase is confirmed", () => {
      component.onCloseConfirmationChange(passphraseWarning);
      answerConfirmation(true);

      harness.footerButton("Close")?.click();

      expect(harness.dialogRef.close).toHaveBeenCalled();
    });

    it("lets a link in the header ask the same way before it leaves", () => {
      component.onCloseConfirmationChange(passphraseWarning);
      answerConfirmation(false);
      const contentService = TestBed.inject(ContentService) as unknown as MockContentService;

      (harness.element.querySelector(".enrolled__card-value") as HTMLElement).click();

      expect(dialogService.openDialog).toHaveBeenCalled();
      expect(contentService.tokenSelected).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).not.toHaveBeenCalled();

      answerConfirmation(true);
      (harness.element.querySelector(".enrolled__card-value") as HTMLElement).click();

      expect(contentService.tokenSelected).toHaveBeenCalledWith("1234567890");
      expect(harness.dialogRef.close).toHaveBeenCalled();
    });

    it("ignores keys other than Escape", () => {
      component.onCloseConfirmationChange(passphraseWarning);

      harness.dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Enter" }));

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });

    it("lets Escape and a backdrop click ask the same way", () => {
      expect(harness.dialogRef.disableClose).toBe(true);
      component.onCloseConfirmationChange(passphraseWarning);
      answerConfirmation(false);

      harness.dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      harness.dialogRef.fireBackdropClick();

      expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });
  });

  it("passes the axe accessibility checks", async () => {
    harness.fixture.detectChanges();

    expect(await axe(harness.element)).toHaveNoViolations();
  });
});
