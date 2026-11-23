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
import { signal, Type } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { HttpErrorResponse, provideHttpClient } from "@angular/common/http";
import { PiResponse } from "@app/app.component";
import { loadedEnrollmentPolicies } from "./enrollment-policy-values";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { environment } from "@env/environment";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { LocalService } from "@services/local/local.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { SystemService } from "@services/system/system.service";
import {
  EnrollmentPolicies,
  EnrollmentPolicyState,
  EnrollmentPolicyTarget,
  EnrollTokenArguments,
  TokenService,
  TokenType
} from "@services/token/token.service";
import { UserData } from "@services/user/user.service";
import { UserService } from "@services/user/user.service";
import { VersioningService } from "@services/version/version.service";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockPiResponse,
  MockNotificationService,
  MockRealmService,
  MockSystemService,
  MockTokenService,
  MockUserService,
  MockVersioningService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { of, Subject, throwError } from "rxjs";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { EnrollHotpComponent } from "./enroll-hotp/enroll-hotp.component";
import { TokenEnrollmentComponent } from "./token-enrollment.component";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "./token-enrollment.constants";
import { TokenEnrollmentSelfServiceComponent } from "./token-enrollment.self-service.component";
import { TokenEnrollmentWizardComponent } from "./token-enrollment.wizard.component";
import { TokenEnrollmentTypeSelectorComponent } from "./token-enrollment-type-selector/token-enrollment-type-selector.component";
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { UserAssignmentComponent } from "@components/token/user-assignment/user-assignment.component";
import { HotpApiPayloadMapper } from "@app/mappers/token-api-payload/hotp-token-api-payload.mapper";

interface TokenEnrollmentComponentInternals {
  _handleEnrollmentResponse: (response: EnrollmentResponse) => void;
  openLastStepDialog: (response: EnrollmentResponse | null) => void;
  handleCompleteEnrollment: (response: EnrollmentResponse | null) => void;
  handleVerifyEnrollment: (response: EnrollmentResponse | null) => void;
}

// Mock token enroll strategy
function installStrategy(component: TokenEnrollmentComponent, strategy: unknown): void {
  const withDefaults = strategy
    ? { enrollmentBlockedReason: signal(null), fieldsInvalid: signal(false), ...(strategy as object) }
    : strategy;
  Object.defineProperty(component, "enrollSwitch", {
    value: () => ({ currentStrategy: () => withDefaults }),
    configurable: true
  });
}

