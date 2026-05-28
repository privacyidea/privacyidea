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
import { Component, input, model, output, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { ActionSelectorComponent } from "./action-selector.component";

@Component({
  selector: "app-policy-action-item-new",
  template: "<div></div>",
  standalone: true
})
class MockPolicyActionItemComponent {
  selectableAction = input.required<any>();
  actionValue = input<any>();
  focusFirstInput = jest.fn();
}

@Component({
  selector: "app-selector-buttons",
  template: "<div></div>",
  standalone: true
})
class MockSelectorButtonsComponent {
  values = input.required<string[]>();
  initialValue = input<string>();
  allowDeselect = input<boolean>();
  disabled = input<boolean>();
  select = output<string | null>();
}

@Component({
  standalone: true,
  imports: [ActionSelectorComponent, ClearableInputComponent],
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
          imports: [
            CommonModule,
            MockPolicyActionItemComponent,
            MockSelectorButtonsComponent,
            ClearableInputComponent
          ]
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

  it("should handle undefined group selection by falling back to empty string", () => {
    component.selectActionGroup();
    expect(component.selectedActionGroup()).toBe("");
  });

  it("should return group names when filteredPolicyActionGroups has groups for the current scope", () => {
    (component["policyService"].filteredPolicyActionGroups as jest.Mock).mockReturnValue({
      admin: { tokenGroup: { enrollTOTP: { type: "bool" as const, desc: "Enroll TOTP." } } }
    });
    hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
    fixture.detectChanges();

    expect(component.actionGroupNamesFiltered()).toContain("tokenGroup");
  });

  it("should handle scope change", () => {
    const spy = jest.spyOn(component.scopeChange, "emit");
    component.selectActionScope("admin");
    TestBed.tick();
    fixture.detectChanges();

    expect(spy).toHaveBeenCalledWith("admin");
  });

  describe("actionsFiltered", () => {
    const adminAction = { type: "bool" as const, desc: "Admin can do this." };
    const userAction = { type: "str" as const, desc: "User can do this." };

    beforeEach(() => {
      (hostComponent.component["policyService"].policyActions as any).set({
        admin: { container_add_token: adminAction, configread: { type: "bool" as const, desc: "Read config." } },
        user: { container_add_token: userAction }
      });
    });

    it("should return items from all scopes with scope labels when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const items = component.actionsFiltered();
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

      const duplicates = component.actionsFiltered().filter((i) => i.actionName === "container_add_token");
      expect(duplicates.length).toBe(2);
    });

    it("should return items from the selected scope only without scope labels", () => {
      (hostComponent.component["policyService"].getActionsOf as jest.Mock).mockReturnValue({
        container_add_token: adminAction,
        configread: { type: "bool" as const, desc: "Read config." }
      });
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin" });
      fixture.detectChanges();

      const items = component.actionsFiltered();
      expect(items.length).toBeGreaterThan(0);
      expect(items.every((i) => i.label === i.actionName)).toBe(true);
      expect(items.every((i) => i.scope === "admin")).toBe(true);
    });

    it("should exclude already-added actions when a scope is selected", () => {
      (hostComponent.component["policyService"].getActionsOf as jest.Mock).mockReturnValue({
        container_add_token: adminAction,
        configread: { type: "bool" as const, desc: "Read config." }
      });
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "admin", action: { container_add_token: true } });
      fixture.detectChanges();

      const items = component.actionsFiltered();
      expect(items.find((i) => i.actionName === "container_add_token")).toBeUndefined();
      expect(items.find((i) => i.actionName === "configread")).toBeDefined();
    });

    it("should exclude already-added actions when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "", action: { container_add_token: true } });
      fixture.detectChanges();

      const items = component.actionsFiltered();
      expect(items.find((i) => i.actionName === "container_add_token")).toBeUndefined();
      expect(items.find((i) => i.actionName === "configread")).toBeDefined();
    });

    it("should use scope-specific detail in each item when no scope is selected", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const adminItem = component.actionsFiltered().find(
        (i) => i.actionName === "container_add_token" && i.scope === "admin"
      );
      const userItem = component.actionsFiltered().find(
        (i) => i.actionName === "container_add_token" && i.scope === "user"
      );

      expect(adminItem?.detail).toEqual(adminAction);
      expect(userItem?.detail).toEqual(userAction);
    });

    it("should emit the correct scope as newScope when adding an action with no policy scope", () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();
      const spy = jest.spyOn(component.actionAdd, "emit");

      component.addPolicyAction({ name: "container_add_token", value: undefined }, "user");

      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ action: { name: "container_add_token", value: undefined }, newScope: "user" })
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

      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ newScope: "admin" })
      );
    });
  });

  describe("focusNextActionItem", () => {
    it("should focus the item at currentIndex + 1 after action is added", async () => {
      hostComponent.policy.set({ ...hostComponent.policy(), scope: "" });
      fixture.detectChanges();

      const mockItem = { focusFirstInput: jest.fn() };
      jest.spyOn(component, "actionItems").mockReturnValue([mockItem as any]);
      jest.spyOn(component, "actionsFiltered").mockReturnValue([
        { actionName: "container_add_token", scope: "admin", label: "container_add_token", detail: { type: "bool" as const, desc: "Admin can do this." } }
      ]);

      component.focusNextActionItem("container_add_token", "admin");
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockItem.focusFirstInput).toHaveBeenCalled();
    });

    it("should not throw when no items are available", async () => {
      jest.spyOn(component, "actionItems").mockReturnValue([]);
      jest.spyOn(component, "actionsFiltered").mockReturnValue([]);

      expect(() => {
        component.focusNextActionItem("nonexistent", "admin");
      }).not.toThrow();

      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  });
});
