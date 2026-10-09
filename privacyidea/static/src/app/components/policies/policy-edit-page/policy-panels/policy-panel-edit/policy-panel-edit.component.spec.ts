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

import {
  Component,
  ElementRef,
  forwardRef,
  input,
  output,
  provideZonelessChangeDetection,
  signal,
  viewChild
} from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { EditActionTabComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/edit-action-tab.component";
import { PolicyActionSearchComponent } from "@components/policies/policy-edit-page/policy-action-search/policy-action-search.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { PolicyPanelEditComponent } from "./policy-panel-edit.component";

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

@Component({ selector: "app-policy-scope-edit", standalone: true, template: "" })
class MockScopeComp {
  scope = input<string>("");
  disabled = input<boolean>(false);
  scopeChange = output<string>();
}

@Component({ selector: "app-policy-description-edit", standalone: true, template: "" })
class MockDescComp {
  description = input<string>("");
  descriptionChange = output<string>();
}

// Provided under the real class, so the panel's viewChild query for the action tab finds the mock.
@Component({
  selector: "app-edit-action-tab",
  standalone: true,
  template: "<div #searchAnchor></div>",
  providers: [{ provide: EditActionTabComponent, useExisting: forwardRef(() => MockActionTab) }]
})
class MockActionTab {
  searchAnchor = viewChild.required<ElementRef<HTMLElement>>("searchAnchor");
  searchField = signal({} as PolicyActionSearchComponent);
  policy = input.required<PolicyDetail>();
  actionFilter = input<string>("");
  searchInHeader = input<boolean>(false);
  actionsUpdate = output<Record<string, string | boolean>>();
  actionFilterChange = output<string>();
  policyScopeChange = output<string | undefined>();
}

@Component({ selector: "app-edit-conditions-tab", standalone: true, template: "" })
class MockCondTab {
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();
}

describe("PolicyPanelEditComponent - Extended Tests", () => {
  let component: PolicyPanelEditComponent;
  let fixture: ComponentFixture<PolicyPanelEditComponent>;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelEditComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService },
        provideZonelessChangeDetection()
      ]
    })
      .overrideComponent(PolicyPanelEditComponent, {
        set: {
          imports: [MockNameComp, MockPrioComp, MockScopeComp, MockDescComp, MockActionTab, MockCondTab]
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

  it("should pass the action tab's search anchor and field on to the page", () => {
    const actionTab = fixture.debugElement.query(By.directive(MockActionTab)).componentInstance as MockActionTab;

    expect(component.searchAnchor()).toBe(actionTab.searchAnchor().nativeElement);
    expect(component.searchField()).toBe(actionTab.searchField());
  });

  it("should have no search anchor or field while the conditions tab is open", () => {
    component.setActiveTab("conditions");
    fixture.detectChanges();

    expect(component.searchAnchor()).toBeUndefined();
    expect(component.searchField()).toBeUndefined();
  });

  it("should set the active tab from a valid selector value", () => {
    component.setActiveTab("actions");

    component.onTabSelected("conditions");
    expect(component.activeTab()).toBe("conditions");

    component.onTabSelected("actions");
    expect(component.activeTab()).toBe("actions");
  });

  it("should ignore invalid or undefined selector values", () => {
    component.setActiveTab("conditions");

    component.onTabSelected(undefined);
    expect(component.activeTab()).toBe("conditions");

    component.onTabSelected("not-a-tab");
    expect(component.activeTab()).toBe("conditions");
  });

  it("should NOT trigger a confirmation dialog on scope change if actions are empty", async () => {
    // Current policy has action: {} (empty)
    await component.onPolicyScopeChange("admin");

    expect(dialogService.confirm).not.toHaveBeenCalled();
    expect(component.editedPolicy().scope).toBe("admin");
  });

  it("should report added actions so that the scope field can lock itself", () => {
    expect(component.policyHasActions()).toBe(false);

    component.updateActions({ otppin: "true" });

    expect(component.policyHasActions()).toBe(true);
  });

  it("should emit onPolicyEdit whenever addPolicyEdit is called", () => {
    const emitSpy = jest.spyOn(component.policyEdit, "emit");
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