describe("TokenEnrollmentComponent", () => {
  let fixture: ComponentFixture<TokenEnrollmentComponent>;
  let component: TokenEnrollmentComponent;
  let tokenService: MockTokenService;
  let userService: MockUserService;
  let notificationServiceMock: MockNotificationService;
  let dialogServiceMock: MockDialogService;
  let authServiceMock: MockAuthService;
  let pendingChangesService: MockPendingChangesService;
  let httpTestingController: HttpTestingController;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });

    class IO {
      observe = jest.fn();
      disconnect = jest.fn();
    }

    (globalThis as unknown as { IntersectionObserver: typeof IO }).IntersectionObserver = IO;
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        MockLocalService,
        MockNotificationService,
        { provide: LocalService, useExisting: MockLocalService },
        { provide: NotificationService, useExisting: MockNotificationService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: UserService, useClass: MockUserService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    httpTestingController = TestBed.inject(HttpTestingController);

    fixture.detectChanges();
  });

  afterEach(() => {
    httpTestingController.verify();
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("creates self service", () => {
    const selfFixture = TestBed.createComponent(TokenEnrollmentSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
  });

  it("self service warns when opening the last step dialog without a response", () => {
    const selfFixture = TestBed.createComponent(TokenEnrollmentSelfServiceComponent);
    const selfComponent = selfFixture.componentInstance;
    (selfComponent as unknown as { openLastStepDialog: (response: null) => void }).openLastStepDialog(null);
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("No enrollment response available.");
  });

  it("formatDateTimeOffset builds the expected ISO-ish string", () => {
    const d = new Date("2025-09-10T00:00:00Z");
    const result = component.formatDateTimeOffset(d, "08:05", "+02:00");
    expect(result).toBe("2025-09-10T08:05+0200");
  });

  it("no default values for validity period", () => {
    expect(component.selectedStartDate()).toBeNull();
    expect(component.selectedEndDate()).toBeNull();
  });

  it("repeatPinForm is invalid when PINs differ and valid when equal", () => {
    component.setPin.set("1234");
    component.repeatPin.set("9999");
    expect(component.repeatPinForm().valid()).toBe(false);
    expect(
      component
        .repeatPinForm()
        .errors()
        .some((e) => e.kind === "pinMismatch")
    ).toBe(true);

    component.repeatPin.set("1234");
    expect(component.repeatPinForm().valid()).toBe(true);
  });

  it("isUserRequired depends on selected token type", () => {
    tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "HOTP" });
    expect(component.isUserRequired()).toBe(false);

    tokenService.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "WebAuthn" });
    expect(component.isUserRequired()).toBe(true);

    tokenService.selectedTokenType.set({ key: "passkey", name: "Passkey", info: "", text: "Passkey" });
    expect(component.isUserRequired()).toBe(true);

    tokenService.selectedTokenType.set({ key: "certificate", name: "Certificate", info: "", text: "Cert" });
    expect(component.isUserRequired()).toBe(true);
  });

  describe("enrollToken()", () => {
    it("snacks and returns when no token type selected", async () => {
      tokenService.selectedTokenType.set("" as unknown as TokenType);

      await component.enrollToken();

      expect(notificationServiceMock.warning).toHaveBeenCalledWith("Please select a token type.");
    });

    it("snacks when user is required but missing", async () => {
      tokenService.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      userService.selectedUser.set(null);

      component.setPin.set("1234");
      component.repeatPin.set("1234");
      userService.selectedUserRealm.set("realm1");
      userService.selectionFilter.set("alice");

      await component.enrollToken();

      expect(notificationServiceMock.warning).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when form is invalid (e.g., PIN mismatch)", async () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      userService.selectedUser.set(null);

      component.setPin.set("1234");
      component.repeatPin.set("9999");

      await component.enrollToken();

      expect(notificationServiceMock.warning).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when clickEnroll is not provided", async () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });

      component.setPin.set("1234");
      component.repeatPin.set("1234");

      installStrategy(component, undefined);

      await component.enrollToken();

      expect(notificationServiceMock.warning).toHaveBeenCalledWith(
        "Enrollment action is not available for the selected token type."
      );
    });

    it("_handleEnrollmentResponse snacks when user is required but missing", () => {
      tokenService.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      (component as unknown as TokenEnrollmentComponentInternals)._handleEnrollmentResponse({
        response: { detail: { rollout_state: "done" } },
        user: null
      } as unknown as EnrollmentResponse);

      expect(notificationServiceMock.warning).toHaveBeenCalledWith(
        "User is required for this token type, but no user was provided."
      );
    });

    it("Default values for enrollment", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterSpy });

      component.enrollToken();

      const expected_parameters = {
        type: "hotp",
        description: "",
        containerSerial: "",
        validityPeriodStart: "",
        validityPeriodEnd: "",
        user: "",
        realm: "",
        onlyAddToRealm: false,
        pin: "",
        serial: null
      };
      expect(enrollmentArgsGetterSpy).toHaveBeenCalledWith(expected_parameters);
    });

    // A token type that is enrolled without a PIN hides the fields, so a PIN left over from
    // another type neither travels with the request nor blocks it through the repeat mismatch
    // it can no longer show.
    it("Does not submit a PIN for a token type that is enrolled without one", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterSpy });
      component.setPin.set("1234");
      component.repeatPin.set("");
      tokenService.selectedTokenType.set({ key: "sshkey", name: "SSH Key", info: "", text: "" });

      component.enrollToken();

      expect(component["showPinFields"]()).toBe(false);
      expect(component.isFormInvalid()).toBe(false);
      expect(enrollmentArgsGetterSpy).toHaveBeenCalledWith(expect.objectContaining({ pin: "" }));
    });

    it("Submits the PIN and enforces the repeat for a type that uses one", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterSpy });
      component.setPin.set("1234");
      component.repeatPin.set("");
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });

      expect(component["showPinFields"]()).toBe(true);
      expect(component.isFormInvalid()).toBe(true);

      component.repeatPin.set("1234");

      expect(component.isFormInvalid()).toBe(false);
      component.enrollToken();
      expect(enrollmentArgsGetterSpy).toHaveBeenCalledWith(expect.objectContaining({ pin: "1234" }));
    });

    it("Treats the form as invalid while the token type reports its enrollment as blocked", () => {
      // A fresh instance: installStrategy swaps in an untracked function, so it must precede the first evaluation.
      const blockedComponent = TestBed.createComponent(TokenEnrollmentComponent).componentInstance;
      installStrategy(blockedComponent, {
        buildEnrollmentArgs: jest.fn(),
        enrollmentBlockedReason: signal("no right")
      });

      expect(blockedComponent.isFormInvalid()).toBe(true);
      expect(blockedComponent.enrollmentBlockedReason()).toBe("no right");
    });

    it("Treats the form as invalid while the token type reports invalid fields of its own", () => {
      const fieldsComponent = TestBed.createComponent(TokenEnrollmentComponent).componentInstance;
      installStrategy(fieldsComponent, { buildEnrollmentArgs: jest.fn(), fieldsInvalid: signal(true) });

      expect(fieldsComponent.isFormInvalid()).toBe(true);
      expect(fieldsComponent.enrollmentBlockedReason()).toBeNull();
    });

    it("Hands the blocking reason to the enroll button of the type selector", () => {
      const blockedFixture = TestBed.createComponent(TokenEnrollmentComponent);
      blockedFixture.componentInstance.enrollmentBlockedReason = signal("no right");
      blockedFixture.detectChanges();

      const selector = blockedFixture.debugElement.query(By.directive(TokenEnrollmentTypeSelectorComponent));
      expect(selector.componentInstance.enrollBlockedReason()).toBe("no right");
      expect(selector.componentInstance.formInvalid()).toBe(true);
    });

    it("Click on the wrapper of the disabled enroll button reveals field errors and does not submit", () => {
      const blockedFixture = TestBed.createComponent(TokenEnrollmentComponent);
      blockedFixture.componentInstance.enrollmentBlockedReason = signal("no right");
      blockedFixture.detectChanges();
      const instance = blockedFixture.componentInstance;
      const revealSpy = jest.spyOn(instance, "revealFieldErrors");
      const enrollSpy = jest.spyOn(instance, "enrollToken");
      const button: HTMLButtonElement = blockedFixture.nativeElement.querySelector("button[type='submit']");

      expect(button.disabled).toBe(true);
      button.parentElement!.click();

      expect(revealSpy).toHaveBeenCalledTimes(1);
      expect(enrollSpy).not.toHaveBeenCalled();
    });

    it("Setting validity dates works", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterSpy });
      component.selectedStartDate.set(new Date("2026-01-01"));
      component.selectedEndDate.set(new Date("2026-12-31"));

      component.enrollToken();

      const expected_parameters = {
        type: "hotp",
        description: "",
        containerSerial: "",
        validityPeriodStart: "2026-01-01T00:00+0000",
        validityPeriodEnd: "2026-12-31T23:59+0000",
        user: "",
        realm: "",
        onlyAddToRealm: false,
        pin: "",
        serial: null
      };
      expect(enrollmentArgsGetterSpy).toHaveBeenCalledWith(expected_parameters);
    });

    describe("enrollment flows", () => {
      it("Simple enrollment only opens last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({ type: "totp" }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterFn });

        // Simulate 2-step init enrollment response
        const enrollResponse = {
          result: { status: true },
          detail: { serial: "TOTP0123456", googleurl: { img: "", value: "" } }
        };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        const spyOpen = jest.spyOn(component as unknown as TokenEnrollmentComponentInternals, "openLastStepDialog");

        // Call enrollToken (should open last step dialog)
        await component.enrollToken();

        expect(enrollmentArgsGetterFn).toHaveBeenCalledTimes(1);
        expect(component.enrollResponse()).toBe(enrollResponse);
        expect(spyOpen).toHaveBeenCalledWith(enrollResponse);

        // Initial enroll API request
        expect(tokenService.enrollToken).toHaveBeenCalled();
        // Open complete dialog
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ response: enrollResponse })
          })
        );

        // Complete and Verify dialog were not opened
        expect(dialogServiceMock.openDialog).not.toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenCompleteEnrollmentComponent,
            data: expect.anything()
          })
        );
        expect(dialogServiceMock.openDialog).not.toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            data: expect.anything()
          })
        );
      });

      it("resets the pending enrollment when the strategy reports a cancellation", async () => {
        tokenService.selectedTokenType.set({ key: "push", name: "Push", info: "", text: "" });
        const reopenDialog = signal<(() => Promise<unknown>) | undefined>(() => Promise.resolve(null));
        installStrategy(component, {
          buildEnrollmentArgs: jest.fn().mockReturnValue({
            data: { type: "push" },
            mapper: jest.fn() as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
          }),
          onEnrollmentResponse: jest.fn().mockResolvedValue(ENROLLMENT_CANCELLED),
          reopenDialog
        });
        tokenService.enrollToken.mockReturnValueOnce(
          of({ result: { status: true }, detail: { serial: "PIPU0001", rollout_state: "clientwait" } })
        );

        const result = await component.enrollToken();

        expect(result).toBe(true);
        expect(component.enrollResponse()).toBeNull();
        expect(component.enrolledDialogData()).toBeNull();
        expect(reopenDialog()).toBeUndefined();
        expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
      });

      it("resets the pending enrollment when the complete dialog cancels it", async () => {
        tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
        installStrategy(component, {
          buildEnrollmentArgs: jest.fn().mockReturnValue({
            data: { type: "hotp" },
            mapper: jest.fn() as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
          })
        });
        tokenService.enrollToken.mockReturnValueOnce(
          of({ result: { status: true }, detail: { serial: "OATH0001", rollout_state: "clientwait" } })
        );
        const dialogRef = new MockMatDialogRef();
        dialogRef.afterClosed.mockReturnValue(of(ENROLLMENT_CANCELLED));
        dialogServiceMock.openDialog.mockReturnValue(dialogRef);

        await component.enrollToken();

        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenCompleteEnrollmentComponent,
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        expect(component.enrollResponse()).toBeNull();
        expect(component.enrolledDialogData()).toBeNull();
      });

      it("resets the pending enrollment when the verify dialog cancels it", async () => {
        tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
        installStrategy(component, {
          buildEnrollmentArgs: jest.fn().mockReturnValue({
            data: { type: "hotp" },
            mapper: jest.fn() as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
          })
        });
        tokenService.enrollToken.mockReturnValueOnce(
          of({ result: { status: true }, detail: { serial: "OATH0002", verify: { message: "Enter OTP" } } })
        );
        const dialogRef = new MockMatDialogRef();
        dialogRef.afterClosed.mockReturnValue(of(ENROLLMENT_CANCELLED));
        dialogServiceMock.openDialog.mockReturnValue(dialogRef);

        await component.enrollToken();

        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        expect(component.enrollResponse()).toBeNull();
        expect(component.enrolledDialogData()).toBeNull();
      });

      it("Strategy with showEnrollDataInLastStep false hides the enroll data in the last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "push", name: "Push", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "push" },
          mapper: jest.fn().mockReturnValue({ type: "push" }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, {
          buildEnrollmentArgs: enrollmentArgsGetterFn,
          showEnrollDataInLastStep: false
        });

        const enrollResponse = {
          result: { status: true },
          detail: { serial: "PIPU0001", rollout_state: "enrolled", pushurl: { img: "img", value: "url" } }
        };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        await component.enrollToken();

        expect(component.enrolledDialogData()?.showEnrollData).toBe(false);
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ showEnrollData: false })
          })
        );
      });

      it("Strategy with showEnrollDataInLastStep true keeps the enroll data in the last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({ type: "totp" }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, {
          buildEnrollmentArgs: enrollmentArgsGetterFn,
          showEnrollDataInLastStep: true
        });

        const enrollResponse = {
          result: { status: true },
          detail: { serial: "TOTP0123456", googleurl: { img: "", value: "" } }
        };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        await component.enrollToken();

        expect(component.enrolledDialogData()?.showEnrollData).toBe(true);
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ showEnrollData: true })
          })
        );
      });

      // enrollToken() of the token service reports the failure itself. The component used to
      // notify a second time and then re-await the rejected promise, which aborted the rest
      // of the method with an unhandled rejection.
      it("returns false on a rejected enrollment without notifying twice", async () => {
        tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
        component.setPin.set("1111");
        component.repeatPin.set("1111");

        const error = { error: { result: { error: { message: "nope" } } } };
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({});
        installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterFn });
        tokenService.enrollToken.mockReturnValue(Promise.reject(error));

        await expect(component.enrollToken()).resolves.toBe(false);

        expect(notificationServiceMock.error).not.toHaveBeenCalled();
      });

      it("warns when the strategy cannot build the enrollment arguments", async () => {
        tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
        installStrategy(component, { buildEnrollmentArgs: jest.fn().mockReturnValue(null) });

        await expect(component.enrollToken()).resolves.toBe(false);

        expect(notificationServiceMock.warning).toHaveBeenCalledWith(
          "Please fill in all required fields or correct invalid entries."
        );
        expect(tokenService.enrollToken).not.toHaveBeenCalled();
      });

      it("Two step enrollment: complete dialog -> last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({
            type: "totp",
            "2stepinit": true
          }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterFn });

        // Simulate 2-step init enrollment response
        const twoStepDetail = {
          serial: "TOTP0123456",
          "2step_output": 64,
          "2step_difficulty": 10000,
          "2step_salt": 1,
          googleurl: { img: "", value: "" },
          rollout_state: "clientwait"
        };
        const enrollResponse = { result: { status: true }, detail: twoStepDetail, type: "hotp" };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        // Mock dialogService.openDialog for both dialogs
        const completeDetail = { serial: "TOTP0123456", googleurl: { img: "", value: "" }, rollout_state: "" };
        const completeResponse = { result: { status: true }, detail: completeDetail, type: "hotp" };
        const afterClosedCompleteMock = jest.fn().mockReturnValue(of(completeResponse));
        dialogServiceMock.openDialog.mockImplementation((opts) => {
          if (opts.component && opts.component.name === "TokenCompleteEnrollmentComponent") {
            return { afterClosed: afterClosedCompleteMock };
          }
          if (opts.component && opts.component.name === "TokenEnrollmentLastStepDialogComponent") {
            return { afterClosed: undefined };
          }
          return { afterClosed: jest.fn().mockReturnValue(of(null)) };
        });

        // Call enrollToken (should open complete dialog, skip verify, open last step dialog)
        await component.enrollToken();

        // Initial enroll API request
        expect(tokenService.enrollToken).toHaveBeenCalled();
        // Open complete dialog
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenCompleteEnrollmentComponent,
            data: expect.objectContaining({ response: enrollResponse }),
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        // After closed complete dialog called and opened last step dialog with correct data
        expect(afterClosedCompleteMock).toHaveBeenCalled();
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ response: completeResponse })
          })
        );

        // Verify dialog was not opened
        expect(dialogServiceMock.openDialog).not.toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            data: expect.anything()
          })
        );
      });

      it("Two step + verify enrollment: complete dialog -> verify dialog -> last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({
            type: "totp",
            "2stepinit": true
          }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterFn });

        // Simulate 2-step init enrollment response
        const twoStepDetail = {
          serial: "TOTP0123456",
          "2step_output": 64,
          "2step_difficulty": 10000,
          "2step_salt": 1,
          googleurl: { img: "", value: "" },
          rollout_state: "clientwait"
        };
        const enrollResponse = { result: { status: true }, detail: twoStepDetail };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        // Mock dialogService.openDialog for all dialogs
        const completeDetail = {
          serial: "TOTP0123456",
          googleurl: { img: "", value: "" },
          rollout_state: "verify",
          verify: { message: "Please enter a valid OTP value of the new token" }
        };
        const completeResponse = { result: { status: true }, detail: completeDetail };
        const afterClosedCompleteMock = jest.fn().mockReturnValue(of(completeResponse));
        const verifyResponse = {
          result: { status: true },
          detail: { serial: "TOTP0123456", rollout_state: "enrolled" }
        };
        const afterClosedVerifyMock = jest.fn().mockReturnValue(of(verifyResponse));
        dialogServiceMock.openDialog.mockImplementation((opts) => {
          if (opts.component && opts.component.name === "TokenCompleteEnrollmentComponent") {
            return { afterClosed: afterClosedCompleteMock };
          }
          if (opts.component && opts.component.name === "TokenVerifyEnrollmentComponent") {
            return { afterClosed: afterClosedVerifyMock };
          }
          if (opts.component && opts.component.name === "TokenEnrollmentLastStepDialogComponent") {
            return { afterClosed: undefined };
          }
          return { afterClosed: jest.fn().mockReturnValue(of(null)) };
        });

        // Call enrollToken (should open complete dialog -> open verify dialog -> open last step dialog)
        await component.enrollToken();

        // Initial enroll API request
        expect(tokenService.enrollToken).toHaveBeenCalled();
        // Open complete dialog
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenCompleteEnrollmentComponent,
            data: expect.objectContaining({ response: enrollResponse }),
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        // After closed complete dialog called and opened verify with correct data
        expect(afterClosedCompleteMock).toHaveBeenCalled();
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            data: expect.objectContaining({ response: completeResponse }),
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        // verify dialog closed and last step dialog opened with correct data
        expect(afterClosedVerifyMock).toHaveBeenCalled();
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ response: verifyResponse })
          })
        );
      });

      it("Verify enrollment: verify dialog -> last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({ type: "totp" }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        installStrategy(component, { buildEnrollmentArgs: enrollmentArgsGetterFn });

        // Simulate init enrollment response
        const completeDetail = {
          serial: "TOTP0123456",
          googleurl: { img: "", value: "" },
          rollout_state: "verify",
          verify: { message: "Please enter a valid OTP value of the new token" }
        };
        const enrollResponse = { result: { status: true }, detail: completeDetail };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        // Mock dialogService.openDialog for all dialogs
        const verifyResponse = {
          result: { status: true },
          detail: { serial: "TOTP0123456", rollout_state: "enrolled" }
        };
        const afterClosedVerifyMock = jest.fn().mockReturnValue(of(verifyResponse));
        dialogServiceMock.openDialog.mockImplementation((opts) => {
          if (opts.component && opts.component.name === "TokenVerifyEnrollmentComponent") {
            return { afterClosed: afterClosedVerifyMock };
          }
          if (opts.component && opts.component.name === "TokenEnrollmentLastStepDialogComponent") {
            return { afterClosed: undefined };
          }
          return { afterClosed: jest.fn().mockReturnValue(of(null)) };
        });

        // Call enrollToken (should open complete dialog -> open verify dialog -> open last step dialog)
        await component.enrollToken();

        // Initial enroll API request
        expect(tokenService.enrollToken).toHaveBeenCalled();
        // Open verify dialog
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            data: expect.objectContaining({ response: enrollResponse }),
            configOverride: { autoFocus: "input", disableClose: true }
          })
        );
        // closed verify dialog and open last step dialog with correct data
        expect(afterClosedVerifyMock).toHaveBeenCalled();
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenEnrollmentLastStepDialogComponent,
            data: expect.objectContaining({ response: verifyResponse })
          })
        );

        // Complete dialog was not opened
        expect(dialogServiceMock.openDialog).not.toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenCompleteEnrollmentComponent,
            data: expect.anything()
          })
        );
      });
    });
  });

  describe("open/reopen dialog flows", () => {
    it("openLastStepDialog: snacks when response is null", () => {
      (component as unknown as TokenEnrollmentComponentInternals).openLastStepDialog(null);
      expect(notificationServiceMock.warning).toHaveBeenCalledWith("No enrollment response available.");
    });

    it("openLastStepDialog: stores last-step data and opens dialog", () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.enrolledDialogData.set({
        response: {} as unknown as EnrollmentResponse,
        enrollParameters: {} as unknown as EnrollTokenArguments,
        tokenType: "hotp"
      });
      const response = { detail: {} } as unknown as EnrollmentResponse;
      (component as unknown as TokenEnrollmentComponentInternals).openLastStepDialog(response);

      expect(dialogServiceMock.openDialog).toHaveBeenCalledTimes(1);
      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: TokenEnrollmentLastStepDialogComponent,
          data: expect.objectContaining({
            tokenType: "hotp",
            response,
            enrollParameters: {}
          })
        })
      );
      expect(component.enrolledDialogData()).toBeDefined();
      expect(component.enrolledDialogData()?.response).toEqual(response);
    });

    it("reopenEnrollmentDialog: uses reopen function when provided", () => {
      const fn = jest.fn().mockReturnValue(of(null));
      installStrategy(component, { reopenDialog: () => fn });
      component.reopenEnrollmentDialog();

      expect(fn).toHaveBeenCalledTimes(1);
      expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    });

    it("reopenEnrollmentDialog: reopens with the regenerated response instead of the initial one", async () => {
      tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
      installStrategy(component, {
        buildEnrollmentArgs: jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn() as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        }),
        reopenDialog: () => undefined
      });
      const enrollResponse = {
        result: { status: true },
        detail: { serial: "TOTP0001", googleurl: { img: "initial-img", value: "initial-url" } }
      } as unknown as EnrollmentResponse;
      tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));
      await component.enrollToken();

      const regenerated = {
        result: { status: true },
        detail: { serial: "TOTP0001", googleurl: { img: "regenerated-img", value: "regenerated-url" } }
      } as unknown as EnrollmentResponse;
      component.enrolledDialogData()?.onEnrollmentResponseChange?.(regenerated);

      expect(component.enrollResponse()).toBe(regenerated);
      expect(component.enrolledDialogData()?.response).toBe(regenerated);

      dialogServiceMock.openDialog.mockClear();
      component.reopenEnrollmentDialog();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: TokenEnrollmentLastStepDialogComponent,
          data: expect.objectContaining({ response: regenerated })
        })
      );
    });

    it("reopenEnrollmentDialog: falls back to last-step data", () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.enrolledDialogData.set({
        tokenType: "hotp",
        response: { result: {}, detail: {} } as unknown as EnrollmentResponse,
        enrollParameters: {} as unknown as EnrollTokenArguments
      });

      const internals = component as unknown as TokenEnrollmentComponentInternals;
      const completeSpy = jest.spyOn(internals, "handleCompleteEnrollment");
      const verifySpy = jest.spyOn(internals, "handleVerifyEnrollment");
      const successSpy = jest.spyOn(internals, "_handleEnrollmentResponse");
      component.reopenEnrollmentDialog();
      expect(completeSpy).toHaveBeenCalledTimes(1);
      expect(verifySpy).toHaveBeenCalledTimes(1);
      expect(successSpy).toHaveBeenCalledTimes(1);
      expect(dialogServiceMock.openDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe("ngOnInit subscriptions", () => {
    it("selectedContainer signal updates containerService.selectedContainer", () => {
      const containers = TestBed.inject(ContainerService) as unknown as MockContainerService;

      component.selectedContainer.set("CONT-9");
      component.ngOnInit();
      component.selectedContainer.set("CONT-42");
      fixture.detectChanges();

      expect(containers.selectedContainerSerial()).toBe("CONT-42");
    });
  });

  describe("wizard", () => {
    let wizardFixture: ComponentFixture<TokenEnrollmentWizardComponent>;
    let wizardComponent: TokenEnrollmentWizardComponent;

    beforeEach(() => {
      wizardFixture = TestBed.createComponent(TokenEnrollmentWizardComponent);
      wizardComponent = wizardFixture.componentInstance;
    });

    it("warns when opening the last step dialog without a response", () => {
      wizardComponent.openLastStepDialog(null);
      expect(notificationServiceMock.warning).toHaveBeenCalledWith("No enrollment response available.");
    });

    it("creates", () => {
      expect(wizardComponent).toBeTruthy();
      wizardFixture.detectChanges();
      const req = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.top.html"
      );
      req.flush("");
      const req2 = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.bottom.html"
      );
      req2.flush("");
    });

    it("disables the enroll button and shows the blocking reason on it", () => {
      // Set before the first render so isFormInvalid picks it up.
      wizardComponent.enrollmentBlockedReason = signal("no right");
      wizardFixture.detectChanges();
      httpTestingController
        .expectOne(environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.top.html")
        .flush("");
      httpTestingController
        .expectOne(environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.bottom.html")
        .flush("");
      wizardFixture.detectChanges();

      const button: HTMLButtonElement = wizardFixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(true);
      const tooltip = wizardFixture.debugElement
        .queryAll(By.directive(MatTooltip))
        .find((el) => el.nativeElement.contains(button))!
        .injector.get(MatTooltip);
      expect(tooltip.disabled).toBe(false);
      expect(tooltip.message).toBe("no right");
    });

    it("show default content if no custom content is defined", () => {
      authServiceMock.authData.set({
        ...authServiceMock.authData()!,
        token_wizard: true
      });
      wizardFixture.detectChanges();
      const req = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.top.html"
      );
      req.flush("");
      const req2 = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.bottom.html"
      );
      req2.flush("");
      wizardFixture.detectChanges();
      expect(wizardFixture.nativeElement.textContent).toContain("Enroll HOTP Token");
    });

    it("show custom content if defined", () => {
      authServiceMock.authData.set({
        ...authServiceMock.authData()!,
        token_wizard: true
      });
      wizardFixture.detectChanges();
      const req = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.top.html"
      );
      req.flush("Custom Content");
      const req2 = httpTestingController.expectOne(
        environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.bottom.html"
      );
      req2.flush("");
      wizardFixture.detectChanges();
      expect(wizardFixture.nativeElement.textContent).toContain("Custom Content");
      expect(wizardFixture.nativeElement.textContent).not.toContain("Enroll HOTP Token");
    });

    describe("wizard renders description correctly", () => {
      beforeEach(() => {
        wizardFixture.detectChanges();
        const req = httpTestingController.expectOne(
          environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.top.html"
        );
        req.flush("");
        const req2 = httpTestingController.expectOne(
          environment.proxyUrl + "/static/public/customize/token-enrollment.wizard.pre.bottom.html"
        );
        req2.flush("");
      });

      // A new target makes the wizard load the enrollment policies again.
      const loadPoliciesRequiringDescription = (requireDescription: boolean, realm: string) => {
        tokenService.getEnrollmentPolicies.mockReturnValue(
          of(
            MockPiResponse.fromValue<EnrollmentPolicies>({
              defaults: {},
              "2step": null,
              force_server_generate: false,
              sms_gateways: [],
              require_description: requireDescription
            })
          )
        );
        userService.selectedUserRealm.set(realm);
        userService.selectedUser.set({ username: "wizard-user" } as unknown as UserData);
      };

      it("description form reports required error when description is required and empty", () => {
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(true, "wizard-realm-1");
        wizardFixture.detectChanges();
        expect(wizardComponent.descriptionRequired()).toBe(true);
        wizardComponent.description.set("");
        wizardComponent.descriptionForm().markAsTouched();
        wizardFixture.detectChanges();
        expect(
          wizardComponent
            .descriptionForm()
            .errors()
            .some((e) => e.kind === "required")
        ).toBe(true);
      });

      it("description form is valid when description is not required", () => {
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["totp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(false, "wizard-realm-2");
        wizardFixture.detectChanges();
        expect(wizardComponent.descriptionRequired()).toBe(false);
        wizardComponent.description.set("");
        wizardComponent.descriptionForm().markAsTouched();
        wizardFixture.detectChanges();
        expect(
          wizardComponent
            .descriptionForm()
            .errors()
            .some((e) => e.kind === "required")
        ).toBe(false);
        expect(wizardComponent.descriptionForm().valid()).toBe(true);
      });

      it("shows description input only if description is required", () => {
        // Description required
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(true, "wizard-realm-3");
        wizardFixture.detectChanges();
        expect(wizardFixture.nativeElement.querySelector("mat-form-field.description-form")).not.toBeNull();

        // Description not required
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: [],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(false, "wizard-realm-4");
        wizardFixture.detectChanges();
        expect(wizardFixture.nativeElement.querySelector("mat-form-field.description-form")).toBeNull();
      });

      it("marks the description as required when the enrollment policies require it", () => {
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(true, "wizard-realm-5");
        wizardFixture.detectChanges();
        const field: HTMLElement = wizardFixture.nativeElement.querySelector("mat-form-field.description-form");
        expect(field.querySelector("textarea")!.required).toBe(true);
        expect(field.querySelector(".mat-mdc-form-field-required-marker")).not.toBeNull();
      });

      it("shows all field errors when the disabled Enroll button is clicked", () => {
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        loadPoliciesRequiringDescription(true, "wizard-realm-6");
        wizardFixture.detectChanges();
        const hotp = wizardFixture.debugElement.query(By.directive(EnrollHotpComponent))
          .componentInstance as EnrollHotpComponent;
        hotp.generateOnServer.set(false);
        wizardFixture.detectChanges();

        const button: HTMLButtonElement = wizardFixture.nativeElement.querySelector("button[type='submit']");
        expect(button.disabled).toBe(true);
        expect(wizardFixture.nativeElement.textContent).not.toContain("Description is required.");

        // The click on the wrapper of the disabled button reveals the errors.
        button.parentElement!.click();
        wizardFixture.detectChanges();

        expect(wizardComponent.descriptionForm().touched()).toBe(true);
        expect(hotp.otpKeyForm().touched()).toBe(true);
        expect(wizardFixture.nativeElement.textContent).toContain("Description is required.");
      });
    });
  });

  describe("enrollment policies", () => {
    const policies: EnrollmentPolicies = {
      defaults: { hashlib: "sha512", otplen: "8" },
      "2step": "force",
      force_server_generate: false,
      sms_gateways: [],
      require_description: false
    };
    const asUser = (username: string): UserData => ({ username }) as unknown as UserData;

    it("enrollment policies follow the selected target", () => {
      userService.selectedUserRealm.set("realm1");
      userService.selectedUser.set(asUser("alice"));
      fixture.detectChanges();
      expect(tokenService.getEnrollmentPolicies).toHaveBeenLastCalledWith(
        expect.objectContaining({ type: "hotp", user: "alice", realm: "realm1" })
      );

      userService.selectedUserRealm.set("realm2");
      userService.selectedUser.set(asUser("bob"));
      fixture.detectChanges();
      expect(tokenService.getEnrollmentPolicies).toHaveBeenLastCalledWith(
        expect.objectContaining({ type: "hotp", user: "bob", realm: "realm2" })
      );

      tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
      fixture.detectChanges();
      expect(tokenService.getEnrollmentPolicies).toHaveBeenLastCalledWith(
        expect.objectContaining({ type: "totp", user: "bob", realm: "realm2" })
      );
    });

    // The policies endpoint must see exactly the user and realm that POST /token/init sends for the same form state.
    const userAssignment = () => {
      authServiceMock.authData.set({ ...authServiceMock.authData()!, rights: ["userlist"] });
      fixture.detectChanges();
      return fixture.debugElement.query(By.directive(UserAssignmentComponent))
        .componentInstance as UserAssignmentComponent;
    };
    const sentInitPayload = async () => {
      const mapper = TestBed.inject(HotpApiPayloadMapper);
      installStrategy(component, { buildEnrollmentArgs: (data: TokenEnrollmentData) => ({ data, mapper }) });
      tokenService.enrollToken.mockClear();
      await component.enrollToken();
      expect(tokenService.enrollToken).toHaveBeenCalledTimes(1);
      const args = tokenService.enrollToken.mock.calls[0][0] as EnrollTokenArguments;
      return args.mapper.toApiPayload(args.data);
    };
    const lastPolicyTarget = () => tokenService.getEnrollmentPolicies.mock.calls.at(-1)![0] as EnrollmentPolicyTarget;

    it("requests the enrollment policies without a realm when no user is selected", async () => {
      userService.selectedUserRealm.set("passwd");
      userService.selectedUser.set(null);
      fixture.detectChanges();
      userAssignment().onlyAddToRealm.set(false);
      fixture.detectChanges();

      const payload = await sentInitPayload();
      expect(payload.user).toBeUndefined();
      expect(payload.realm).toBeUndefined();

      const target = lastPolicyTarget();
      expect(target.user).toBeUndefined();
      expect(target.realm).toBeUndefined();
    });

    it("requests the enrollment policies with the realm when only adding to the realm", async () => {
      userService.selectedUserRealm.set("passwd");
      userService.selectedUser.set(null);
      fixture.detectChanges();
      userAssignment().onlyAddToRealmChange(true);
      fixture.detectChanges();

      const target = lastPolicyTarget();
      expect(target.realm).toBe("passwd");
      expect(target.user).toBeUndefined();

      const payload = await sentInitPayload();
      expect(payload.realm).toBe("passwd");
      expect(payload.user).toBeUndefined();
    });

    it("uses the same user and realm for the policies and the enrollment", async () => {
      userService.selectedUserRealm.set("realm1");
      userService.selectedUser.set(asUser("alice"));
      fixture.detectChanges();

      const target = lastPolicyTarget();
      const payload = await sentInitPayload();
      expect(target.user).toBe("alice");
      expect(target.realm).toBe("realm1");
      expect({ user: target.user, realm: target.realm }).toEqual({ user: payload.user, realm: payload.realm });
    });

    describe("while the enrollment policies load", () => {
      const startLoading = () => {
        const response = new Subject<PiResponse<EnrollmentPolicies>>();
        tokenService.getEnrollmentPolicies.mockReturnValue(response);
        const freshFixture = TestBed.createComponent(TokenEnrollmentComponent);
        const fresh = freshFixture.componentInstance;
        freshFixture.detectChanges();
        const buildEnrollmentArgs = jest.fn().mockReturnValue({
          data: { type: "hotp" },
          mapper: jest.fn().mockReturnValue({ type: "hotp" }) as unknown as TokenApiPayloadMapper<TokenEnrollmentData>
        });
        const markFieldsTouched = jest.fn();
        installStrategy(fresh, { buildEnrollmentArgs, markFieldsTouched });
        tokenService.enrollToken.mockReturnValue(
          of({ result: { status: true }, detail: { serial: "HOTP1", googleurl: { img: "", value: "" } } })
        );
        const answer = (value: Partial<EnrollmentPolicies>) => {
          response.next(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, ...value }));
          freshFixture.detectChanges();
        };
        return { fresh, freshFixture, answer, buildEnrollmentArgs, markFieldsTouched };
      };

      it("does not look blocked or invalid", () => {
        const { fresh } = startLoading();
        expect(fresh.enrollmentPoliciesLoading()).toBe(true);
        expect(fresh.enrollmentBlockedReason()).toBeNull();
        expect(fresh.isFormInvalid()).toBe(false);
      });

      it("enrolls after the response when the form is valid with the new policies", async () => {
        const { fresh, answer, buildEnrollmentArgs } = startLoading();
        const result = fresh.enrollToken();
        await Promise.resolve();
        expect(tokenService.enrollToken).not.toHaveBeenCalled();
        expect(buildEnrollmentArgs).not.toHaveBeenCalled();

        answer({ require_description: false });
        await result;
        expect(tokenService.enrollToken).toHaveBeenCalledTimes(1);
      });

      it("does not enroll and reveals the errors when the new policies make the form invalid", async () => {
        const { fresh, answer, markFieldsTouched } = startLoading();
        fresh.description.set("");
        const result = fresh.enrollToken();
        await Promise.resolve();

        answer({ require_description: true });
        expect(await result).toBe(false);
        expect(tokenService.enrollToken).not.toHaveBeenCalled();
        expect(fresh.descriptionForm().touched()).toBe(true);
        expect(markFieldsTouched).toHaveBeenCalled();
      });

      it("does not enroll when the policies cannot be determined", async () => {
        const { fresh, freshFixture } = startLoading();
        tokenService.getEnrollmentPolicies.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
        userService.selectedUserRealm.set("realm1");
        userService.selectedUser.set(asUser("alice"));
        freshFixture.detectChanges();
        expect(await fresh.enrollToken()).toBe(false);
        expect(tokenService.enrollToken).not.toHaveBeenCalled();
      });
    });

    it("keeps the previous policies visible while those of a new target load", () => {
      const next = new Subject<PiResponse<EnrollmentPolicies>>();
      tokenService.getEnrollmentPolicies.mockReturnValueOnce(
        of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, "2step": "allow" }))
      );
      const freshFixture = TestBed.createComponent(TokenEnrollmentComponent);
      const fresh = freshFixture.componentInstance;
      freshFixture.detectChanges();
      expect(fresh.enrollmentPolicyState().state).toBe("loaded");

      tokenService.getEnrollmentPolicies.mockReturnValue(next);
      userService.selectedUserRealm.set("realm1");
      userService.selectedUser.set(asUser("alice"));
      freshFixture.detectChanges();

      expect(fresh.enrollmentPoliciesLoading()).toBe(true);
      const state = fresh.enrollmentPolicyState();
      expect(loadedEnrollmentPolicies(state)?.["2step"]).toBe("allow");
      expect(state.state).toBe("pending");
    });

    it("blocks Enroll with the policy error", () => {
      const message = "There are policies with conflicting actions: ['a', 'b']";
      tokenService.getEnrollmentPolicies.mockReturnValue(
        throwError(
          () =>
            new HttpErrorResponse({ status: 403, error: { result: { status: false, error: { code: 303, message } } } })
        )
      );
      const freshFixture = TestBed.createComponent(TokenEnrollmentComponent);
      const fresh = freshFixture.componentInstance;
      freshFixture.detectChanges();

      expect(fresh.enrollmentBlockedReason()).toContain(message);
      expect(fresh.isFormInvalid()).toBe(true);
      expect(freshFixture.nativeElement.textContent).toContain(message);
    });

    it("passes the blocked reason to the type selector", () => {
      tokenService.getEnrollmentPolicies.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
      const selfFixture = TestBed.createComponent(TokenEnrollmentSelfServiceComponent);
      selfFixture.detectChanges();

      const selector = selfFixture.debugElement.query(By.directive(TokenEnrollmentTypeSelectorComponent))
        .componentInstance as TokenEnrollmentTypeSelectorComponent;
      expect(selector.enrollBlockedReason()).not.toBeNull();
      expect(selector.enrollBlockedReason()).toBe(selfFixture.componentInstance.enrollmentBlockedReason());
    });

    it("requires the description from the enrollment policies", () => {
      const descriptionFormFor = (requireDescription: boolean) => {
        tokenService.getEnrollmentPolicies.mockReturnValue(
          of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, require_description: requireDescription }))
        );
        const freshFixture = TestBed.createComponent(TokenEnrollmentComponent);
        const fresh = freshFixture.componentInstance;
        freshFixture.detectChanges();
        fresh.description.set("");
        freshFixture.detectChanges();
        return fresh.descriptionForm();
      };

      authServiceMock.authData.set({ ...authServiceMock.authData()!, require_description: [] });
      expect(descriptionFormFor(true).valid()).toBe(false);

      authServiceMock.authData.set({ ...authServiceMock.authData()!, require_description: ["hotp"] });
      expect(descriptionFormFor(false).valid()).toBe(true);
    });

    const renderWithPolicies = <C extends TokenEnrollmentComponent>(
      componentType: Type<C>,
      overrides: Partial<EnrollmentPolicies>
    ): ComponentFixture<C> => {
      tokenService.getEnrollmentPolicies.mockReturnValue(
        of(MockPiResponse.fromValue<EnrollmentPolicies>({ ...policies, ...overrides }))
      );
      const freshFixture = TestBed.createComponent(componentType);
      freshFixture.detectChanges();
      return freshFixture;
    };
    const descriptionField = (root: HTMLElement): HTMLElement =>
      Array.from(root.querySelectorAll<HTMLElement>("mat-form-field")).find(
        (field) => field.querySelector("mat-label")?.textContent?.trim() === "Description"
      )!;
    const variants: [string, Type<TokenEnrollmentComponent>][] = [
      ["admin", TokenEnrollmentComponent],
      ["self-service", TokenEnrollmentSelfServiceComponent]
    ];

    it("does not notify or throw when the disabled Enroll button is clicked for passkey", () => {
      tokenService.selectedTokenType.set({ key: "passkey", name: "Passkey", info: "", text: "" });
      const freshFixture = renderWithPolicies(TokenEnrollmentComponent, { require_description: true });
      const fresh = freshFixture.componentInstance;
      notificationServiceMock.error.mockClear();

      const button: HTMLButtonElement = freshFixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(true);
      expect(() => fresh.revealFieldErrors()).not.toThrow();
      button.parentElement!.click();
      freshFixture.detectChanges();

      expect(notificationServiceMock.error).not.toHaveBeenCalled();
      expect(fresh.descriptionForm().touched()).toBe(true);
    });

    describe.each(variants)("%s", (_variant, componentType) => {
      it("marks the description as required when the enrollment policies require it", () => {
        const freshFixture = renderWithPolicies(componentType, { require_description: true });
        const field = descriptionField(freshFixture.nativeElement);
        expect(field).toBeDefined();
        expect(field.querySelector("textarea")!.required).toBe(true);
        expect(field.querySelector(".mat-mdc-form-field-required-marker")).not.toBeNull();
      });

      it("does not mark the description as required without the enrollment policy", () => {
        const freshFixture = renderWithPolicies(componentType, { require_description: false });
        const field = descriptionField(freshFixture.nativeElement);
        expect(field).toBeDefined();
        expect(field.querySelector("textarea")!.required).toBe(false);
        expect(field.querySelector(".mat-mdc-form-field-required-marker")).toBeNull();
      });

      it("shows all field errors when the disabled Enroll button is clicked", () => {
        const freshFixture = renderWithPolicies(componentType, { require_description: true, "2step": null });
        const fresh = freshFixture.componentInstance;
        const hotp = freshFixture.debugElement.query(By.directive(EnrollHotpComponent))
          .componentInstance as EnrollHotpComponent;
        hotp.generateOnServer.set(false);
        fresh.setPin.set("1234");
        freshFixture.detectChanges();

        const button: HTMLButtonElement = freshFixture.nativeElement.querySelector("button[type='submit']");
        expect(button.disabled).toBe(true);
        expect(freshFixture.nativeElement.textContent).not.toContain("Description is required.");

        // The click on the wrapper of the disabled button reveals the errors.
        button.parentElement!.click();
        freshFixture.detectChanges();

        expect(fresh.descriptionForm().touched()).toBe(true);
        expect(fresh.repeatPinForm().touched()).toBe(true);
        expect(hotp.otpKeyForm().touched()).toBe(true);
        expect(freshFixture.nativeElement.textContent).toContain("Description is required.");
        expect(freshFixture.nativeElement.textContent).toContain("OTP key is required");
      });
    });

    it("forwards enrollmentPolicies to the hotp component", () => {
      const loaded: EnrollmentPolicyState = { state: "loaded", policies };
      const switchFixture = TestBed.createComponent(EnrollTokenTypeSwitchComponent);
      switchFixture.componentRef.setInput("tokenTypeKey", "hotp");
      switchFixture.detectChanges();
      const hotp = () =>
        switchFixture.debugElement.query(By.directive(EnrollHotpComponent)).componentInstance as EnrollHotpComponent;
      expect(hotp().enrollmentPolicies()).toEqual({ state: "unrestricted" });

      switchFixture.componentRef.setInput("enrollmentPolicies", loaded);
      switchFixture.detectChanges();

      expect(hotp().enrollmentPolicies()).toEqual(loaded);
    });
  });

  describe("pending changes", () => {
    it("registers hasChanges, validChanges, and save in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("hasChanges reflects the form's dirty state", () => {
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      expect(fn()).toBe(false);
      component.descriptionForm().markAsDirty();
      expect(fn()).toBe(true);
    });

    it("validChanges is false when no token type is selected", () => {
      const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      tokenService.selectedTokenType.set({ key: "", name: "", info: "", text: "" } as unknown as TokenType);
      expect(fn()).toBe(false);
    });

    it("ngOnDestroy clears all pending-changes registrations", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });
  });
});

