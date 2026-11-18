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

import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { NO_ERRORS_SCHEMA } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { By } from "@angular/platform-browser";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { environment } from "@env/environment";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { of } from "rxjs";
import { TokenVerifyEnrollmentComponent } from "./token-verify-enrollment.component";
import { axe } from "@testing/axe";

describe("TokenVerifyEnrollmentComponent", () => {
  let component: TokenVerifyEnrollmentComponent;
  let fixture: ComponentFixture<TokenVerifyEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123", verify: { message: "Enter OTP" } }, type: "hotp" },
    enrollParameters: { data: {} },
    onEnrollmentResponseChange: jest.fn()
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenVerifyEnrollmentComponent],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("shows the enrollment data for the enrolled token type", async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenVerifyEnrollmentComponent],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            tokenType: "hotp",
            response: {
              result: { status: true },
              detail: {
                serial: "PIEM0001",
                rollout_state: "verify",
                verify: { message: "Enter OTP" },
                googleurl: { description: "", img: "data:image/png;base64,QR", value: "otpauth://hotp/PIEM0001" },
                otpkey: { description: "", img: "", value: "seed://3132", value_b32: "GEZA" }
              }
            },
            enrollParameters: { data: { type: "email" } },
            onEnrollmentResponseChange: jest.fn()
          }
        }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    const emailFixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
    emailFixture.detectChanges();

    const element: HTMLElement = emailFixture.nativeElement;
    expect(element.querySelector("img.enrollment-data__qr")).toBeNull();
    expect(element.querySelector("app-otp-key")).toBeNull();
  });

  it("should report a regenerated QR code to the opener of the dialog", () => {
    const regenerated = {
      type: "hotp",
      detail: { type: "hotp", serial: "123", googleurl: { img: "regenerated-img", value: "regenerated-url" } },
      result: { status: true }
    } as EnrollmentResponse;
    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regenerated);

    expect(dialogData.onEnrollmentResponseChange).toHaveBeenCalledWith(regenerated);
  });

  it("should render the verification message outside the input so it is not capped to its width", () => {
    const message = fixture.debugElement
      .queryAll(By.css("div"))
      .find((element) => element.nativeElement.textContent.trim() === "Enter OTP");

    expect(message).toBeTruthy();
    expect(fixture.debugElement.query(By.css("mat-hint"))).toBeNull();
    expect(message!.nativeElement.closest("mat-form-field")).toBeNull();
  });

  it("should disable verify action if input is invalid", () => {
    component.verifyOTP_value.set("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("should enable verify action if input is valid", () => {
    component.verifyOTP_value.set("123456");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should call verifyToken and close dialog on successful verify", () => {
    component.verifyOTP_value.set("123456");
    component.onDialogAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalledWith("123", "123456");
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  it("does not send a verify request without the serial of the enrolled token", () => {
    (component as unknown as { responseDetails: undefined }).responseDetails = undefined;
    mockTokenService.verifyToken.mockClear();
    component.verifyOTP_value.set("123456");
    component.onDialogAction("verify");
    expect(mockTokenService.verifyToken).not.toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it("should not close dialog if rollout_state is not enrolled", () => {
    mockTokenService.verifyToken = jest.fn().mockReturnValue(
      of({
        result: { status: true },
        detail: { rollout_state: "client_wait", serial: "123", type: "hotp" },
        type: "hotp"
      })
    );
    component.verifyOTP_value.set("123456");
    component.onDialogAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it("should close dialog on switch route", () => {
    component.onSwitchRoute();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  describe("cancelling the enrollment", () => {
    const setup = async (data: Record<string, unknown> = {}, canDelete = false) => {
      TestBed.resetTestingModule();
      dialogRefSpy = { close: jest.fn() };
      await TestBed.configureTestingModule({
        imports: [TokenVerifyEnrollmentComponent],
        providers: [
          provideHttpClient(),
          { provide: TokenService, useClass: MockTokenService },
          { provide: ContentService, useClass: MockContentService },
          { provide: AuthService, useClass: MockAuthService },
          { provide: MatDialogRef, useValue: dialogRefSpy },
          { provide: MAT_DIALOG_DATA, useValue: { ...dialogData, ...data } }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();
      fixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
      component = fixture.componentInstance;
      mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.actionAllowed.mockImplementation((action: string) => canDelete && action === "delete");
      fixture.detectChanges();
    };

    const actionValues = () => component.dialogActions().map((action) => action.value);

    const buttonLabels = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button") as NodeListOf<HTMLElement>).map(
        (button) => button.textContent?.trim() ?? ""
      );

    it("offers close instead of cancel without the delete right", async () => {
      await setup({}, false);

      expect(actionValues()).toEqual(["verify"]);
      expect(buttonLabels()).toEqual(["Close", "Verify"]);
    });

    it("replaces the close button with cancel before the verify action", async () => {
      await setup({}, true);

      expect(actionValues()).toEqual(["cancelEnrollment", "verify"]);
      expect(buttonLabels()).toEqual(["Cancel", "Verify"]);
    });

    it("never offers to cancel a rollover", async () => {
      await setup({ rollover: true }, true);

      expect(actionValues()).toEqual(["verify"]);
      expect(buttonLabels()).toEqual(["Close", "Verify"]);
    });

    it("deletes the unverified token and reports the cancellation", async () => {
      await setup({}, true);

      component.onDialogAction("cancelEnrollment");

      expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
      expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });
  });

  describe("context", () => {
    const setupContext = async (role: "admin" | "user", wizard = false) => {
      TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [TokenVerifyEnrollmentComponent],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TokenService, useClass: MockTokenService },
          { provide: ContentService, useClass: MockContentService },
          { provide: AuthService, useClass: MockAuthService },
          { provide: MatDialogRef, useValue: dialogRefSpy },
          {
            provide: MAT_DIALOG_DATA,
            useValue: { ...dialogData, wizard, enrollParameters: { data: { user: "alice", realm: "realm1" } } }
          }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...authService.authData(), role } as AuthData);
      fixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
      fixture.detectChanges();
    };
    const cardLabels = () =>
      Array.from(fixture.nativeElement.querySelectorAll(".enrolled__card-label") as NodeListOf<HTMLElement>).map(
        (label) => label.textContent?.trim()
      );

    it("shows the user and the realm to an admin", async () => {
      await setupContext("admin");
      expect(cardLabels()).toEqual(["Token", "User", "Realm"]);
    });

    it("leaves out the user and the realm in self-service", async () => {
      await setupContext("user");
      expect(cardLabels()).toEqual(["Token"]);
    });

    it("frames the step with the summary and the post customization in the wizard", async () => {
      await setupContext("user", true);
      const httpMock = TestBed.inject(HttpTestingController);
      const customizationUrl = (position: string) =>
        environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;
      httpMock.expectOne(customizationUrl("top")).flush("<p>Top {{ serial }}</p>");
      httpMock.expectOne(customizationUrl("bottom")).flush("<p>Bottom</p>");
      await fixture.whenStable();
      fixture.detectChanges();

      const text = fixture.nativeElement.textContent as string;
      expect(text).toContain("The token was enrolled.");
      expect(text).toContain("Top 123");
      expect(text).toContain("Bottom");
      expect(cardLabels()).toEqual([]);
      expect(text).toContain("Close");
      httpMock.verify();
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
