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
import { PlatformLocation } from "@angular/common";
import { HttpErrorResponse } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NotificationService } from "@services/notification/notification.service";
import { RecoverService } from "@services/recover/recover.service";
import { MockNotificationService, MockPiResponse, MockRecoverService } from "@testing/mock-services";
import { of, throwError } from "rxjs";
import { PasswordRecoveryResetComponent, splitUserAndRealm } from "./password-recovery-reset.component";

describe("splitUserAndRealm", () => {
  it("splits at the last @", () => {
    expect(splitUserAndRealm("alice@realm1")).toEqual({ user: "alice", realm: "realm1" });
    expect(splitUserAndRealm("alice@example.com@realm1")).toEqual({ user: "alice@example.com", realm: "realm1" });
  });

  it("keeps a login name without realm", () => {
    expect(splitUserAndRealm("alice")).toEqual({ user: "alice" });
    expect(splitUserAndRealm("@realm1")).toEqual({ user: "@realm1" });
  });
});

describe("PasswordRecoveryResetComponent", () => {
  let fixture: ComponentFixture<PasswordRecoveryResetComponent>;
  let component: PasswordRecoveryResetComponent;
  let recoverService: MockRecoverService;
  let notificationService: MockNotificationService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswordRecoveryResetComponent],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ user: "alice@realm1" }), fragment: "abc123" } }
        },
        { provide: RecoverService, useClass: MockRecoverService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();
    recoverService = TestBed.inject(RecoverService) as unknown as MockRecoverService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    fixture = TestBed.createComponent(PasswordRecoveryResetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("removes the recovery code from the address bar", () => {
    const platformLocation = TestBed.inject(PlatformLocation);
    platformLocation.replaceState({}, "", "/app/v2/reset/alice@realm1?foo=bar#abc123");
    expect(platformLocation.hash).toBe("#abc123");

    TestBed.createComponent(PasswordRecoveryResetComponent);

    expect(platformLocation.hash).toBe("");
    expect(platformLocation.pathname).toBe("/app/v2/reset/alice@realm1");
    expect(platformLocation.search).toBe("?foo=bar");
  });

  it("disables the submit button until both passwords are given and equal", () => {
    expect(component.isSubmitDisabled()).toBe(true);
    component.password.set("secret");
    expect(component.isSubmitDisabled()).toBe(true);
    component.repeatPassword.set("other");
    expect(component.isSubmitDisabled()).toBe(true);
    expect(component.passwordMismatch()).toBe(true);
    component.repeatPassword.set("secret");
    expect(component.isSubmitDisabled()).toBe(false);
    expect(component.passwordMismatch()).toBe(false);
  });

  it("shows why the passwords are not accepted", () => {
    component.password.set("secret");
    component.repeatPassword.set("other");
    component.repeatPasswordField().markAsTouched();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("The passwords do not match.");

    component.repeatPassword.set("secret");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
  });

  it("asks for the new password in password inputs a password manager recognizes", () => {
    const inputs: HTMLInputElement[] = Array.from(fixture.nativeElement.querySelectorAll("input"));
    expect(inputs.map((input) => input.type)).toEqual(["password", "password"]);
    expect(inputs.map((input) => input.autocomplete)).toEqual(["new-password", "new-password"]);

    component.hidePassword.set(false);
    fixture.detectChanges();
    expect(inputs.map((input) => input.type)).toEqual(["text", "text"]);
  });

  it("sets the password with the user, realm and code of the link and goes to the login page", () => {
    component.password.set("secret");
    component.repeatPassword.set("secret");

    component.onSubmit();

    expect(recoverService.resetPassword).toHaveBeenCalledWith({
      user: "alice",
      realm: "realm1",
      recoverycode: "abc123",
      password: "secret"
    });
    expect(notificationService.success).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.LOGIN);
  });

  it("does not submit different passwords", () => {
    component.password.set("secret");
    component.repeatPassword.set("other");

    component.onSubmit();

    expect(recoverService.resetPassword).not.toHaveBeenCalled();
  });

  it("reports an invalid or expired code", () => {
    recoverService.resetPassword.mockReturnValue(of(MockPiResponse.fromValue(false)));
    component.password.set("secret");
    component.repeatPassword.set("secret");

    component.onSubmit();

    expect(component.errorMessage()).toContain("invalid or has expired");
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.submitting()).toBe(false);
  });

  it("shows the message of the server on an error", () => {
    recoverService.resetPassword.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 403,
            error: { result: { error: { code: 303, message: "Not allowed" } } }
          })
      )
    );
    component.password.set("secret");
    component.repeatPassword.set("secret");

    component.onSubmit();

    expect(component.errorMessage()).toBe("Not allowed");
    expect(component.submitting()).toBe(false);
  });
});

describe("PasswordRecoveryResetComponent with a link without code", () => {
  let component: PasswordRecoveryResetComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswordRecoveryResetComponent],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ user: "alice@realm1" }), fragment: null } }
        },
        { provide: RecoverService, useClass: MockRecoverService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();
    component = TestBed.createComponent(PasswordRecoveryResetComponent).componentInstance;
  });

  it("explains the problem and does not accept a password", () => {
    component.password.set("secret");
    component.repeatPassword.set("secret");

    expect(component.errorMessage()).toContain("The link is incomplete");
    expect(component.isSubmitDisabled()).toBe(true);
  });
});
