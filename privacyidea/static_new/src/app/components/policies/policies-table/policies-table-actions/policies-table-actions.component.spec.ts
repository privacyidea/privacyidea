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
import { PoliciesTableActionsComponent } from "./policies-table-actions.component";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { PolicyService } from "../../../../services/policies/policies.service";
import { MockDialogService } from "src/testing/mock-services/mock-dialog-service";
import { MockAuthService } from "src/testing/mock-services/mock-auth-service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";

describe("PoliciesTableActionsComponent", () => {
  let component: PoliciesTableActionsComponent;
  let fixture: ComponentFixture<PoliciesTableActionsComponent>;
  let dialogService: MockDialogService;
  let policyService: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesTableActionsComponent, NoopAnimationsModule],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PoliciesTableActionsComponent);
    component = fixture.componentInstance;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    fixture.componentRef.setInput("policySelection", new Set(["policy1"]));
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should open create dialog", () => {
    const spy = jest.spyOn(dialogService, "openDialog");
    component.createNewPolicy();
    expect(spy).toHaveBeenCalled();
  });

  it("should call delete on confirmed policies", async () => {
    jest.spyOn(dialogService, "openDialog").mockReturnValue({ afterClosed: () => of(true) } as any);
    const spy = jest.spyOn(policyService, "deletePolicy");
    await component.deleteSelectedPolicies();
    expect(spy).toHaveBeenCalledWith("policy1");
  });
});