describe("token-enrollment constants", () => {
  const hasQr = (type: string) => !NO_QR_CODE_TOKEN_TYPES.includes(type);
  const canRegenerate = (type: string) => !NO_REGENERATE_TOKEN_TYPES.includes(type);
  const regenerateLabel = (type: string) => (REGENERATE_AS_VALUES_TOKEN_TYPES.includes(type) ? "Values" : "QR Code");

  it("REGENERATE_AS_VALUES_TOKEN_TYPES is a subset of NO_QR_CODE_TOKEN_TYPES", () => {
    const allIn = REGENERATE_AS_VALUES_TOKEN_TYPES.every((t) => NO_QR_CODE_TOKEN_TYPES.includes(t));
    expect(allIn).toBe(true);
  });

  it("NO_REGENERATE_TOKEN_TYPES contains WebAuthn and Passkey", () => {
    expect(NO_REGENERATE_TOKEN_TYPES).toEqual(expect.arrayContaining(["webauthn", "passkey"]));
  });

  it("NO_QR_CODE_TOKEN_TYPES lists paper and tan; does not include hotp", () => {
    expect(NO_QR_CODE_TOKEN_TYPES).toEqual(expect.arrayContaining(["paper", "tan"]));
    expect(NO_QR_CODE_TOKEN_TYPES).not.toContain("hotp");
  });

  it("hotp → shows QR, can regenerate, label is 'QR Code'", () => {
    expect(hasQr("hotp")).toBe(true);
    expect(canRegenerate("hotp")).toBe(true);
    expect(regenerateLabel("hotp")).toBe("QR Code");
  });

  it("paper → no QR, can regenerate, label is 'Values'", () => {
    expect(hasQr("paper")).toBe(false);
    expect(canRegenerate("paper")).toBe(true);
    expect(regenerateLabel("paper")).toBe("Values");
  });

  it("tan → no QR, can regenerate, label is 'Values'", () => {
    expect(hasQr("tan")).toBe(false);
    expect(canRegenerate("tan")).toBe(true);
    expect(regenerateLabel("tan")).toBe("Values");
  });

  it("indexedsecret → no QR and cannot regenerate", () => {
    expect(hasQr("indexedsecret")).toBe(false);
    expect(canRegenerate("indexedsecret")).toBe(false);
    expect(regenerateLabel("indexedsecret")).toBe("QR Code");
  });

  it("webauthn → no QR, cannot regenerate; label would be 'QR Code'", () => {
    expect(hasQr("webauthn")).toBe(false);
    expect(canRegenerate("webauthn")).toBe(false);
    expect(regenerateLabel("webauthn")).toBe("QR Code");
  });

  it("passkey → no QR, cannot regenerate; label would be 'QR Code'", () => {
    expect(hasQr("passkey")).toBe(false);
    expect(canRegenerate("passkey")).toBe(false);
    expect(regenerateLabel("passkey")).toBe("QR Code");
  });
});
