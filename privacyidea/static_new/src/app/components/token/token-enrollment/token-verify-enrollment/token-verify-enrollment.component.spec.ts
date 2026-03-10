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

import { TokenVerifyEnrollmentComponent } from "./token-verify-enrollment.component";
import { MockTokenService } from "src/testing/mock-services/mock-token-service";
import { MockContentService } from "src/testing/mock-services/mock-content-service";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NO_ERRORS_SCHEMA } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";
import { TokenService } from "../../../../services/token/token.service";
import { of } from "rxjs";
import { ContentService } from "../../../../services/content/content.service";

describe("TokenVerifyEnrollmentComponent", () => {
  let component: TokenVerifyEnrollmentComponent;
  let fixture: ComponentFixture<TokenVerifyEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123", verify: { message: "Enter OTP" } }, type: "hotp" },
    enrollParameters: { data: {} }
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenVerifyEnrollmentComponent],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should disable verify action if input is invalid", () => {
    component.verifyOTPControl.setValue("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("should enable verify action if input is valid", () => {
    component.verifyOTPControl.setValue("123456");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should call verifyToken and close dialog on successful verify", () => {
    component.verifyOTPControl.setValue("123456");
    component.onDialogAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  it("should not close dialog if rollout_state is not enrolled", () => {
    mockTokenService.verifyToken = jest.fn().mockReturnValue(of({
      result: { status: true },
      detail: { rollout_state: "client_wait", serial: "123", type: "hotp" },
      type: "hotp"
    }));
    component.verifyOTPControl.setValue("123456");
    component.onDialogAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it("should close dialog on switch route", () => {
    component.onSwitchRoute();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });
});
