import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, fakeAsync, TestBed, tick } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { Router } from "@angular/router";
import { of, throwError } from "rxjs";
import {
  MockAuthDetail,
  MockAuthService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockValidateService
} from "../../../testing/mock-services";
import { AuthData, AuthDetail, AuthService } from "../../services/auth/auth.service";
import { LocalService } from "../../services/local/local.service";
import { NotificationService } from "../../services/notification/notification.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { ValidateService } from "../../services/validate/validate.service";
import { LoginComponent } from "./login.component";

describe("LoginComponent", () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let authService: MockAuthService;
  let localService: MockLocalService;
  let notificationService: MockNotificationService;
  let sessionTimerService: jest.Mocked<SessionTimerServiceInterface>;
  let validateService: MockValidateService;
  let router: jest.Mocked<Router>;

  beforeEach(async () => {
    // Mock for SessionTimerService as it's not in mock-services.ts
    const sessionTimerServiceMock = {
      startRefreshingRemainingTime: jest.fn(),
      startTimer: jest.fn(),
      resetTimer: jest.fn()
    };

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
        { provide: SessionTimerService, useValue: sessionTimerServiceMock },
        { provide: Router, useValue: routerMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    // Use a double cast to inform TypeScript that we know the injected service is a mock.
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    localService = TestBed.inject(LocalService) as unknown as MockLocalService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    sessionTimerService = TestBed.inject(SessionTimerService) as unknown as jest.Mocked<SessionTimerServiceInterface>;
    validateService = TestBed.inject(ValidateService) as unknown as MockValidateService;
    router = TestBed.inject(Router) as jest.Mocked<Router>;
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("should warn and open a snack bar if the user is already logged in", () => {
    authService.acceptAuthentication();
    const warn = jest.spyOn(console, "warn").mockImplementation();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(notificationService.openSnackBar).toHaveBeenCalledWith("User is already logged in.");
    expect(warn).toHaveBeenCalledWith("User is already logged in.");

    warn.mockRestore();
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
    });

    it("should handle a successful login", () => {
      const successResponse = MockPiResponse.fromValue<AuthData, AuthDetail>({ token: "fake-token" } as AuthData);
      authService.authenticate.mockReturnValue(of(successResponse));

      component.onSubmit();

      expect(localService.saveData).toHaveBeenCalledWith("mockBearerTokenKey", "fake-token");
      expect(sessionTimerService.startRefreshingRemainingTime).toHaveBeenCalled();
      expect(sessionTimerService.startTimer).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith("/tokens");
    });

    it("should handle a challenge response", () => {
      const challengeResponse = new MockPiResponse<AuthData, AuthDetail>({
        detail: { messages: ["Please enter OTP"] },
        result: { authentication: "CHALLENGE", status: true, value: false as any }
      });
      authService.authenticate.mockReturnValue(of(challengeResponse));

      component.onSubmit();

      expect(component.loginMessage()).toEqual(["Please enter OTP"]);
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
  });

  describe("passkeyLogin", () => {
    it("should call validateService.authenticatePasskey and handle success", () => {
      const successResponse = MockPiResponse.fromValue<AuthData, AuthDetail>({ token: "passkey-token" } as AuthData);
      jest.spyOn(validateService, "authenticatePasskey").mockReturnValue(of(successResponse));

      component.passkeyLogin();

      expect(validateService.authenticatePasskey).toHaveBeenCalled();
      expect(localService.saveData).toHaveBeenCalledWith("mockBearerTokenKey", "passkey-token");
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
    it("should start polling when a push challenge is received", fakeAsync(() => {
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
      tick(1000); // Let some polling happen (5 polls at 200ms)

      expect(component.pushTriggered()).toBe(true);
      expect(pollSpy).toHaveBeenCalledWith("tx-push");
      expect(pollSpy.mock.calls.length).toBeGreaterThan(1);

      component.ngOnDestroy(); // cleanup
    }));

    it("should stop polling and log in on successful poll", fakeAsync(() => {
      jest.spyOn(validateService, "pollTransaction").mockReturnValueOnce(of(false)).mockReturnValueOnce(of(true)); // Succeed on second poll
      const successResponse = MockPiResponse.fromValue<AuthData, AuthDetail>({ token: "push-token" } as AuthData);
      authService.authenticate.mockReturnValue(of(successResponse));
      (component as any).transactionId = "tx-push-success";
      component.username.set("test-user");

      (component as any).startPushPolling();
      tick(500); // 2 polls at 200ms interval + buffer

      expect(authService.authenticate).toHaveBeenCalledWith({
        username: "test-user",
        password: "",
        transaction_id: "tx-push-success"
      });
      expect(localService.saveData).toHaveBeenCalledWith("mockBearerTokenKey", "push-token");
    }));
  });

  describe("logout", () => {
    it("should remove token, logout, and navigate to login", async () => {
      component.logout();
      await fixture.whenStable(); // Wait for router.navigate promise
      expect(localService.removeData).toHaveBeenCalledWith("mockBearerTokenKey");
      expect(authService.logout).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(["login"]);
    });
  });
});
