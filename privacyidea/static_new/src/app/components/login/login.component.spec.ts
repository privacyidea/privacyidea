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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { Router } from "@angular/router";
import { of, throwError } from "rxjs";
import {
  MockAuthDetail,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockSessionTimerService,
  MockValidateService
} from "../../../testing/mock-services";
import { AuthData, AuthDetail, AuthService } from "../../services/auth/auth.service";
import { LocalService } from "../../services/local/local.service";
import { NotificationService } from "../../services/notification/notification.service";
import { SessionTimerService } from "../../services/session-timer/session-timer.service";
import { ValidateService } from "../../services/validate/validate.service";
import { LoginComponent } from "./login.component";
import { ROUTE_PATHS } from "../../route_paths";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { ConfigService } from "../../services/config/config.service";
import { By } from "@angular/platform-browser";
import { MockConfigService } from "../../../testing/mock-services/mock-config-service";

describe("LoginComponent", () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let authService: MockAuthService;
  let localService: MockLocalService;
  let configService: MockConfigService;
  let notificationService: MockNotificationService;
  let sessionTimerService: MockSessionTimerService;
  let validateService: MockValidateService;
  let router: jest.Mocked<Router>;

  beforeEach(async () => {
    const routerMock = {
      navigateByUrl: jest.fn().mockResolvedValue(true),
      navigate: jest.fn().mockResolvedValue(true)
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: LocalService, useClass: MockLocalService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: SessionTimerService, useClass: MockSessionTimerService },
        { provide: Router, useValue: routerMock },
        { provide: ConfigService, useClass: MockConfigService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    // Use a double cast to inform TypeScript that we know the injected service is a mock.
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    localService = TestBed.inject(LocalService) as unknown as MockLocalService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    sessionTimerService = TestBed.inject(SessionTimerService) as unknown as MockSessionTimerService;
    validateService = TestBed.inject(ValidateService) as unknown as MockValidateService;
    configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
    router = TestBed.inject(Router) as jest.Mocked<Router>;

    // Default setup for most tests (not logged in)
    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("when already logged in", () => {
    it("should warn and open a snack bar on initialization", () => {
      authService.isAuthenticated.set(true);
      const warn = jest.spyOn(console, "warn").mockImplementation();

      // Re-run constructor logic by creating a new component with the new state
      const loggedInFixture = TestBed.createComponent(LoginComponent);
      loggedInFixture.detectChanges();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith("User is already logged in.");
      expect(warn).toHaveBeenCalledWith("User is already logged in.");

      warn.mockRestore();
    });
  });

  describe("wizard", () => {
    beforeEach(() => {
      component.username.set("test-user");
      component.password.set("test-pass");
    });

    it("should redirect to token wizard", () => {
      authService.authData.set({
        ...authService.authData()!,
        token_wizard: true
      });
      component.onSubmit();

      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_WIZARD);
    });

    it("should redirect to token wizard first if token and container wizard are enabled", () => {
      authService.authData.set({
        ...authService.authData()!,
        token_wizard: true,
        container_wizard: { enabled: true, type: "smartphone", registration: false, template: null }
      });
      component.onSubmit();

      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_WIZARD);
    });

    it("should redirect to container wizard if only container wizard is enabled", () => {
      authService.authData.set({
        ...authService.authData()!,
        token_wizard: false,
        container_wizard: { enabled: true, type: "smartphone", registration: false, template: null }
      });
      component.onSubmit();

      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);
    });
  });

  describe("onSubmit", () => {
    beforeEach(() => {
      component.username.set("test-user");
      component.password.set("test-pass");
    });

    it("should call authService.authenticate with username/password", () => {
      component.onSubmit();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "test-pass"
      });
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS);
    });

    it("should call authService.authenticate with username/password/realm", () => {
      component.realm.set("test-realm");
      component.onSubmit();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "test-pass",
        realm: "test-realm"
      });
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS);
    });

    it("should call authService.authenticate not with empty realm", () => {
      component.realm.set("");
      component.onSubmit();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "test-pass"
      });
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS);
    });

    it("should handle a complex multi-challenge response with WebAuthn and OTP", () => {
      const webAuthnSignRequestData = {
        allowCredentials: [
          {
            id: "sLGtMkbtYaEl2sYAD4iDdsVRUyihBfPBDhkVQemXUujuLE2G7WdSO5sb0IfGE-dwsABqT00mcqR9oTntiP0mEQ",
            transports: ["usb", "internal", "nfc", "ble"],
            type: "public-key"
          }
        ],
        challenge: "AiHIAWAv283XqtFFlyzmfdQwzevsDLHKdiHrt6iUiA8",
        rpId: "fritz.box",
        timeout: 60000,
        userVerification: "discouraged"
      };

      const multiChallengeResponse = new MockPiResponse<AuthData, AuthDetail>({
        detail: {
          transaction_id: "02247192477167467513",
          multi_challenge: [
            {
              client_mode: "interactive",
              message: "please enter otp: ",
              serial: "OATH0000719A",
              transaction_id: "02247192477167467513",
              type: "hotp"
            },
            {
              client_mode: "interactive",
              message: "please enter otp: ",
              serial: "OATH000545CD",
              transaction_id: "02247192477167467513",
              type: "hotp"
            },
            {
              attributes: { webAuthnSignRequest: webAuthnSignRequestData },
              client_mode: "webauthn",
              message: "Please confirm with your WebAuthn token (Generic WebAuthn Token)",
              serial: "WAN0002E3AE",
              transaction_id: "02247192477167467513",
              type: "webauthn"
            }
          ]
        },
        result: { authentication: "CHALLENGE", status: true, value: false as any }
      });
      authService.authenticate.mockReturnValue(of(multiChallengeResponse));

      component.onSubmit();
      // "please enter otp:" is not duplicated
      expect(component.authMessage()).toEqual([
        "please enter otp: ",
        "Please confirm with your WebAuthn token (Generic WebAuthn Token)"
      ]);
      expect(component.showOtpField()).toBe(true);
      expect(component.webAuthnTriggered()).toEqual(webAuthnSignRequestData);
      expect((component as any).transactionId).toBe("02247192477167467513");
      expect(component.pushTriggered()).toBe(false); // No push challenge in this specific multi_challenge

      expect(localService.saveData).not.toHaveBeenCalled();
      expect(sessionTimerService.startRefreshingRemainingTime).not.toHaveBeenCalled();
      expect(sessionTimerService.startTimer).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should handle a challenge response", () => {
      const challengeResponse = new MockPiResponse<AuthData, AuthDetail>({
        detail: { message: "Please enter OTP" }, // Use detail.message for simple cases
        result: { authentication: "CHALLENGE", status: true, value: false as any }
      });
      authService.authenticate.mockReturnValue(of(challengeResponse));

      component.onSubmit();

      expect(component.authMessage()).toEqual(["Please enter OTP"]); // Now this assertion is correct
      expect(component.showOtpField()).toBe(true);
      expect(localService.saveData).not.toHaveBeenCalled();
      expect(sessionTimerService.startRefreshingRemainingTime).not.toHaveBeenCalled();
      expect(sessionTimerService.startTimer).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should submit otp and transaction_id on challenge response", () => {
      // GIVEN: The component is in a challenge state
      component.showOtpField.set(true);
      component.otp.set("654321");
      (component as any).transactionId = "tx123";

      // WHEN: The form is submitted
      component.onSubmit();

      // THEN: The correct parameters are sent
      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "654321",
        transaction_id: "tx123"
      });
    });

    it("should handle a failed login", () => {
      const errorResponse = {
        error: {
          result: {
            error: { message: "Invalid credentials" }
          }
        }
      };
      authService.authenticate.mockReturnValue(throwError(() => errorResponse));

      component.onSubmit();

      expect(component.errorMessage()).toBe("Invalid credentials");
      expect(component.password()).toBe(""); // Password field should be cleared
    });

    it("should toggle password visibility", () => {
      // GIVEN: The password field is initially hidden
      expect(component.hidePassword()).toBe(true);
      const passwordInput = fixture.debugElement.query(By.css("#password")).nativeElement;
      expect(passwordInput.type).toBe("password");

      // WHEN: Clicking the visibility toggle button
      const toggleButton = fixture.debugElement.query(By.css("button[matSuffix]"));
      toggleButton.nativeElement.click();
      fixture.detectChanges();

      // THEN: The password field should be visible
      expect(component.hidePassword()).toBe(false);
      expect(passwordInput.type).toBe("text");

      // AND: Clicking it again should hide it
      toggleButton.nativeElement.click();
      fixture.detectChanges();
      expect(component.hidePassword()).toBe(true);
      expect(passwordInput.type).toBe("password");
    });

    it("should reset password visibility on login reset", () => {
      // GIVEN: password visibility is toggled to show
      component.hidePassword.set(false);
      fixture.detectChanges();
      expect(fixture.debugElement.query(By.css("#password")).nativeElement.type).toBe("text");

      // WHEN: Resetting the login
      component.resetLogin();
      fixture.detectChanges();

      // THEN: password visibility should be reset to hidden
      expect(component.hidePassword()).toBe(true);
      expect(fixture.debugElement.query(By.css("#password")).nativeElement.type).toBe("password");
    });

    it("should reset password visibility on login error", () => {
      // GIVEN: password visibility is toggled to show
      component.hidePassword.set(false);
      fixture.detectChanges();
      expect(fixture.debugElement.query(By.css("#password")).nativeElement.type).toBe("text");

      // AND: Auth fails
      const errorResponse = { error: { result: { error: { message: "Invalid credentials" } } } };
      authService.authenticate.mockReturnValue(throwError(() => errorResponse));

      // WHEN: Submitting login
      component.onSubmit();
      fixture.detectChanges();

      // THEN: password visibility should be reset to hidden
      expect(component.hidePassword()).toBe(true);

      // The password input stays in the DOM because showOtpField is false and useRemoteLogin is false.
      const passwordInput = fixture.debugElement.query(By.css("#password"));
      expect(passwordInput).not.toBeNull();
      expect(passwordInput.nativeElement.type).toBe("password");
    });
  });

  describe("passkeyLogin", () => {
    it("should call validateService.authenticatePasskey and handle success", () => {
      const successResponse = MockPiResponse.fromValue<AuthData, AuthDetail>({ token: "passkey-token" } as AuthData);
      jest.spyOn(validateService, "authenticatePasskey").mockReturnValue(of(successResponse));

      component.passkeyLogin();

      expect(validateService.authenticatePasskey).toHaveBeenCalled();
      expect(localService.saveData).toHaveBeenCalledWith("bearer_token", "passkey-token");
      expect(router.navigateByUrl).toHaveBeenCalledWith("/tokens");
    });

    it("should handle failure", () => {
      const errorResponse = { error: { result: { error: { message: "Passkey auth failed" } } } };
      jest.spyOn(validateService, "authenticatePasskey").mockReturnValue(throwError(() => errorResponse));

      component.passkeyLogin();

      expect(component.errorMessage()).toBe("Passkey auth failed");
    });
  });

  describe("webAuthnLogin", () => {
    it("should call validateService.authenticateWebAuthn with correct data", () => {
      const signRequest = { challenge: "abc" };
      component.webAuthnTriggered.set(signRequest);
      component.username.set("test-user");
      (component as any).transactionId = "tx-webauthn";
      const mockResponse = new MockPiResponse<AuthData, AuthDetail>({ detail: new MockAuthDetail() });
      jest.spyOn(validateService, "authenticateWebAuthn").mockReturnValue(of(mockResponse));

      component.webAuthnLogin();

      expect(validateService.authenticateWebAuthn).toHaveBeenCalledWith({
        signRequest: signRequest,
        transaction_id: "tx-webauthn",
        username: "test-user"
      });
    });

    it("should do nothing if webAuthn is not triggered", () => {
      const webAuthnSpy = jest.spyOn(validateService, "authenticateWebAuthn");
      component.webAuthnTriggered.set(null);

      component.webAuthnLogin();

      expect(webAuthnSpy).not.toHaveBeenCalled();
    });
  });

  describe("Push Polling", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    it("should start polling when a push challenge is received", async () => {
      const pollSpy = jest.spyOn(validateService, "pollTransaction").mockReturnValue(of(false));
      const challengeResponse = new MockPiResponse<AuthData, AuthDetail>({
        detail: {
          transaction_id: "tx-push",
          multi_challenge: [{ type: "push" } as any]
        },
        result: { authentication: "CHALLENGE", status: true, value: false as any }
      });
      authService.authenticate.mockReturnValue(of(challengeResponse));

      component.onSubmit();
      jest.advanceTimersByTime(1000); // Let some polling happen (5 polls at 200ms)
      await Promise.resolve();

      expect(component.pushTriggered()).toBe(true);
      expect(pollSpy).toHaveBeenCalledWith("tx-push");
      expect(pollSpy.mock.calls.length).toBeGreaterThan(1);

      component.ngOnDestroy(); // cleanup
    });

    it("should stop polling and log in on successful poll", async () => {
      jest.spyOn(validateService, "pollTransaction").mockReturnValueOnce(of(false)).mockReturnValueOnce(of(true)); // Succeed on second poll
      const successResponse = MockPiResponse.fromValue<AuthData, AuthDetail>({ token: "push-token" } as AuthData);
      authService.authenticate.mockReturnValue(of(successResponse));
      (component as any).transactionId = "tx-push-success";
      component.username.set("test-user");

      (component as any).startPushPolling();
      jest.advanceTimersByTime(500); // 2 polls at 200ms interval + buffer
      await Promise.resolve();

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "",
        transaction_id: "tx-push-success"
      });
      expect(localService.saveData).toHaveBeenCalledWith("bearer_token", "push-token");
    });
  });

  describe("logout", () => {
    it("should remove token, logout, and navigate to login", async () => {
      const authServiceSpy = jest.spyOn(authService, "logout");
      component.logout();
      fixture.whenStable().then(() => {
        expect(localService.removeData).toHaveBeenCalledWith("bearer_token");
        expect(authServiceSpy).toHaveBeenCalled();
        expect(router.navigate).toHaveBeenCalledWith(["login"]);
      });
    });
  });

  describe("Realm Selection", () => {
    it("should display realm selection if realms are provided", () => {
      configService.config.set({
        ...configService.config(),
        realms: "realm1,realm2"
      });
      fixture.detectChanges();

      expect(component.realms()).toEqual(["realm1", "realm2"]);
      expect(component.realm()).toEqual("realm1");
      const realmSelect = fixture.debugElement.query(By.css("mat-select"));
      expect(realmSelect).toBeTruthy();

      // Open the select dropdown to render options
      realmSelect.componentInstance.open();
      fixture.detectChanges();

      const options = fixture.debugElement.queryAll(By.css("mat-option"));
      expect(options.length).toBe(2);
      expect(options[0].nativeElement.textContent).toContain("realm1");
      expect(options[1].nativeElement.textContent).toContain("realm2");
    });

    it("should preselect the first realm", () => {
      configService.config.set({
        ...configService.config(),
        realms: "realmA,realmB"
      });
      fixture.detectChanges();

      expect(component.realm()).toBe("realmA");
    });

    it("should not display realm selection if realms list is empty", () => {
      configService.config.set({
        ...configService.config(),
        realms: ""
      });
      fixture.detectChanges();

      const realmSelect = fixture.debugElement.query(By.css("mat-select"));
      expect(realmSelect).toBeFalsy();
    });
  });

  describe("Remote user login", () => {
    it("should show remote user login button when remote_user is set", () => {
      configService.config.set({ ...configService.config(), remote_user: "testuser", force_remote_user: false });
      fixture.detectChanges();
      const btn = fixture.debugElement.query(By.css("button[aria-label='Remote Login Button']"));
      expect(btn).toBeTruthy();
      expect(btn.nativeElement.textContent).toContain("Log In");
    });

    it("should call remoteLogin and authenticate with remote_user", () => {
      configService.config.set({ ...configService.config(), remote_user: "testuser", force_remote_user: false });
      fixture.detectChanges();
      const authSpy = jest.spyOn(authService, "authenticate").mockReturnValue(of({ result: { status: true } }));
      const remoteLoginSpy = jest.spyOn(component, "remoteLogin");
      const btn = fixture.debugElement.query(By.css("button[aria-label='Remote Login Button']"));
      btn.nativeElement.click();
      fixture.detectChanges();
      expect(remoteLoginSpy).toHaveBeenCalled();
      expect(authSpy).toHaveBeenCalledWith({ username: "testuser" });
    });

    it("remoteLogin should show error if remote_user is not set", () => {
      configService.config.set({ ...configService.config(), remote_user: "" });
      fixture.detectChanges();
      const spy = jest.spyOn(notificationService, "openSnackBar");
      component.remoteLogin();
      expect(spy).toHaveBeenCalledWith(expect.stringContaining("Remote user not available"));
    });

    it("Login with credentials button should switch to normal login", () => {
      configService.config.set({ ...configService.config(), remote_user: "testuser", force_remote_user: false });
      fixture.detectChanges();
      expect(component.useRemoteLogin()).toBe(true);
      let btn = fixture.debugElement.query(By.css("button[aria-label='Login with credentials Button']"));
      btn.nativeElement.click();
      fixture.detectChanges();

      expect(component.useRemoteLogin()).toBe(false);
      btn = fixture.debugElement.query(By.css("button[aria-label='Login with credentials Button']"));
      expect(btn).toBeNull();
      const loginBtn = fixture.debugElement.query(By.css("button[aria-label='Login Button']"));
      expect(loginBtn).toBeTruthy();
    });

    it("should hide login with credentials button if forceRemoteUser is true", () => {
      configService.config.set({ ...configService.config(), remote_user: "testuser", force_remote_user: true });
      fixture.detectChanges();
      const btn = fixture.debugElement.query(By.css("button[aria-label='Login with credentials Button']"));
      expect(btn).toBeNull();
    });
  });
});

describe("passkeyLoginEnabled signal", () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let configService: ConfigService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [provideHttpClient(), ConfigService]
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    configService = TestBed.inject(ConfigService);
  });

  it("should be true if passkey_login is not 'hide'", () => {
    configService.config.set({
      ...configService.config(),
      passkey_login: "show"
    });
    fixture.detectChanges();
    expect(component.passkeyLoginEnabled()).toBe(true);

    configService.config.set({
      ...configService.config(),
      passkey_login: "somethingelse"
    });
    fixture.detectChanges();
    expect(component.passkeyLoginEnabled()).toBe(true);
  });

  it("should be false if passkey_login is 'hide'", () => {
    configService.config.set({
      ...configService.config(),
      passkey_login: "hide"
    });
    fixture.detectChanges();
    expect(component.passkeyLoginEnabled()).toBe(false);
  });
});
