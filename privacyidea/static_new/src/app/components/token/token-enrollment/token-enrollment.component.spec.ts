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

import { TokenEnrollmentComponent } from "./token-enrollment.component";
import { UserService } from "../../../services/user/user.service";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockRealmService,
  MockTokenService,
  MockUserService,
  MockVersioningService
} from "../../../../testing/mock-services";
import { TokenService } from "../../../services/token/token.service";
import { LocalService } from "../../../services/local/local.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { ContainerService } from "../../../services/container/container.service";
import { RealmService } from "../../../services/realm/realm.service";
import { AuthService } from "../../../services/auth/auth.service";
import { VersioningService } from "../../../services/version/version.service";
import { ContentService } from "../../../services/content/content.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { FormControl, FormGroup, Validators } from "@angular/forms";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { TokenEnrollmentSelfServiceComponent } from "./token-enrollment.self-service.component";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "./token-enrollment.constants";
import { TokenEnrollmentWizardComponent } from "./token-enrollment.wizard.component";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";
import { environment } from "../../../../environments/environment";
import { MockDialogService } from "../../../../testing/mock-services/mock-dialog-service";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";

describe("TokenEnrollmentComponent", () => {
  let fixture: ComponentFixture<TokenEnrollmentComponent>;
  let component: TokenEnrollmentComponent;
  let selfFixture: ComponentFixture<TokenEnrollmentSelfServiceComponent>;
  let selfComponent: TokenEnrollmentSelfServiceComponent;

  let tokenService: MockTokenService;
  let userSvc: MockUserService;
  let notificationServiceMock: MockNotificationService;
  let dialogServiceMock: MockDialogService;
  let authServiceMock: MockAuthService;
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

      constructor(_: any, __?: any) {}
    }

    (global as any).IntersectionObserver = IO;
  });

  beforeEach(async () => {
    let mockVersioningService: MockVersioningService;

    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        NoopAnimationsModule,
        MockLocalService,
        MockNotificationService,
        { provide: LocalService, useExisting: MockLocalService },
        { provide: NotificationService, useExisting: MockNotificationService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: UserService, useClass: MockUserService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentComponent);
    component = fixture.componentInstance;
    selfFixture = TestBed.createComponent(TokenEnrollmentSelfServiceComponent);
    selfComponent = selfFixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    userSvc = TestBed.inject(UserService) as unknown as MockUserService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockVersioningService = TestBed.inject(VersioningService) as unknown as MockVersioningService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
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
    expect(selfComponent).toBeTruthy();
  });

  it("formatDateTimeOffset builds the expected ISO-ish string", () => {
    const d = new Date("2025-09-10T00:00:00Z");
    const result = component.formatDateTimeOffset(d, "08:05", "+02:00");
    expect(result).toBe("2025-09-10T08:05+0200");
  });

  it("no default values for validity period", () => {
    expect(component.selectedStartDateControl.value).toBeNull();
    expect(component.selectedEndDateControl.value).toBeNull();
  });

  it("pinMismatchValidator: returns error when PINs differ; null when equal", () => {
    const group = new FormGroup({
      setPin: new FormControl("1234", { nonNullable: true }),
      repeatPin: new FormControl("9999", { nonNullable: true })
    });
    expect(TokenEnrollmentComponent.pinMismatchValidator(group)).toEqual({ pinMismatch: true });

    group.get("repeatPin")!.setValue("1234");
    expect(TokenEnrollmentComponent.pinMismatchValidator(group)).toBeNull();
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

  it("userExistsValidator flags unknown usernames and accepts existing ones", () => {
    userSvc.users.set([
      {
        username: "alice",
        resolver: "r1",
        description: "",
        editable: false,
        email: "",
        givenname: "",
        mobile: "",
        phone: "",
        surname: "",
        userid: "",
        user_realm: ""
      } as any,
      {
        username: "bob",
        resolver: "r1",
        description: "",
        editable: false,
        email: "",
        givenname: "",
        mobile: "",
        phone: "",
        surname: "",
        userid: "",
        user_realm: ""
      } as any
    ]);

    const ctrl = new FormControl<string | any | null>("charlie", { nonNullable: true });
    expect(component.userExistsValidator(ctrl as any)).toEqual({ userNotInRealm: { value: "charlie" } });

    ctrl.setValue("alice");
    expect(component.userExistsValidator(ctrl as any)).toBeNull();

    ctrl.setValue({ username: "alice" });
    expect(component.userExistsValidator(ctrl as any)).toBeNull();

    ctrl.setValue("");
    expect(component.userExistsValidator(ctrl as any)).toBeNull();
  });

  describe("enrollToken()", () => {
    it("snacks and returns when no token type selected", async () => {
      (tokenService.selectedTokenType as any).set("");

      await (component as any).enrollToken();

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Please select a token type.");
    });

    it("snacks when user is required but missing", async () => {
      tokenService.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      userSvc.selectedUser.set(null);

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("1234");
      component.selectedUserRealmControl.setValue("realm1");
      component.userFilterControl.setValue("alice");

      await (component as any).enrollToken();

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when form is invalid (e.g., PIN mismatch)", async () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      userSvc.selectedUser.set(null);

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("9999");

      await (component as any).enrollToken();

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when clickEnroll is not provided", async () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("1234");

      component.enrollmentArgsGetter = undefined;

      await component.enrollToken();

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "Enrollment action is not available for the selected token type."
      );
    });

    it("_handleEnrollmentResponse snacks when user is required but missing", () => {
      tokenService.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      (component as any)._handleEnrollmentResponse({
        response: { detail: { rollout_state: "done" } } as any,
        user: null
      });

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "User is required for this token type, but no user was provided."
      );
    });

    it("Default values for enrollment", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      component.enrollmentArgsGetter = enrollmentArgsGetterSpy;

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

    it("Setting validity dates works", () => {
      const enrollmentArgsGetterSpy = jest.fn().mockReturnValue({ data: {}, mapper: {} });
      component.enrollmentArgsGetter = enrollmentArgsGetterSpy;
      component.selectedStartDateControl.setValue(new Date("2026-01-01"));
      component.selectedEndDateControl.setValue(new Date("2026-12-31"));

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
          mapper: jest.fn().mockReturnValue({ type: "totp" }) as any
        });
        component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);

        // Simulate 2-step init enrollment response
        const enrollResponse = {
          result: { status: true },
          detail: { serial: "TOTP0123456", googleurl: { img: "", value: "" } }
        };
        tokenService.enrollToken.mockReturnValueOnce(of(enrollResponse));

        const spyOpen = jest.spyOn(component as any, "openLastStepDialog");

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

      it("handles clickEnroll rejection by showing error snack", async () => {
        tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
        component.setPinControl.setValue("1111");
        component.repeatPinControl.setValue("1111");

        const error = { error: { result: { error: { message: "nope" } } } };
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({});
        component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);
        tokenService.enrollToken.mockReturnValue(Promise.reject(error));

        await component.enrollToken().catch(() => undefined);

        expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to enroll token: nope");
      });

      it("Two step enrollment: complete dialog -> last step dialog", async () => {
        tokenService.selectedTokenType.set({ key: "totp", name: "TOTP", info: "", text: "" });
        const enrollmentArgsGetterFn = jest.fn().mockReturnValue({
          data: { type: "totp" },
          mapper: jest.fn().mockReturnValue({ type: "totp", "2stepinit": true }) as any
        });
        component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);

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
            data: expect.objectContaining({ response: enrollResponse })
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
          mapper: jest.fn().mockReturnValue({ type: "totp", "2stepinit": true }) as any
        });
        component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);

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
            data: expect.objectContaining({ response: enrollResponse })
          })
        );
        // After closed complete dialog called and opened verify with correct data
        expect(afterClosedCompleteMock).toHaveBeenCalled();
        expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
          expect.objectContaining({
            component: TokenVerifyEnrollmentComponent,
            data: expect.objectContaining({ response: completeResponse })
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
          mapper: jest.fn().mockReturnValue({ type: "totp" }) as any
        });
        component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);

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
            data: expect.objectContaining({ response: enrollResponse })
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
      (component as any).openLastStepDialog(null);
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("No enrollment response available.");
    });

    it("openLastStepDialog: stores last-step data and opens dialog", () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.enrolledDialogData.set({ response: {} as any, enrollParameters: {} as any, tokenType: "hotp" });
      const response = { detail: {} } as any;
      (component as any).openLastStepDialog(response);

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
      component.updateReopenDialog(fn);
      component.reopenEnrollmentDialog();

      expect(fn).toHaveBeenCalledTimes(1);
      expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    });

    it("reopenEnrollmentDialog: falls back to last-step data", () => {
      tokenService.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.enrolledDialogData.set({
        tokenType: "hotp",
        response: { result: {}, detail: {} } as any,
        enrollParameters: {} as any
      });

      const completeSpy = jest.spyOn(component as any, "handleCompleteEnrollment");
      const verifySpy = jest.spyOn(component as any, "handleVerifyEnrollment");
      const successSpy = jest.spyOn(component as any, "_handleEnrollmentResponse");
      component.reopenEnrollmentDialog();
      expect(completeSpy).toHaveBeenCalledTimes(1);
      expect(verifySpy).toHaveBeenCalledTimes(1);
      expect(successSpy).toHaveBeenCalledTimes(1);
      expect(dialogServiceMock.openDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe("ngOnInit subscriptions", () => {
    it("selectedContainerControl updates containerService.selectedContainer", () => {
      const containers = TestBed.inject(ContainerService) as unknown as MockContainerService;

      component.selectedContainerControl.setValue("CONT-9");
      component.ngOnInit();
      component.selectedContainerControl.setValue("CONT-42");

      expect(containers.selectedContainer()).toBe("CONT-42");
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
      expect(regenerateLabel("indexedsecret")).toBe("QR Code"); // label ignored when cannot regenerate
    });

    it("webauthn → no QR, cannot regenerate; label would be 'QR Code'", () => {
      expect(hasQr("webauthn")).toBe(false);
      expect(canRegenerate("webauthn")).toBe(false);
      expect(regenerateLabel("webauthn")).toBe("QR Code"); // label ignored when cannot regenerate
    });

    it("passkey → no QR, cannot regenerate; label would be 'QR Code'", () => {
      expect(hasQr("passkey")).toBe(false);
      expect(canRegenerate("passkey")).toBe(false);
      expect(regenerateLabel("passkey")).toBe("QR Code"); // label ignored when cannot regenerate
    });
  });

  describe("wizard", () => {
    let wizardFixture: ComponentFixture<TokenEnrollmentWizardComponent>;
    let wizardComponent: TokenEnrollmentWizardComponent;

    beforeEach(() => {
      wizardFixture = TestBed.createComponent(TokenEnrollmentWizardComponent);
      wizardComponent = wizardFixture.componentInstance;
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

      it("sets description validator correctly when description is required", () => {
        // Set require_description for HOTP
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        wizardFixture.detectChanges();
        wizardComponent.setDescriptionValidators();
        wizardFixture.detectChanges();
        expect(wizardComponent.descriptionRequired()).toBe(true);
        expect(wizardComponent.descriptionControl.hasValidator(Validators.required)).toBe(true);
        // Should have required error if empty
        wizardComponent.descriptionControl.setValue("");
        wizardComponent.descriptionControl.markAsTouched();
        wizardComponent.descriptionControl.updateValueAndValidity();
        expect(wizardComponent.descriptionControl.hasError("required")).toBe(true);
      });

      it("does not set required validator if description is not required", () => {
        // Remove require_description
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["totp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        wizardFixture.detectChanges();
        wizardComponent.setDescriptionValidators();
        wizardFixture.detectChanges();
        expect(wizardComponent.descriptionRequired()).toBe(false);
        expect(wizardComponent.descriptionControl.hasValidator(Validators.required)).toBe(false);
        wizardComponent.descriptionControl.setValue("");
        wizardComponent.descriptionControl.markAsTouched();
        wizardComponent.descriptionControl.updateValueAndValidity();
        expect(wizardComponent.descriptionControl.hasError("required")).toBe(false);
      });

      it("shows description input only if description is required", () => {
        // Description required
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: ["hotp"],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        wizardFixture.detectChanges();
        expect(wizardFixture.nativeElement.querySelector("mat-form-field.description-form")).not.toBeNull();

        // Description not required
        authServiceMock.authData.set({
          ...authServiceMock.authData()!,
          require_description: [],
          token_wizard: true,
          default_tokentype: "hotp"
        });
        wizardFixture.detectChanges();
        expect(wizardFixture.nativeElement.querySelector("mat-form-field.description-form")).toBeNull();
      });
    });
  });
});
