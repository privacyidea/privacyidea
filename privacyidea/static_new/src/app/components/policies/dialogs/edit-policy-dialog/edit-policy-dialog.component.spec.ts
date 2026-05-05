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
import { EditPolicyDialogComponent } from "./edit-policy-dialog.component";
import { PolicyService } from "../../../../services/policies/policies.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { MockDialogService } from "src/testing/mock-services/mock-dialog-service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { of } from "rxjs";
import { ROUTE_PATHS } from "../../../../route_paths";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "src/testing/mock-services/mock-pending-changes-service";

@Component({ selector: "app-policy-panel-edit", standalone: true, template: "" })
class MockPanel {
  policy = input.required<any>();
  onPolicyEdit = output<any>();
}

function createTestBed(paramName: string | null) {
  return TestBed.configureTestingModule({
    imports: [EditPolicyDialogComponent, NoopAnimationsModule],
    providers: [
      {
        provide: ActivatedRoute,
        useValue: { paramMap: of({ get: (key: string) => (key === "name" ? paramName : null) }) }
      },
      {
        provide: Router,
        useValue: { navigateByUrl: jest.fn(), events: of(), url: ROUTE_PATHS.POLICIES }
      },
      { provide: PolicyService, useClass: MockPolicyService },
      { provide: DialogService, useClass: MockDialogService },
      { provide: PendingChangesService, useClass: MockPendingChangesService }
    ]
  })
    .overrideComponent(EditPolicyDialogComponent, { set: { imports: [MockPanel] } })
    .compileComponents();
}

describe("EditPolicyDialogComponent – create mode", () => {
  let component: EditPolicyDialogComponent;
  let fixture: ComponentFixture<EditPolicyDialogComponent>;
  let policyService: MockPolicyService;
  let dialogService: MockDialogService;
  let router: Router;

  beforeEach(async () => {
    await createTestBed(null);

    fixture = TestBed.createComponent(EditPolicyDialogComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should be in create mode when no name param", () => {
    expect(component.mode()).toBe("create");
  });

  it("should merge edits into the policy", () => {
    component.addPolicyEdit({ priority: 99 });
    expect(component.editedPolicy().priority).toBe(99);
  });

  it("canSave returns false if no edits", () => {
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns false if name is missing", () => {
    component.addPolicyEdit({ name: "" });
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns true if edits and name present", () => {
    // TODO: Not only name, but also scope and at least one action should be required
    component.addPolicyEdit({ name: "ValidName" });
    expect(component.canSave()).toBe(true);
  });

  it("onAction does not call onSave if value is not submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction(null);
    expect(spy).not.toHaveBeenCalled();
  });

  it("onAction calls onSave if value is submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction("submit");
    expect(spy).toHaveBeenCalled();
  });

  it("onCancel navigates back directly when no changes", () => {
    component.onCancel();
    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy calls saveNewPolicy in create mode and navigates back", async () => {
    const spy = jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue(true);
    const success = await component.onSave();
    expect(spy).toHaveBeenCalled();
    expect(success).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy does not navigate when saveNewPolicy returns false", async () => {
    jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue(false);
    const success = await component.onSave();
    expect(success).toBe(false);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });
});

describe("EditPolicyDialogComponent – edit mode", () => {
  let component: EditPolicyDialogComponent;
  let fixture: ComponentFixture<EditPolicyDialogComponent>;
  let policyService: MockPolicyService;
  let router: Router;

  beforeEach(async () => {
    await createTestBed("TestPolicy");

    fixture = TestBed.createComponent(EditPolicyDialogComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it("should be in edit mode when name param is present", () => {
    expect(component.mode()).toBe("edit");
  });

  it("savePolicy calls savePolicyEdits in edit mode and navigates back", async () => {
    const spy = jest.spyOn(policyService, "savePolicyEdits").mockResolvedValue(true);
    const success = await component.onSave();
    expect(spy).toHaveBeenCalled();
    expect(success).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy does not navigate when savePolicyEdits returns false", async () => {
    jest.spyOn(policyService, "savePolicyEdits").mockResolvedValue(false);
    const success = await component.onSave();
    expect(success).toBe(false);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });
});
