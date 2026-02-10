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

import { ComponentFixture, TestBed, fakeAsync, tick } from "@angular/core/testing";
import { PolicyPanelEditComponent } from "./policy-panel-edit.component";
import { DialogService } from "../../../../../../services/dialog/dialog.service";
import { PolicyService } from "../../../../../../services/policies/policies.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";
import { of } from "rxjs";

/**
 * Concrete Mock class for DialogService.
 */
class MockDialogService {
  confirm = jest.fn().mockResolvedValue(true);
}

// Child Stubs
@Component({ selector: "app-policy-name-edit", standalone: true, template: "" })
class MockNameComp {
  policyName = input<string>("");
  policyNameChange = output<string>();
}

@Component({ selector: "app-policy-priority-edit", standalone: true, template: "" })
class MockPrioComp {
  priority = input<number>(0);
  priorityChange = output<number>();
}

@Component({ selector: "app-policy-description-edit", standalone: true, template: "" })
class MockDescComp {
  description = input<string>("");
  descriptionChange = output<string>();
}

@Component({ selector: "app-edit-action-tab", standalone: true, template: "" })
class MockActionTab {
  policy = input.required<any>();
  actionsUpdate = output<any>();
  policyScopeChange = output<any>();
}

@Component({ selector: "app-edit-conditions-tab", standalone: true, template: "" })
class MockCondTab {
  policy = input.required<any>();
  policyEdit = output<any>();
}

describe("PolicyPanelEditComponent - Extended Tests", () => {
  let component: PolicyPanelEditComponent;
  let fixture: ComponentFixture<PolicyPanelEditComponent>;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelEditComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(PolicyPanelEditComponent, {
        set: {
          imports: [MockNameComp, MockPrioComp, MockDescComp, MockActionTab, MockCondTab]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyPanelEditComponent);
    component = fixture.componentInstance;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture.componentRef.setInput("policy", {
      name: "Base Policy",
      priority: 5,
      action: {},
      scope: "user"
    });

    fixture.detectChanges();
  });

  it("should accumulate multiple edits correctly", () => {
    component.addPolicyEdit({ name: "Step 1" });
    component.addPolicyEdit({ priority: 10 });

    const finalPolicy = component.editedPolicy();
    expect(finalPolicy.name).toBe("Step 1");
    expect(finalPolicy.priority).toBe(10);
    expect(Object.keys(component.policyEdits()).length).toBe(2);
  });

  it("should switch between actions and conditions tabs", () => {
    expect(component.activeTab()).toBe("actions");

    component.setActiveTab("conditions");
    expect(component.activeTab()).toBe("conditions");

    component.setActiveTab("actions");
    expect(component.activeTab()).toBe("actions");
  });

  it("should NOT trigger a confirmation dialog on scope change if actions are empty", async () => {
    // Current policy has action: {} (empty)
    await component.onPolicyScopeChange("admin");

    expect(dialogService.confirm).not.toHaveBeenCalled();
    expect(component.editedPolicy().scope).toBe("admin");
  });

  it("should emit onPolicyEdit whenever addPolicyEdit is called", () => {
    const emitSpy = jest.spyOn(component.onPolicyEdit, "emit");
    const editPayload = { description: "New Description" };

    component.addPolicyEdit(editPayload);

    expect(emitSpy).toHaveBeenCalledWith(editPayload);
  });

  it("should correctly handle updateActions via a dedicated method", () => {
    const newActions = { login_mode: "privacy", otppin: "true" };
    component.updateActions(newActions);

    expect(component.editedPolicy().action).toEqual(newActions);
    expect(component.isPolicyEdited()).toBe(true);
  });

  it("should reset all local edits if the linkedSignal source (input policy) changes", () => {
    // 1. Make an edit
    component.addPolicyEdit({ name: "Local Modification" });
    expect(component.isPolicyEdited()).toBe(true);

    // 2. Simulate parent providing a new policy object reference
    fixture.componentRef.setInput("policy", {
      name: "Brand New Policy",
      priority: 1,
      action: {},
      scope: "web"
    });
    fixture.detectChanges();

    // 3. Edits should be gone
    expect(component.isPolicyEdited()).toBe(false);
    expect(component.editedPolicy().name).toBe("Brand New Policy");
  });

  it("should handle nullish description correctly in the template", () => {
    fixture.componentRef.setInput("policy", {
      name: "No Desc",
      priority: 1,
      action: {},
      scope: "user",
      description: undefined
    });
    fixture.detectChanges();

    // The editedPolicy() should reflect the input, and the getter for description
    // in the template (description ?? '') will handle the string conversion.
    expect(component.editedPolicy().description).toBeUndefined();
  });
});
