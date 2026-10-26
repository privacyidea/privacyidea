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
import { provideRouter } from "@angular/router";
import { ConfigService } from "@services/config/config.service";
import { RecoverService } from "@services/recover/recover.service";
import { MockRecoverService } from "@testing/mock-services";
import { MockConfigService } from "@testing/mock-services/mock-config-service";
import { throwError } from "rxjs";
import { PasswordRecoveryRequestComponent } from "./password-recovery-request.component";

describe("PasswordRecoveryRequestComponent", () => {
  let fixture: ComponentFixture<PasswordRecoveryRequestComponent>;
  let component: PasswordRecoveryRequestComponent;
  let configService: MockConfigService;
  let recoverService: MockRecoverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswordRecoveryRequestComponent],
      providers: [
        provideRouter([]),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: RecoverService, useClass: MockRecoverService }
      ]
    }).compileComponents();
    configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
    recoverService = TestBed.inject(RecoverService) as unknown as MockRecoverService;
    configService.config.update((config) => ({ ...config, password_reset: true }));
    fixture = TestBed.createComponent(PasswordRecoveryRequestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("disables the submit button until the username and the email are given", () => {
    expect(component.isSubmitDisabled()).toBe(true);
    component.username.set("alice");
    expect(component.isSubmitDisabled()).toBe(true);
    component.email.set("alice@example.com");
    expect(component.isSubmitDisabled()).toBe(false);
  });

  it("offers the realms of the realm dropdown and preselects the first one", () => {
    configService.config.update((config) => ({ ...config, realms: "realm1, realm2" }));
    fixture.detectChanges();

    expect(component.realms()).toEqual(["realm1", "realm2"]);
    expect(component.realm()).toBe("realm1");
    expect(fixture.nativeElement.querySelector("mat-select")).toBeTruthy();
  });

  it("shows no realm field without a realm dropdown", () => {
    expect(fixture.nativeElement.querySelector("mat-select")).toBeNull();
  });

  it("requests the recovery email and shows the confirmation", () => {
    configService.config.update((config) => ({ ...config, realms: "realm1" }));
    component.username.set("alice");
    component.email.set("alice@example.com");

    component.onSubmit();
    fixture.detectChanges();

    expect(recoverService.requestRecoveryCode).toHaveBeenCalledWith({
      user: "alice",
      email: "alice@example.com",
      realm: "realm1"
    });
    expect(component.sent()).toBe(true);
    expect(fixture.nativeElement.textContent).toContain("alice@example.com");
  });

  it("does not send the no-realm sentinel or a cleared realm", () => {
    configService.config.update((config) => ({ ...config, realms: "-,realm1" }));
    component.username.set("alice");
    component.email.set("alice@example.com");

    component.onSubmit();

    expect(recoverService.requestRecoveryCode).toHaveBeenCalledWith({ user: "alice", email: "alice@example.com" });
  });

  it("shows the message of the server if the email cannot be sent", () => {
    recoverService.requestRecoveryCode.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 400,
            error: { result: { error: { code: 1, message: "The email does not match the users email." } } }
          })
      )
    );
    component.username.set("alice");
    component.email.set("other@example.com");

    component.onSubmit();
    fixture.detectChanges();

    expect(component.sent()).toBe(false);
    expect(component.submitting()).toBe(false);
    expect(component.errorMessage()).toBe("The email does not match the users email.");
  });

  it("does not submit an incomplete form", () => {
    component.onSubmit();
    expect(recoverService.requestRecoveryCode).not.toHaveBeenCalled();
  });

  it("points out that the password reset is not enabled once the config is loaded", () => {
    configService.config.update((config) => ({ ...config, password_reset: false }));
    component.username.set("alice");
    component.email.set("alice@example.com");
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("Resetting the password is not enabled.");
    expect(component.isSubmitDisabled()).toBe(true);
  });

  it("does not claim the password reset is disabled before the config is loaded", () => {
    configService.config.update((config) => ({ ...config, password_reset: false }));
    configService.configLoaded.set(false);
    component.username.set("alice");
    component.email.set("alice@example.com");
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain("Resetting the password is not enabled.");
    expect(component.isSubmitDisabled()).toBe(false);
  });
});
