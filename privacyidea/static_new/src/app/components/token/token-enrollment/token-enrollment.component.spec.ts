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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { TokenEnrollmentComponent } from "./token-enrollment.component";
import { UserService } from "../../../services/user/user.service";
import {
  MockContainerService,
  MockContentService,
  MockDialogService,
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
import { FormControl, FormGroup } from "@angular/forms";
import { lastValueFrom, of, throwError } from "rxjs";
import { signal } from "@angular/core";
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

describe("TokenEnrollmentComponent", () => {
  let fixture: ComponentFixture<TokenEnrollmentComponent>;
  let component: TokenEnrollmentComponent;
  let selfFixture: ComponentFixture<TokenEnrollmentSelfServiceComponent>;
  let selfComponent: TokenEnrollmentSelfServiceComponent;

  let tokenSvc: MockTokenService;
  let userSvc: MockUserService;
  let notifications: MockNotificationService;
  let dialog: MockDialogService;
  let authService: MockAuthService;
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

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    userSvc = TestBed.inject(UserService) as unknown as MockUserService;
    notifications = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockVersioningService = TestBed.inject(VersioningService) as unknown as MockVersioningService;
    dialog = TestBed.inject(DialogService) as unknown as MockDialogService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
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
    tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "HOTP" });
    expect(component.isUserRequired).toBe(false);

    tokenSvc.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "WebAuthn" });
    expect(component.isUserRequired).toBe(true);

    tokenSvc.selectedTokenType.set({ key: "passkey", name: "Passkey", info: "", text: "Passkey" });
    expect(component.isUserRequired).toBe(true);

    tokenSvc.selectedTokenType.set({ key: "certificate", name: "Certificate", info: "", text: "Cert" });
    expect(component.isUserRequired).toBe(true);
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
      (tokenSvc.selectedTokenType as any).set("");

      await (component as any).enrollToken();

      expect(notifications.openSnackBar).toHaveBeenCalledWith("Please select a token type.");
    });

    it("snacks when user is required but missing", async () => {
      tokenSvc.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      userSvc.selectedUser.set(null);

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("1234");
      component.selectedUserRealmControl.setValue("realm1");
      component.userFilterControl.setValue("alice");

      await (component as any).enrollToken();

      expect(notifications.openSnackBar).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when form is invalid (e.g., PIN mismatch)", async () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      userSvc.selectedUser.set(null);

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("9999");

      await (component as any).enrollToken();

      expect(notifications.openSnackBar).toHaveBeenCalledWith(
        "Please fill in all required fields or correct invalid entries."
      );
    });

    it("snacks when clickEnroll is not provided", async () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });

      component.setPinControl.setValue("1234");
      component.repeatPinControl.setValue("1234");

      component.enrollmentArgsGetter = undefined;

      await component.enrollToken();

      expect(notifications.openSnackBar).toHaveBeenCalledWith(
        "Enrollment action is not available for the selected token type."
      );
    });

    it("calls clickEnroll, sets enrollResponse, opens last step dialog", async () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.descriptionControl.setValue("desc");
      component.setPinControl.setValue("0000");
      component.repeatPinControl.setValue("0000");
      component.selectedContainerControl.setValue("CONT-1");
      component.selectedUserRealmControl.setValue("");

      const response = { detail: { rollout_state: "done" } } as any;

      const enrollmentArgsGetterFn = jest.fn().mockReturnValue(of(response));
      component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);
      const onEnrollmentResponseFn = jest.fn().mockReturnValue(lastValueFrom(of(response)));
      component.updateOnEnrollmentResponse(onEnrollmentResponseFn);

      const spyOpen = jest.spyOn(component as any, "openLastStepDialog");

      await component.enrollToken();

      expect(enrollmentArgsGetterFn).toHaveBeenCalledTimes(1);
      expect(component.enrollResponse()).toBe(response);
      expect(spyOpen).toHaveBeenCalledWith({ response, user: null });
    });

    it("handles clickEnroll rejection by showing error snack", async () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.setPinControl.setValue("1111");
      component.repeatPinControl.setValue("1111");

      const error = { error: { result: { error: { message: "nope" } } } };
      const enrollmentArgsGetterFn = jest.fn().mockReturnValue({});
      component.updateEnrollmentArgsGetter(enrollmentArgsGetterFn);
      tokenSvc.enrollToken.mockReturnValue(Promise.reject(error));

      await component.enrollToken().catch(() => undefined);

      expect(notifications.openSnackBar).toHaveBeenCalledWith("Failed to enroll token: nope");
    });

    it("does NOT open dialog if rollout_state is 'clientwait'", async () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      component.setPinControl.setValue("0000");
      component.repeatPinControl.setValue("0000");
      TestBed.flushEffects();

      const response = { detail: { rollout_state: "clientwait" } } as any;
      tokenSvc.enrollToken.mockReturnValue(of(response));

      const spyOpen = jest.spyOn(component as any, "openLastStepDialog");

      await component.enrollToken();

      expect(spyOpen).not.toHaveBeenCalled();
    });

    it("_handleEnrollmentResponse snacks when user is required but missing", () => {
      tokenSvc.selectedTokenType.set({ key: "webauthn", name: "Webauthn", info: "", text: "" });
      (component as any)._handleEnrollmentResponse({
        response: { detail: { rollout_state: "done" } } as any,
        user: null
      });

      expect(notifications.openSnackBar).toHaveBeenCalledWith(
        "User is required for this token type, but no user was provided."
      );
    });
  });

  describe("open/reopen dialog flows", () => {
    it("openLastStepDialog: snacks when response is null", () => {
      (component as any).openLastStepDialog({ response: null, user: null });
      expect(notifications.openSnackBar).toHaveBeenCalledWith("No enrollment response available.");
    });

    it("openLastStepDialog: stores last-step data and opens dialog", () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      const response = { detail: {} } as any;
      (component as any).openLastStepDialog({ response, user: null });

      expect(dialog.openTokenEnrollmentLastStepDialog).toHaveBeenCalledTimes(1);
      const callArg = (dialog.openTokenEnrollmentLastStepDialog as jest.Mock).mock.calls[0][0];
      expect(callArg.data.response).toBe(response);

      expect(component._lastTokenEnrollmentLastStepDialogData()).toBeTruthy();
    });

    it("reopenEnrollmentDialog: uses reopen function when provided", () => {
      const fn = jest.fn().mockReturnValue(of(null));
      component.updateReopenDialog(fn);
      component.reopenEnrollmentDialog();

      expect(fn).toHaveBeenCalledTimes(1);
      expect(dialog.openTokenEnrollmentLastStepDialog).not.toHaveBeenCalled();
    });

    it("reopenEnrollmentDialog: falls back to last-step data", () => {
      tokenSvc.selectedTokenType.set({ key: "hotp", name: "HOTP", info: "", text: "" });
      (component as any)._lastTokenEnrollmentLastStepDialogData.set({
        tokentype: tokenSvc.selectedTokenType(),
        response: {},
        serial: signal(null),
        enrollToken: () => Promise.resolve(null),
        user: null,
        userRealm: "",
        onlyAddToRealm: false
      } as any);

      component.reopenEnrollmentDialog();
      expect(dialog.openTokenEnrollmentLastStepDialog).toHaveBeenCalledTimes(1);
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
      authService.authData.set({
        ...authService.authData()!,
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
      authService.authData.set({
        ...authService.authData()!,
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
  });
});
