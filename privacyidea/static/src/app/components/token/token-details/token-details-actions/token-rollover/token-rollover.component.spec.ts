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

import { HttpErrorResponse, provideHttpClient } from "@angular/common/http";
import { By } from "@angular/platform-browser";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { EnrollmentPolicies, TokenService } from "@services/token/token.service";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import {
  MockDialogService,
  MockNotificationService,
  MockPiResponse,
  MockSystemService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { of, Subject, throwError } from "rxjs";
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

    const lastStepDialogRef = dialogService.openDialog.mock.results[0].value;
    lastStepDialogRef.close();

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should keep the regenerated response for a reopened last step dialog", async () => {
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
    component.enrolledDialogData()?.onEnrollmentResponseChange?.(regenerated);

    expect(component.enrollResponse()).toBe(regenerated);
    expect(component.enrolledDialogData()?.response).toBe(regenerated);

    dialogService.openDialog.mockClear();
    (component as unknown as { openLastStepDialog: (response: EnrollmentResponse | null) => void }).openLastStepDialog(
      component.enrolledDialogData()?.response ?? null
    );

    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ response: regenerated }) })
    );
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

    expect(component.enrolledDialogData()?.tokenType).toBe("totp");
  });

  it("should show a warning when opening the last step dialog without a response", () => {
    (component as unknown as { openLastStepDialog: (response: EnrollmentResponse | null) => void }).openLastStepDialog(
      null
    );

    expect(notificationService.warning).toHaveBeenCalledWith("No rollover response available.");
    expect(dialogService.openDialog).not.toHaveBeenCalled();
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

  describe("enrollment policies", () => {
    const policies: EnrollmentPolicies = {
      defaults: { hashlib: "sha512" },
      "2step": null,
      force_server_generate: false,
      sms_gateways: [],
      require_description: false
    };

    const createRollover = () => {
      const freshFixture = TestBed.createComponent(TokenRolloverComponent);
      freshFixture.detectChanges();
      return freshFixture;
    };

    it("requests the enrollment policies of the rolled over token", () => {
      tokenService.getEnrollmentPolicies.mockClear();
      tokenService.getEnrollmentPolicies.mockReturnValue(of(MockPiResponse.fromValue<EnrollmentPolicies>(policies)));
      const freshFixture = createRollover();

      expect(tokenService.getEnrollmentPolicies).toHaveBeenCalledWith({ type: "hotp", serial: "ABC123" });
      const typeSwitch = freshFixture.debugElement.query(By.directive(EnrollTokenTypeSwitchComponent))
        .componentInstance as EnrollTokenTypeSwitchComponent;
      expect(typeSwitch.enrollmentPolicies()).toEqual({ state: "loaded", policies });
    });

    it("blocks the rollover until the policies allow it", () => {
      const rolloverDisabled = (freshFixture: ComponentFixture<TokenRolloverComponent>) =>
        freshFixture.componentInstance.dialogActions()[0].disabled;

      tokenService.getEnrollmentPolicies.mockReturnValue(new Subject());
      expect(rolloverDisabled(createRollover())).toBe(true);

      const message = "There are policies with conflicting actions: ['a', 'b']";
      tokenService.getEnrollmentPolicies.mockReturnValue(
        throwError(
          () =>
            new HttpErrorResponse({ status: 403, error: { result: { status: false, error: { code: 303, message } } } })
        )
      );
      const failed = createRollover();
      expect(rolloverDisabled(failed)).toBe(true);
      expect(failed.nativeElement.textContent).toContain(message);

      tokenService.getEnrollmentPolicies.mockReturnValue(of(MockPiResponse.fromValue<EnrollmentPolicies>(policies)));
      expect(rolloverDisabled(createRollover())).toBe(false);
    });

    describe("description input", () => {
      const withRequirement = (require_description: boolean) =>
        tokenService.getEnrollmentPolicies.mockReturnValue(
          of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, require_description }))
        );
      const field = (f: ComponentFixture<TokenRolloverComponent>) => f.nativeElement.querySelector("textarea");

      it("shows no field when no description is required", () => {
        withRequirement(false);
        const f = createRollover();
        expect(field(f)).toBeNull();
        expect(f.componentInstance.dialogActions()[0].disabled).toBe(false);
      });

      it("shows a required field and blocks the rollover while the token has no description", () => {
        withRequirement(true);
        const f = createRollover();
        expect(field(f)).not.toBeNull();
        expect(field(f).closest("mat-form-field").textContent).toContain("Description");
        expect(f.componentInstance.dialogActions()[0].disabled).toBe(true);

        f.componentInstance.description.set("   ");
        f.detectChanges();
        expect(f.componentInstance.dialogActions()[0].disabled).toBe(true);

        f.componentInstance.description.set("my token");
        f.detectChanges();
        expect(f.componentInstance.dialogActions()[0].disabled).toBe(false);
      });

      it("sends the entered description with the rollover request", async () => {
        withRequirement(true);
        const f = createRollover();
        f.componentInstance.description.set("my token");
        const buildEnrollmentArgs = jest.fn().mockReturnValue(null);
        installStrategy(f.componentInstance, { buildEnrollmentArgs });

        await f.componentInstance.rolloverToken();

        expect(buildEnrollmentArgs).toHaveBeenCalledWith(
          expect.objectContaining({ description: "my token", rollover: true })
        );
      });

      it("does not roll over while the required description is empty", async () => {
        withRequirement(true);
        const f = createRollover();
        const buildEnrollmentArgs = jest.fn();
        installStrategy(f.componentInstance, { buildEnrollmentArgs });

        await f.componentInstance.rolloverToken();

        expect(buildEnrollmentArgs).not.toHaveBeenCalled();
      });
    });

    describe("with a token that has a description", () => {
      beforeEach(async () => {
        TestBed.resetTestingModule();
        await TestBed.configureTestingModule({
          imports: [TokenRolloverComponent],
          providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            { provide: TokenService, useClass: MockTokenService },
            { provide: NotificationService, useClass: MockNotificationService },
            { provide: DialogService, useClass: MockDialogService },
            { provide: MAT_DIALOG_DATA, useValue: { token: { ...mockToken, description: "laptop" } } },
            { provide: MatDialogRef, useValue: dialogRef },
            { provide: UserService, useClass: MockUserService },
            { provide: SystemService, useClass: MockSystemService }
          ]
        }).compileComponents();
        tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      });

      it("does not block the rollover when the token already has the required description", () => {
        tokenService.getEnrollmentPolicies.mockReturnValue(
          of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, require_description: true }))
        );

        const f = createRollover();
        expect(f.componentInstance.dialogActions()[0].disabled).toBe(false);
        expect(f.nativeElement.querySelector("textarea")).toBeNull();
      });

      it("sends the existing description with the rollover request", async () => {
        tokenService.getEnrollmentPolicies.mockReturnValue(
          of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, require_description: true }))
        );
        const f = createRollover();
        const buildEnrollmentArgs = jest.fn().mockReturnValue(null);
        installStrategy(f.componentInstance, { buildEnrollmentArgs });

        await f.componentInstance.rolloverToken();

        expect(buildEnrollmentArgs).toHaveBeenCalledWith(expect.objectContaining({ description: "laptop" }));
      });
    });
  });

  describe("handleCompleteEnrollment", () => {
    it("opens the complete-enrollment dialog when rollout_state is 'clientwait' and forwards the result to verify", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { rollout_state: "clientwait", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const completeResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const afterClosed = jest.fn().mockReturnValue(of(completeResponse));
      dialogService.openDialog.mockReturnValue({ afterClosed } as unknown as MatDialogRef<unknown>);

      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const verifySpy = jest.spyOn(component, "handleVerifyEnrollment").mockImplementation(() => undefined);

      component.handleCompleteEnrollment(enrollResponse);

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ response: enrollResponse }),
          configOverride: { autoFocus: "input", disableClose: true }
        })
      );
      expect(verifySpy).toHaveBeenCalledWith(completeResponse);
      expect(component.enrolledDialogData()?.showEnrollData).toBe(false);
    });

    it("skips the dialog and routes directly to verify when rollout_state is not 'clientwait'", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const verifySpy = jest.spyOn(component, "handleVerifyEnrollment").mockImplementation(() => undefined);

      component.handleCompleteEnrollment(enrollResponse);

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(verifySpy).toHaveBeenCalledWith(enrollResponse);
    });
  });

  describe("handleVerifyEnrollment", () => {
    it("opens the verify dialog when the response requires verification and finalizes with the closed result", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { verify: { message: "type the OTP" }, serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const verifiedResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const afterClosed = jest.fn().mockReturnValue(of(verifiedResponse));
      dialogService.openDialog.mockReturnValue({ afterClosed } as unknown as MatDialogRef<unknown>);

      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const finalizeSpy = jest
        .spyOn(component as unknown as { _handleEnrollmentResponse: () => void }, "_handleEnrollmentResponse")
        .mockImplementation(() => undefined);

      component.handleVerifyEnrollment(enrollResponse);

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ response: enrollResponse }),
          configOverride: { autoFocus: "input", disableClose: true }
        })
      );
      expect(finalizeSpy).toHaveBeenCalledWith(verifiedResponse);
      expect(component.enrollResponse()).toEqual(verifiedResponse);
    });

    it("skips the verify dialog when no verification is required", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const finalizeSpy = jest
        .spyOn(component as unknown as { _handleEnrollmentResponse: () => void }, "_handleEnrollmentResponse")
        .mockImplementation(() => undefined);

      component.handleVerifyEnrollment(enrollResponse);

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(finalizeSpy).toHaveBeenCalledWith(enrollResponse);
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
