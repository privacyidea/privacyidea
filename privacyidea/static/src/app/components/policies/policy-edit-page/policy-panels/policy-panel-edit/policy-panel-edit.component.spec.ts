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
import { MatTabsModule } from "@angular/material/tabs";
import { By } from "@angular/platform-browser";
import { EditActionTabComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/edit-action-tab.component";
import { PolicyActionSearchComponent } from "@components/policies/policy-edit-page/policy-action-search/policy-action-search.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { PolicyPanelEditComponent } from "./policy-panel-edit.component";
import { PolicyNameEditComponent } from "./policy-name-edit/policy-name-edit.component";
import { PolicyPriorityEditComponent } from "./policy-priority-edit/policy-priority-edit.component";

/**
 * Concrete Mock class for DialogService.
 */
class MockDialogService {
  confirm = jest.fn().mockResolvedValue(true);
}

// Child Stubs, provided under the real classes so the panel's viewChild queries find them.
@Component({
  selector: "app-policy-name-edit",
  standalone: true,
  template: "",
  providers: [{ provide: PolicyNameEditComponent, useExisting: forwardRef(() => MockNameComp) }]
})
class MockNameComp {
  policyName = input<string>("");
  nameTaken = input<boolean>(false);
  policyNameChange = output<string>();
  valid = signal(true);
}

@Component({
  selector: "app-policy-priority-edit",
  standalone: true,
  template: "",
  providers: [{ provide: PolicyPriorityEditComponent, useExisting: forwardRef(() => MockPrioComp) }]
})
class MockPrioComp {
  priority = input<number | null>(0);
  priorityChange = output<number | null>();
  valid = signal(true);
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
  valid = signal(true);
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

  const tabElements = (): HTMLElement[] =>
    fixture.debugElement.queryAll(By.css("[role=tab]")).map((tab) => tab.nativeElement as HTMLElement);

  const panelsWithContent = (): number =>
    fixture.debugElement
      .queryAll(By.css("[role=tabpanel]"))
      .filter((panel) => (panel.nativeElement as HTMLElement).querySelector(".tab-container") !== null).length;

  /** Leaving tab content detaches asynchronously, so the view needs a stable pass and a second change detection. */
  const settle = async (): Promise<void> => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };

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
          imports: [MatTabsModule, MockNameComp, MockPrioComp, MockScopeComp, MockDescComp, MockActionTab, MockCondTab]
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

  it("should hand the name collision of the page to the name field", () => {
    const nameField = () => fixture.debugElement.query(By.directive(MockNameComp)).componentInstance as MockNameComp;
    expect(nameField().nameTaken()).toBe(false);

    fixture.componentRef.setInput("nameTaken", true);
    fixture.detectChanges();

    expect(nameField().nameTaken()).toBe(true);
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

  it("should have no search anchor or field while the conditions tab is open", async () => {
    component.setActiveTab("conditions");
    await settle();

    expect(component.searchAnchor()).toBeUndefined();
    expect(component.searchField()).toBeUndefined();
  });

  it("should resolve the action tab inside the lazy tab content again after switching back", async () => {
    const anchorOfOpenTab = () =>
      (fixture.debugElement.query(By.directive(MockActionTab)).componentInstance as MockActionTab).searchAnchor()
        .nativeElement;
    expect(component.searchAnchor()).toBe(anchorOfOpenTab());

    component.setActiveTab("conditions");
    await settle();
    expect(component.searchAnchor()).toBeUndefined();

    component.setActiveTab("actions");
    await settle();
    expect(component.searchAnchor()).toBe(anchorOfOpenTab());
    expect(component.searchField()).toBeDefined();
  });

  it("should render a tablist with an actions and a conditions tab", () => {
    const tabs = tabElements();

    expect(fixture.debugElement.queryAll(By.css("[role=tablist]")).length).toBe(1);
    expect(tabs.map((tab) => tab.textContent?.trim())).toEqual(["Actions", "Conditions"]);
    expect(
      fixture.debugElement.query(By.css("[role=tablist]")).nativeElement.closest(".mat-mdc-tab-group")
    ).not.toBeNull();
    expect(fixture.debugElement.query(By.css(".policy-tabs"))).not.toBeNull();
  });

  it("should flip aria-selected and the active tab when a tab header is clicked", async () => {
    expect(tabElements().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false"]);

    tabElements()[1].click();
    await settle();

    expect(component.activeTab()).toBe("conditions");
    expect(tabElements().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true"]);

    tabElements()[0].click();
    await settle();

    expect(component.activeTab()).toBe("actions");
    expect(tabElements().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false"]);
  });

  it("should select the tab that the parent sets as activeTab", async () => {
    expect(component.tabIndex()).toBe(0);

    fixture.componentRef.setInput("activeTab", "conditions");
    await settle();

    expect(component.tabIndex()).toBe(1);
    expect(tabElements().map((tab) => tab.getAttribute("aria-selected"))).toEqual(["false", "true"]);
  });

  it("should render content in exactly one tabpanel and create the tab components lazily", async () => {
    expect(fixture.debugElement.queryAll(By.css("[role=tabpanel]")).length).toBe(2);
    expect(panelsWithContent()).toBe(1);
    expect(fixture.debugElement.query(By.directive(MockActionTab))).not.toBeNull();
    expect(fixture.debugElement.query(By.directive(MockCondTab))).toBeNull();

    component.setActiveTab("conditions");
    await settle();

    expect(panelsWithContent()).toBe(1);
    expect(fixture.debugElement.query(By.directive(MockActionTab))).toBeNull();
    expect(fixture.debugElement.query(By.directive(MockCondTab))).not.toBeNull();
  });

  it("should hand the edited policy to the active tab component", () => {
    const actionTab = fixture.debugElement.query(By.directive(MockActionTab)).componentInstance as MockActionTab;

    expect(actionTab.policy().name).toBe("Base Policy");
    expect(actionTab.searchInHeader()).toBe(false);

    fixture.componentRef.setInput("searchInHeader", true);
    fixture.detectChanges();

    expect(actionTab.searchInHeader()).toBe(true);
  });

  it("should set the active tab from a tab index", () => {
    component.onTabIndexChange(1);
    expect(component.activeTab()).toBe("conditions");

    component.onTabIndexChange(0);
    expect(component.activeTab()).toBe("actions");
  });

  it("should ignore a tab index outside the tab list", () => {
    component.setActiveTab("conditions");

    component.onTabIndexChange(5);
    expect(component.activeTab()).toBe("conditions");

    component.onTabIndexChange(-1);
    expect(component.activeTab()).toBe("conditions");
  });

  it("should NOT trigger a confirmation dialog on scope change if actions are empty", async () => {
    // Current policy has action: {} (empty)
    await component.onPolicyScopeChange("admin");

    expect(dialogService.confirm).not.toHaveBeenCalled();
    expect(component.editedPolicy().scope).toBe("admin");
  });

  it("should clear the actions on a confirmed scope change while actions are present", async () => {
    component.updateActions({ otppin: "true" });
    const emitSpy = jest.spyOn(component.policyEdit, "emit");

    await component.onPolicyScopeChange("admin");

    expect(dialogService.confirm).toHaveBeenCalledWith(expect.objectContaining({ title: "Change Policy Scope" }));
    expect(emitSpy).toHaveBeenCalledWith({ scope: "admin", action: {} });
    expect(component.editedPolicy().scope).toBe("admin");
    expect(component.editedPolicy().action).toEqual({});
    expect(component.policyHasActions()).toBe(false);
  });

  it("should keep scope and actions when the scope change is cancelled", async () => {
    component.updateActions({ otppin: "true" });
    dialogService.confirm.mockResolvedValueOnce(false);
    const emitSpy = jest.spyOn(component.policyEdit, "emit");

    await component.onPolicyScopeChange("admin");

    expect(dialogService.confirm).toHaveBeenCalledTimes(1);
    expect(emitSpy).not.toHaveBeenCalled();
    expect(component.editedPolicy().scope).toBe("user");
    expect(component.editedPolicy().action).toEqual({ otppin: "true" });
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

  describe("priority", () => {
    const priorityField = () =>
      fixture.debugElement.query(By.directive(MockPrioComp)).componentInstance as MockPrioComp;

    it("should hand the priority of the policy to the priority field", () => {
      expect(priorityField().priority()).toBe(5);
    });

    it("should store a priority that the priority field reports", () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");

      priorityField().priorityChange.emit(7);

      expect(component.editedPolicy().priority).toBe(7);
      expect(emitSpy).toHaveBeenCalledWith({ priority: 7 });
    });

    it("should store a priority of 0, so that the priority field can report it as too small", () => {
      priorityField().priorityChange.emit(0);

      expect(component.editedPolicy().priority).toBe(0);
    });

    it("should keep the last priority while the priority field is empty", () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");

      priorityField().priorityChange.emit(null);

      expect(component.editedPolicy().priority).toBe(5);
      expect(component.isPolicyEdited()).toBe(false);
      expect(emitSpy).not.toHaveBeenCalled();
    });
  });

  describe("valid", () => {
    const nameField = () => fixture.debugElement.query(By.directive(MockNameComp)).componentInstance as MockNameComp;
    const priorityField = () =>
      fixture.debugElement.query(By.directive(MockPrioComp)).componentInstance as MockPrioComp;

    it("should be true while name, priority and scope are valid", () => {
      expect(component.valid()).toBe(true);
    });

    it("should be false while the name is invalid", () => {
      nameField().valid.set(false);

      expect(component.valid()).toBe(false);
    });

    it("should be false while the priority is invalid", () => {
      priorityField().valid.set(false);

      expect(component.valid()).toBe(false);
    });

    it("should be false while no scope is chosen", () => {
      component.addPolicyEdit({ scope: "" });

      expect(component.valid()).toBe(false);
    });

    it("should be false while an added action holds an invalid value", () => {
      const actionTab = fixture.debugElement.query(By.directive(MockActionTab)).componentInstance as MockActionTab;

      actionTab.valid.set(false);

      expect(component.valid()).toBe(false);
    });

    it("should be true again once the invalid action value is corrected", () => {
      const actionTab = fixture.debugElement.query(By.directive(MockActionTab)).componentInstance as MockActionTab;
      actionTab.valid.set(false);

      actionTab.valid.set(true);

      expect(component.valid()).toBe(true);
    });

    it("should be true again once a scope is chosen", () => {
      component.addPolicyEdit({ scope: "" });
      component.addPolicyEdit({ scope: "admin" });

      expect(component.valid()).toBe(true);
    });
  });
});
