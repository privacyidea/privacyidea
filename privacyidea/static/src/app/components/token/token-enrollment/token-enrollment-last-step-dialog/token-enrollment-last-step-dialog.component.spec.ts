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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TokenEnrollmentDialogData, TokenService } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { axe } from "@testing/axe";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  const createDialogData = (): TokenEnrollmentDialogData => ({
    response: {
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
    },
    tokenType: "totp",
    userRealm: "test-realm",
    onlyAddToRealm: false,
    enrollParameters: {
      data: {} as unknown as TokenEnrollmentData,
      mapper: {} as unknown as BaseApiPayloadMapper
    },
    onEnrollmentResponseChange: jest.fn()
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

  const setup = async (dialogData: TokenEnrollmentDialogData): Promise<void> => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: dialogData },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await setup(createDialogData());
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render title for normal enrollment", () => {
    expect(component["rollover"]).toBe(false);
    expect(component.title()).toBe("Token Successfully Enrolled");
  });

  it("should close on a route switch while nothing blocks it", () => {
    component.onSwitchRoute();

    expect(component["dialogRef"].close).toHaveBeenCalled();
  });

  it("should keep the dialog open on a route switch while closing is blocked", () => {
    component["onCloseBlockedReasonChange"]("Download the PKCS#12 file.");

    component.onSwitchRoute();

    expect(component["dialogRef"].close).not.toHaveBeenCalled();
  });

  it("should render the enrollment data when showEnrollData is not set", () => {
    expect(fixture.nativeElement.querySelector("app-token-enrollment-data")).toBeTruthy();
  });

  it("should not render the QR code when showEnrollData is false", async () => {
    const pushDialogData: TokenEnrollmentDialogData = {
      ...createDialogData(),
      showEnrollData: false,
      tokenType: "push",
      response: {
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
      }
    };
    await setup(pushDialogData);

    expect(fixture.nativeElement.querySelector("app-token-enrollment-data")).toBeNull();
    expect(fixture.nativeElement.querySelector('img[alt="QR Code"]')).toBeNull();
    expect(fixture.nativeElement.querySelector("app-token-enrolled-text")).toBeTruthy();
    expect(component.title()).toBe("Token Successfully Enrolled");
    expect(
      Array.from(fixture.nativeElement.querySelectorAll("button")).some((button) =>
        (button as HTMLButtonElement).textContent?.includes("Close")
      )
    ).toBe(true);
  });

  it("should report a regenerated QR code to the opener of the dialog", () => {
    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regeneratedResponse);

    expect(component.data.onEnrollmentResponseChange).toHaveBeenCalledWith(regeneratedResponse);
  });

  it("should render title for rollover", async () => {
    await setup({ ...createDialogData(), rollover: true });

    expect(component["rollover"]).toBe(true);
    expect(component.title()).toBe("Token Successfully Rolled Over");
  });

  const footerButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));
  const footerButton = (label: string) =>
    footerButtons().find((button) => button.textContent?.trim() === label) as HTMLButtonElement | undefined;

  it("keeps the close button enabled while the enrollment data still has to be saved", () => {
    component["onCloseBlockedReasonChange"]("Download the PKCS#12 file.");
    fixture.detectChanges();

    expect(footerButton("Close")?.disabled).toBe(false);
  });

  it("offers only the close button", () => {
    expect(footerButtons().map((button) => button.textContent?.trim())).toEqual(["Close"]);
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
