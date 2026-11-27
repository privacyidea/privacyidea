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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import {
  MockDialogService,
  MockNotificationService,
  MockSystemService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { of } from "rxjs";
import { TokenCompleteEnrollmentPushComponent } from "@components/token/token-enrollment/token-complete-enrollment-push/token-complete-enrollment-push.component";
import { TokenCompleteEnrollmentTwoStepComponent } from "@components/token/token-enrollment/token-complete-enrollment-two-step/token-complete-enrollment-two-step.component";
import { TokenEnrollmentDialogComponent } from "@components/token/token-enrollment/token-enrollment-dialog/token-enrollment-dialog.component";
import { TokenEnrollmentSuccessComponent } from "@components/token/token-enrollment/token-enrollment-success/token-enrollment-success.component";
import { TokenRolloverComponent } from "./token-rollover.component";
import { UserService } from "@services/user/user.service";
import { SystemService } from "@services/system/system.service";
import { axe } from "@testing/axe";

// Mock token enroll strategy
function installStrategy(component: TokenRolloverComponent, strategy: unknown): void {
  Object.defineProperty(component, "enrollSwitch", {
    value: () => ({ currentStrategy: () => strategy }),
    configurable: true
  });
}

describe("TokenRolloverComponent", () => {
  let component: TokenRolloverComponent;
  let fixture: ComponentFixture<TokenRolloverComponent>;
  let tokenService: MockTokenService;
  let notificationService: MockNotificationService;
  let dialogService: MockDialogService;
  let dialogRef: { close: jest.Mock };

  const mockToken = { type: "hotp", serial: "ABC123", tokentype: "hotp" };
  const mockData = { token: mockToken };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenRolloverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: UserService, useClass: MockUserService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenRolloverComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeDefined();
  });

  it("should include the token serial in the dialog title", () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    expect(component.title()).toBe("Rollover Token ABC123");
  });

  // enrollToken() reports the failure itself, so the component only has to stop quietly
  // instead of notifying a second time and leaving the rejection unhandled.
  it("should stop without a second notification when enrollment fails", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: {},
        mapper: { map: (x: unknown) => x }
      })
    });
    tokenService.enrollToken.mockReturnValue(
      new Promise((_resolve, reject) => reject({ error: { result: { error: { message: "boom" } } } }))
    );

    await expect(component.rolloverToken()).resolves.toBeUndefined();

    expect(notificationService.error).not.toHaveBeenCalled();
  });

  it("rolls the token over only once while the request runs, and disables Rollover meanwhile", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({ data: {}, mapper: { map: (x: unknown) => x } })
    });
    let answer!: (response: EnrollmentResponse) => void;
    tokenService.enrollToken.mockReturnValue(new Promise<EnrollmentResponse>((resolve) => (answer = resolve)));

    const first = component.rolloverToken();
    void component.rolloverToken();

    expect(tokenService.enrollToken).toHaveBeenCalledTimes(1);
    expect(component.dialogActions()[0].disabled).toBe(true);

    answer({ result: { status: true }, detail: { serial: "ABC123", rollout_state: "enrolled" } } as EnrollmentResponse);
    await first;
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should warn when the strategy cannot build the enrollment arguments", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, { buildEnrollmentArgs: jest.fn().mockReturnValue(null) });

    await component.rolloverToken();

    expect(notificationService.warning).toHaveBeenCalledWith(
      "Please fill in all required fields or correct invalid entries."
    );
    expect(tokenService.enrollToken).not.toHaveBeenCalled();
  });

  it("should call enrollToken and close dialog on successful rollover", async () => {
    const mockEnrollResp = {
      result: { status: true },
      detail: { rollout_state: "done", serial: "ABC123", verify: false }
    };

    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: {},
        mapper: { map: (x: unknown) => x }
      })
    });

    const reloadSpy = jest.spyOn(tokenService.tokenDetailResource, "reload");
    tokenService.enrollToken.mockReturnValue(of(mockEnrollResp as unknown as EnrollmentResponse));

    await component.rolloverToken();

    expect(tokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRef.close).toHaveBeenCalled();
    expect(dialogService.openDialog).toHaveBeenCalled();

    const successDialogRef = dialogService.openDialog.mock.results[0].value;
    successDialogRef.close();

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("runs the first step of the token type only once the rollover form has closed", async () => {
    component.token.set({ type: "push", serial: "PIPU0001" });
    const firstResponse = { result: { status: true }, detail: { serial: "PIPU0001", rollout_state: "clientwait" } };
    const firstStep = jest.fn().mockReturnValue({ kind: "push" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({ data: { type: "push" }, mapper: { map: (x: unknown) => x } }),
      firstStep
    });
    tokenService.enrollToken.mockReturnValue(of(firstResponse as unknown as EnrollmentResponse));

    await component.rolloverToken();

    expect(firstStep).toHaveBeenCalledWith(firstResponse, { type: "push" });
    expect(component.enrollmentFlow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
    expect(dialogRef.close.mock.invocationCallOrder[0]).toBeLessThan(
      dialogService.openDialog.mock.invocationCallOrder[0]
    );
    expect(component.enrollmentFlow.dialogData()?.rollover).toBe(true);
  });

  it("keeps a regenerated response in the enrollment data of the rollover", async () => {
    const mockEnrollResp = {
      result: { status: true },
      detail: { rollout_state: "done", serial: "ABC123", googleurl: { img: "initial-img", value: "initial-url" } }
    } as unknown as EnrollmentResponse;

    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: {},
        mapper: { map: (x: unknown) => x }
      })
    });
    tokenService.enrollToken.mockReturnValue(of(mockEnrollResp));

    await component.rolloverToken();

    const regenerated = {
      result: { status: true },
      detail: { rollout_state: "done", serial: "ABC123", googleurl: { img: "regenerated-img", value: "regen-url" } }
    } as unknown as EnrollmentResponse;
    component.enrollmentFlow.dialogData()?.onEnrollmentResponseChange?.(regenerated);

    expect(component.enrollmentFlow.dialogData()?.response).toBe(regenerated);
  });

  it("gives the dialogs the type of the enrollment request, not the selected enrollment type", async () => {
    component.token.set({ type: "totp", serial: "TOTP0001" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: { type: "totp", serial: "TOTP0001", rollover: true },
        mapper: { map: (x: unknown) => x }
      })
    });
    tokenService.enrollToken.mockReturnValue(
      of({
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "TOTP0001" }
      } as unknown as EnrollmentResponse)
    );
    // The selected enrollment type is shared and falls back to hotp when the route changes
    tokenService.selectedTokenType.set({ key: "hotp", name: "", text: "", info: "" });

    await component.rolloverToken();

    expect(component.enrollmentFlow.dialogData()?.tokenType).toBe("totp");
  });

  it("should show snackbar if no token is set", async () => {
    component.token.set(null);
    await component.rolloverToken();
    expect(notificationService.warning).toHaveBeenCalledWith("No token selected for rollover.");
  });

  it("should show snackbar if no strategy is available", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, undefined);
    await component.rolloverToken();
    expect(notificationService.warning).toHaveBeenCalledWith(
      "Rollover action is not available for the selected token type."
    );
  });

  it("runs the two-step completion and reloads the token details after each step", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: { type: "hotp", serial: "ABC123", rollover: true },
        mapper: { map: (x: unknown) => x }
      })
    });
    tokenService.enrollToken.mockReturnValue(
      of({
        result: { status: true },
        detail: { rollout_state: "clientwait", serial: "ABC123" }
      } as unknown as EnrollmentResponse)
    );
    const completed = {
      result: { status: true },
      detail: { rollout_state: "enrolled", serial: "ABC123" }
    } as unknown as EnrollmentResponse;
    const reloadSpy = jest.spyOn(tokenService.tokenDetailResource, "reload");

    await component.rolloverToken();
    expect(component.enrollmentFlow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);

    component.enrollmentFlow.finishStep(completed);

    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({ component: TokenEnrollmentDialogComponent })
    );
    expect(component.enrollmentFlow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(component.enrollmentFlow.dialogData()).toEqual(
      expect.objectContaining({ response: completed, rollover: true })
    );
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
