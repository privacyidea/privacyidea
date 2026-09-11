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

import { CommonModule } from "@angular/common";
import { Component, input, model, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { By } from "@angular/platform-browser";
import { PolicyDetail, PolicyService, ScopedPolicyActions } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { ActionSelectorComponent } from "./action-selector.component";
import { PolicyActionItemComponent, SelectableAction } from "./policy-action-item/policy-action-item-new.component";

@Component({
  selector: "app-policy-action-item-new",
  template: "<div></div>",
  standalone: true
})
class MockPolicyActionItemComponent {
  selectableAction = input.required<SelectableAction>();
  actionValue = input<string | number>();
  focusFirstInput = jest.fn();
}

@Component({
  standalone: true,
  imports: [ActionSelectorComponent],
  template: ` <app-action-selector [policy]="policy()" /> `
})
class TestHostComponent {
  policy = model<PolicyDetail>({
    name: "Test Policy",
    scope: "",
    conditions: [],
    action: {},
    description: "",
    adminrealm: [],
    adminuser: [],
    check_all_resolvers: false,
    client: [],
    pinode: [],
    priority: 0,
    realm: [],
    resolver: [],
    time: "",
    user: [],
    user_agents: [],
    user_case_insensitive: false,
    active: true
  });

  @ViewChild(ActionSelectorComponent)
  public component!: ActionSelectorComponent;
}

describe("ActionSelectorComponent", () => {
  let hostComponent: TestHostComponent;
  let fixture: ComponentFixture<TestHostComponent>;
  let component: ActionSelectorComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    })
      .overrideComponent(ActionSelectorComponent, {
        set: {
          imports: [CommonModule, MockPolicyActionItemComponent, MatButtonModule, MatIconModule, MatExpansionModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();
    component = hostComponent.component;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should list one panel per group of the selected scope", () => {
    (component["policyService"].filteredPolicyActionGroups as jest.Mock).mockReturnValue({
      admin: {
        tokenGroup: { enrollTOTP: { type: "bool" as const, desc: "Enroll TOTP." } },
        systemGroup: { configread: { type: "bool" as const, desc: "Read config." } }
      }
    });
    hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
    fixture.detectChanges();

    expect(component.actionGroups().map((group) => group.name)).toEqual(["tokenGroup", "systemGroup"]);
    const headers = fixture.debugElement.queryAll(By.css(".action-group-panel mat-expansion-panel-header"));
    expect(headers.map((header) => header.nativeElement.textContent.trim())).toEqual(["tokenGroup1", "systemGroup1"]);
  });

  it("should keep every group collapsed until one is opened", () => {
    (component["policyService"].filteredPolicyActionGroups as jest.Mock).mockReturnValue({
      admin: { tokenGroup: { enrollTOTP: { type: "bool" as const, desc: "Enroll TOTP." } } }
    });
    hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
    fixture.detectChanges();

    expect(component.openGroups().size).toBe(0);

    component.setGroupOpen("tokenGroup", true);
    expect([...component.openGroups()]).toEqual(["tokenGroup"]);

    component.setGroupOpen("tokenGroup", false);
    expect(component.openGroups().size).toBe(0);
  });

  it("should open the groups a search still matches, and collapse them once it is cleared", () => {
    (component["policyService"].filteredPolicyActionGroups as jest.Mock).mockReturnValue({
      admin: {
        tokenGroup: { enrollTOTP: { type: "bool" as const, desc: "Enroll TOTP." } },
        systemGroup: { configread: { type: "bool" as const, desc: "Read config." } }
      }
    });
    hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
    fixture.detectChanges();

    component.actionFilter.set("enroll");
    expect([...component.openGroups()]).toEqual(["tokenGroup", "systemGroup"]);

    component.actionFilter.set("");
    expect(component.openGroups().size).toBe(0);
  });

  describe("addable actions", () => {
    const adminAction = { type: "bool" as const, desc: "Admin can do this." };
    const userAction = { type: "str" as const, desc: "User can do this." };

    beforeEach(() => {
      (
        hostComponent.component["policyService"].policyActions as unknown as {
          set: (value: ScopedPolicyActions) => void;
        }
      ).set({
        admin: { container_add_token: adminAction, configread: { type: "bool" as const, desc: "Read config." } },
        user: { container_add_token: userAction }
      });
    });

    it("should return items from all scopes with scope labels when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const items = component.allScopeActions();
      const adminItem = items.find((i) => i.actionName === "container_add_token" && i.scope === "admin");
      const userItem = items.find((i) => i.actionName === "container_add_token" && i.scope === "user");

      expect(adminItem).toBeDefined();
      expect(userItem).toBeDefined();
      expect(adminItem?.label).toBe("[admin] container_add_token");
      expect(userItem?.label).toBe("[user] container_add_token");
    });

    it("should show a duplicate action name twice when it exists in multiple scopes", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const duplicates = component.allScopeActions().filter((i) => i.actionName === "container_add_token");
      expect(duplicates.length).toBe(2);
    });

    it("should group the items of the selected scope, without scope labels", () => {
      (component["policyService"].filteredPolicyActionGroups as jest.Mock).mockReturnValue({
        admin: {
          tokenGroup: { container_add_token: adminAction },
          systemGroup: { configread: { type: "bool" as const, desc: "Read config." } }
        }
      });
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
      fixture.detectChanges();

      const items = component.actionGroups().flatMap((group) => group.actions);
      expect(items.length).toBe(2);
      expect(items.every((i) => i.label === i.actionName)).toBe(true);
      expect(items.every((i) => i.scope === "admin")).toBe(true);
    });

    it("should ask for the groups without the actions the policy already has", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin", action: { container_add_token: true } });
      fixture.detectChanges();

      component.actionGroups();

      expect(component["policyService"].filteredPolicyActionGroups).toHaveBeenCalledWith(["container_add_token"], "");
    });

    it("should exclude already-added actions when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "", action: { container_add_token: true } });
      fixture.detectChanges();

      const items = component.allScopeActions();
      expect(items.find((i) => i.actionName === "container_add_token")).toBeUndefined();
      expect(items.find((i) => i.actionName === "configread")).toBeDefined();
    });

    it("should use scope-specific detail in each item when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const adminItem = component
        .allScopeActions()
        .find((i) => i.actionName === "container_add_token" && i.scope === "admin");
      const userItem = component
        .allScopeActions()
        .find((i) => i.actionName === "container_add_token" && i.scope === "user");

      expect(adminItem?.detail).toEqual(adminAction);
      expect(userItem?.detail).toEqual(userAction);
    });

    it("should emit the correct scope as newScope when adding an action with no policy scope", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();
      const spy = jest.spyOn(component.actionAdd, "emit");

      component.addPolicyAction({ name: "container_add_token", value: "" }, "user");

      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ action: { name: "container_add_token", value: "" }, newScope: "user" })
      );
    });

    it("should emit action without newScope when policy already has a scope", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
      fixture.detectChanges();
      const spy = jest.spyOn(component.actionAdd, "emit");

      component.addPolicyAction({ name: "configread", value: true }, "admin");

      expect(spy).toHaveBeenCalledWith({ action: { name: "configread", value: true } });
    });

    it("should fall back to getScopeOfAction when itemScope is not provided", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();
      (hostComponent.component["policyService"].getScopeOfAction as jest.Mock).mockReturnValue("admin");
      const spy = jest.spyOn(component.actionAdd, "emit");

      component.addPolicyAction({ name: "configread", value: true });

      expect(spy).toHaveBeenCalledWith(expect.objectContaining({ newScope: "admin" }));
    });
  });

  describe("focusNextActionItem", () => {
    it("should focus the item at currentIndex + 1 after action is added", async () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const mockItem: Partial<PolicyActionItemComponent> = { focusFirstInput: jest.fn() };
      jest.spyOn(component, "actionItems").mockReturnValue([mockItem as PolicyActionItemComponent]);
      jest.spyOn(component, "renderedActions").mockReturnValue([
        {
          actionName: "container_add_token",
          scope: "admin",
          label: "container_add_token",
          detail: { type: "bool" as const, desc: "Admin can do this." }
        }
      ]);

      component.focusNextActionItem("container_add_token", "admin");
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockItem.focusFirstInput).toHaveBeenCalled();
    });

    it("should not throw when no items are available", async () => {
      jest.spyOn(component, "actionItems").mockReturnValue([]);
      jest.spyOn(component, "renderedActions").mockReturnValue([]);

      expect(() => {
        component.focusNextActionItem("nonexistent", "admin");
      }).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  });
});
