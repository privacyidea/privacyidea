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

import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";

import { of } from "rxjs";
import { TokenCompleteEnrollmentComponent } from "./token-complete-enrollment.component";

describe("TokenCompleteEnrollmentComponent", () => {
  let component: TokenCompleteEnrollmentComponent;
  let fixture: ComponentFixture<TokenCompleteEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123" }, type: "hotp" },
    enrollParameters: { data: { type: "hotp", twoStepInit: true } },
    onEnrollmentResponseChange: jest.fn()
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
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

  it("should disable enroll action if input is invalid", () => {
    component.clientPart.set("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("should enable enroll action if input is valid", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should call enrollToken and close dialog on successful enroll", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(
      of({
        type: "hotp",
        detail: { type: "hotp", serial: "X", rollout_state: "enrolled" },
        result: { status: true }
      } as EnrollmentResponse)
    );
    component.clientPart.set("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  it("should not close dialog if rollout_state is client_wait", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(
      of({
        type: "hotp",
        detail: { type: "hotp", serial: "X", rollout_state: "client_wait" },
        result: { status: true }
      } as EnrollmentResponse)
    );
    component.clientPart.set("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it("should remove twoStepInit from enrollParameters.data when enrolling", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    jest.spyOn(component["tokenService"], "enrollToken").mockImplementation((params) => {
      expect(params.data.type).toEqual("hotp");
      expect(params.data["twoStepInit"]).toBeUndefined();
      return of({
        result: { status: true },
        detail: { rollout_state: "enrolled", type: "hotp", serial: "123" },
        type: "hotp"
      });
    });
    component.onDialogAction("enroll");
  });

  describe("cancelling the enrollment", () => {
    let authService: MockAuthService;

    const setup = async (data: Record<string, unknown> = {}, canDelete = false) => {
      TestBed.resetTestingModule();
      dialogRefSpy = { close: jest.fn() };
      await TestBed.configureTestingModule({
        imports: [TokenCompleteEnrollmentComponent],
        providers: [
          { provide: TokenService, useClass: MockTokenService },
          { provide: ContentService, useClass: MockContentService },
          { provide: AuthService, useClass: MockAuthService },
          { provide: MatDialogRef, useValue: dialogRefSpy },
          { provide: MAT_DIALOG_DATA, useValue: { ...dialogData, ...data } }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();
      fixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
      component = fixture.componentInstance;
      mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.actionAllowed.mockImplementation((action: string) => canDelete && action === "delete");
      fixture.detectChanges();
    };

    const actionValues = () => component.dialogActions().map((action) => action.value);

    it("offers no cancel action without the delete right", async () => {
      await setup({}, false);

      expect(actionValues()).toEqual(["enroll"]);
      expect(component["showCloseButton"]()).toBe(true);
    });

    it("offers the cancel action and drops the close button for two step enrollments", async () => {
      await setup({ response: { detail: { serial: "123", "2step_output": 1 }, type: "hotp" } }, true);

      expect(actionValues()).toEqual(["cancelEnrollment", "enroll"]);
      expect(component["showCloseButton"]()).toBe(false);
    });

    it("keeps the close button for clientwait enrollments without a client part", async () => {
      await setup({}, true);

      expect(actionValues()).toEqual(["cancelEnrollment", "enroll"]);
      expect(component["showCloseButton"]()).toBe(true);
    });

    it("never offers to cancel a rollover", async () => {
      await setup({ rollover: true }, true);

      expect(actionValues()).toEqual(["enroll"]);
      expect(component["showCloseButton"]()).toBe(true);
    });

    it("deletes the incomplete token and reports the cancellation", async () => {
      await setup({}, true);

      component.onDialogAction("cancelEnrollment");

      expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
      expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });
  });
});
