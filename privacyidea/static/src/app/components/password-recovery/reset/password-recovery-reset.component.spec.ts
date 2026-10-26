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
          useValue: { snapshot: { paramMap: convertToParamMap({ user: "alice@realm1", code: "abc123" }) } }
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

  it("disables the submit button until both passwords are given and equal", () => {
    expect(component.isSubmitDisabled()).toBe(true);
    component.password.set("secret");
    expect(component.isSubmitDisabled()).toBe(true);
    component.repeatPassword.set("other");
    expect(component.isSubmitDisabled()).toBe(true);
    expect(component.passwordMismatch()).toBe(true);
    component.repeatPassword.set("secret");
    expect(component.isSubmitDisabled()).toBe(false);
    expect(component.mismatchMessage()).toBe("");
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
