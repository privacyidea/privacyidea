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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import {
  MockDialogService,
  MockNotificationService,
  MockSystemService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of } from "rxjs";
import { TokenRolloverComponent } from "./token-rollover.component";

describe("TokenRolloverComponent", () => {
  let component: TokenRolloverComponent;
  let fixture: ComponentFixture<TokenRolloverComponent>;
  let tokenService: MockTokenService;
  let notificationService: MockNotificationService;
  let dialogService: MockDialogService;
  let dialogRef: { close: jest.Mock };

  const mockToken = { type: "hotp", serial: "ABC123", tokentype: "hotp" };
  const mockData = { token: mockToken };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenRolloverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: UserService, useClass: MockUserService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenRolloverComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeDefined();
  });

  it("should call enrollToken and close dialog on successful rollover", async () => {
    const mockEnrollResp = MockPiResponse.fromValue<boolean>(true, {
      type: "hotp",
      serial: "ABC123",
      rollout_state: "done"
    }) as unknown as EnrollmentResponse;

    component.token.set({ type: "hotp", serial: "ABC123" });
    component.enrollmentArgsGetter = jest.fn().mockReturnValue({
      data: {} as TokenEnrollmentData,
      mapper: { map: (x: TokenEnrollmentData) => x }
    });

    const reloadSpy = jest.spyOn(tokenService.tokenDetailResource, "reload");
    tokenService.enrollToken.mockReturnValue(of(mockEnrollResp));

    await component.rolloverToken();

    expect(tokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRef.close).toHaveBeenCalled();
    expect(dialogService.openDialog).toHaveBeenCalled();

    const lastStepDialogRef = dialogService.openDialog.mock.results[0].value;
    lastStepDialogRef.close();

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should show snackbar if no token is set", async () => {
    component.token.set(null);
    await component.rolloverToken();
    expect(notificationService.warning).toHaveBeenCalledWith("No token selected for rollover.");
  });

  it("should show snackbar if enrollmentArgsGetter is missing", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    component.enrollmentArgsGetter = undefined;
    await component.rolloverToken();
    expect(notificationService.warning).toHaveBeenCalledWith(
      "Rollover action is not available for the selected token type."
    );
  });

  it("updateAdditionalFormFields keeps dialog actions enabled (child handles its own validation)", () => {
    component.updateAdditionalFormFields();
    fixture.detectChanges();

    expect(component.formGroupInvalid()).toBe(false);
    expect(component.dialogActions()).toEqual([expect.objectContaining({ disabled: false })]);
  });
});
