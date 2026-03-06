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
import { VerifyEnrollmentComponent } from "./verify-enrollment.component";
import { MockTokenService } from "src/testing/mock-services/mock-token-service";
import { NotificationService } from "../../../../../services/notification/notification.service";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { of } from "rxjs";
import { MockNotificationService } from "../../../../../../testing/mock-services";
import { TokenService } from "../../../../../services/token/token.service";

describe("VerifyEnrollmentComponent", () => {
  let component: VerifyEnrollmentComponent;
  let fixture: ComponentFixture<VerifyEnrollmentComponent>;
  let tokenService: MockTokenService;
  let notificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VerifyEnrollmentComponent, FormsModule, ReactiveFormsModule],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(VerifyEnrollmentComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call verifyToken and reload on verifyOTP", () => {
    component.otpControl.setValue("123456");
    component.verifyOTP();
    expect(tokenService.verifyToken).toHaveBeenCalledWith({
      serial: tokenService.tokenSerial(),
      type: tokenService.selectedTokenType().key,
      verify: "123456"
    });
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Token verified successfully!"));
  });

  it("should not call openSnackBar if rollout_state is not enrolled", () => {
    jest.spyOn(tokenService, "verifyToken").mockReturnValue(of({
      detail: { serial: "ABC123", rollout_state: "pending" },
      result: { status: true }
    }));
    const snackSpy = jest.spyOn(notificationService, "openSnackBar");
    component.otpControl.setValue("654321");
    component.verifyOTP();
    expect(snackSpy).not.toHaveBeenCalled();
  });

  it("should disable button if otpControl is invalid", () => {
    component.otpControl.setValue("");
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector("button");
    expect(button.disabled).toBe(true);
  });
});
