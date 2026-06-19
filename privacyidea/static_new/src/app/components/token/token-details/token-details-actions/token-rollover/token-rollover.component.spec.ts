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
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import {
  MockDialogService,
  MockNotificationService,
  MockSystemService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { of } from "rxjs";
import { TokenRolloverComponent } from "./token-rollover.component";
import { UserService } from "@services/user/user.service";
import { SystemService } from "@services/system/system.service";

// Mock token enroll strategy
function installStrategy(component: TokenRolloverComponent, strategy: unknown): void {
  Object.defineProperty(component, "enrollSwitch", {
    value: () => ({ currentStrategy: () => strategy }),
    configurable: true
  });
}

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
    const mockEnrollResp = {
      result: { status: true },
      detail: { rollout_state: "done", serial: "ABC123", verify: false }
    };

    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, {
      buildEnrollmentArgs: jest.fn().mockReturnValue({
        data: {},
        mapper: { map: (x: unknown) => x }
      })
    });

    const reloadSpy = jest.spyOn(tokenService.tokenDetailResource, "reload");
    tokenService.enrollToken.mockReturnValue(of(mockEnrollResp as unknown as EnrollmentResponse));

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

  it("should show snackbar if no strategy is available", async () => {
    component.token.set({ type: "hotp", serial: "ABC123" });
    installStrategy(component, undefined);
    await component.rolloverToken();
    expect(notificationService.warning).toHaveBeenCalledWith(
      "Rollover action is not available for the selected token type."
    );
  });

  describe("handleCompleteEnrollment", () => {
    it("opens the complete-enrollment dialog when rollout_state is 'clientwait' and forwards the result to verify", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { rollout_state: "clientwait", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const completeResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const afterClosed = jest.fn().mockReturnValue(of(completeResponse));
      dialogService.openDialog.mockReturnValue({ afterClosed } as unknown as MatDialogRef<unknown>);

      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const verifySpy = jest.spyOn(component, "handleVerifyEnrollment").mockImplementation(() => undefined);

      component.handleCompleteEnrollment(enrollResponse);

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ response: enrollResponse })
        })
      );
      expect(verifySpy).toHaveBeenCalledWith(completeResponse);
      expect(component.enrolledDialogData()?.showEnrollData).toBe(false);
    });

    it("skips the dialog and routes directly to verify when rollout_state is not 'clientwait'", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const verifySpy = jest.spyOn(component, "handleVerifyEnrollment").mockImplementation(() => undefined);

      component.handleCompleteEnrollment(enrollResponse);

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(verifySpy).toHaveBeenCalledWith(enrollResponse);
    });
  });

  describe("handleVerifyEnrollment", () => {
    it("opens the verify dialog when the response requires verification and finalizes with the closed result", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { verify: { message: "type the OTP" }, serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const verifiedResponse = {
        result: { status: true },
        detail: { rollout_state: "enrolled", serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      const afterClosed = jest.fn().mockReturnValue(of(verifiedResponse));
      dialogService.openDialog.mockReturnValue({ afterClosed } as unknown as MatDialogRef<unknown>);

      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const finalizeSpy = jest
        .spyOn(component as unknown as { _handleEnrollmentResponse: () => void }, "_handleEnrollmentResponse")
        .mockImplementation(() => undefined);

      component.handleVerifyEnrollment(enrollResponse);

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ response: enrollResponse })
        })
      );
      expect(finalizeSpy).toHaveBeenCalledWith(verifiedResponse);
      expect(component.enrollResponse()).toEqual(verifiedResponse);
    });

    it("skips the verify dialog when no verification is required", () => {
      const enrollResponse = {
        result: { status: true },
        detail: { serial: "ABC123" }
      } as unknown as EnrollmentResponse;
      component.enrolledDialogData.set({
        response: enrollResponse,
        enrollParameters: {} as never,
        tokenType: "hotp",
        rollover: true
      });
      const finalizeSpy = jest
        .spyOn(component as unknown as { _handleEnrollmentResponse: () => void }, "_handleEnrollmentResponse")
        .mockImplementation(() => undefined);

      component.handleVerifyEnrollment(enrollResponse);

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(finalizeSpy).toHaveBeenCalledWith(enrollResponse);
    });
  });
});
