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
import { MatDialogRef } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPiResponse, MockRouter } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockNotificationService } from "@testing/mock-services/mock-notification-service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { of } from "rxjs";
import { PoliciesTableActionsComponent } from "./policies-table-actions.component";

describe("PoliciesTableActionsComponent", () => {
  let component: PoliciesTableActionsComponent;
  let fixture: ComponentFixture<PoliciesTableActionsComponent>;
  let dialogService: MockDialogService;
  let policyService: MockPolicyService;
  let notificationService: MockNotificationService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesTableActionsComponent],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: Router, useClass: MockRouter }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PoliciesTableActionsComponent);
    component = fixture.componentInstance;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    router = TestBed.inject(Router);
    fixture.componentRef.setInput("policySelection", [{ name: "policy1" } as PolicyDetail]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should navigate to new policy page on createNewPolicy", () => {
    component.createNewPolicy();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_NEW);
  });

  it("should call delete on confirmed policies", async () => {
    jest
      .spyOn(dialogService, "openDialog")
      .mockReturnValue({ afterClosed: () => of(true) } as unknown as MatDialogRef<AbstractDialogComponent<unknown, unknown>, unknown>);
    const spy = jest.spyOn(policyService, "deletePolicy");
    await component.deleteSelectedPolicies();
    expect(spy).toHaveBeenCalledWith("policy1");
  });

  describe("copySelectedPolicies", () => {
    const closeCopyDialogWith = (newName: string | null) =>
      jest
        .spyOn(dialogService, "openDialog")
        .mockReturnValue({ afterClosed: () => of(newName) } as unknown as MatDialogRef<
          AbstractDialogComponent<unknown, unknown>,
          unknown
        >);
    const flushPromises = () => new Promise((resolve) => setTimeout(resolve));

    it("copies the policy under the name from the dialog and reports nothing on success", async () => {
      closeCopyDialogWith("policy1-copy");

      await component.copySelectedPolicies();
      await flushPromises();

      expect(policyService.copyPolicy).toHaveBeenCalledWith("policy1", "policy1-copy");
      expect(notificationService.error).not.toHaveBeenCalled();
    });

    it("does not copy when the dialog is cancelled", async () => {
      closeCopyDialogWith(null);

      await component.copySelectedPolicies();

      expect(policyService.copyPolicy).not.toHaveBeenCalled();
    });

    it("reports the server message when the copy request fails", async () => {
      closeCopyDialogWith("policy 1");
      policyService.copyPolicy.mockRejectedValue(
        new HttpErrorResponse({
          status: 400,
          error: { result: { error: { message: "Policy name must not contain white spaces!" } } }
        })
      );

      await component.copySelectedPolicies();
      await flushPromises();

      expect(notificationService.error).toHaveBeenCalledWith(
        "Copying the policy to policy 1 failed: Policy name must not contain white spaces!"
      );
    });

    it("reports the error of a response without status", async () => {
      closeCopyDialogWith("policy1-copy");
      policyService.copyPolicy.mockResolvedValue(MockPiResponse.fromError({ message: "not created" }));

      await component.copySelectedPolicies();
      await flushPromises();

      expect(notificationService.error).toHaveBeenCalledWith("Copying the policy to policy1-copy failed: not created");
    });

    it("reports a failure without a server message", async () => {
      closeCopyDialogWith("policy1-copy");
      policyService.copyPolicy.mockRejectedValue("Policy not found");

      await component.copySelectedPolicies();
      await flushPromises();

      expect(notificationService.error).toHaveBeenCalledWith("Copying the policy to policy1-copy failed");
    });
  });
});
