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
import { NO_ERRORS_SCHEMA } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { of } from "rxjs";
import { TokenVerifyEnrollmentComponent } from "./token-verify-enrollment.component";

describe("TokenVerifyEnrollmentComponent", () => {
  let component: TokenVerifyEnrollmentComponent;
  let fixture: ComponentFixture<TokenVerifyEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123", verify: { message: "Enter OTP" } }, type: "hotp" },
    enrollParameters: { data: {} }
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
    expect(mockTokenService.verifyToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).toHaveBeenCalled();
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

    it("offers no cancel action without the delete right", async () => {
      await setup({}, false);

      expect(actionValues()).toEqual(["verify"]);
    });

    it("offers the cancel action before the verify action", async () => {
      await setup({}, true);

      expect(actionValues()).toEqual(["cancelEnrollment", "verify"]);
    });

    it("never offers to cancel a rollover", async () => {
      await setup({ rollover: true }, true);

      expect(actionValues()).toEqual(["verify"]);
    });

    it("deletes the unverified token and reports the cancellation", async () => {
      await setup({}, true);

      component.onDialogAction("cancelEnrollment");

      expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
      expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });
  });
});
