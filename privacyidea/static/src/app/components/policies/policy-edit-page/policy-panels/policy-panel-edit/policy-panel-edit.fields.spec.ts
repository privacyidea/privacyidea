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

import { Component, input, output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTabsModule } from "@angular/material/tabs";
import { By } from "@angular/platform-browser";
import { DialogService } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { PolicyDescriptionEditComponent } from "./policy-description/policy-description-edit.component";
import { PolicyNameEditComponent } from "./policy-name-edit/policy-name-edit.component";
import { PolicyPanelEditComponent } from "./policy-panel-edit.component";
import { PolicyPriorityEditComponent } from "./policy-priority-edit/policy-priority-edit.component";
import { PolicyScopeEditComponent } from "./policy-scope-edit/policy-scope-edit.component";

@Component({ selector: "app-edit-action-tab", standalone: true, template: "" })
class StubActionTab {
  policy = input.required<PolicyDetail>();
  actionFilter = input<string>("");
  searchInHeader = input<boolean>(false);
  actionsUpdate = output<Record<string, string | boolean>>();
  policyScopeChange = output<string | undefined>();
}

@Component({ selector: "app-edit-conditions-tab", standalone: true, template: "" })
class StubConditionsTab {
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();
}

/**
 * The panel with its real name, scope, priority and description fields: the rules of the fields decide
 * whether the panel is valid, and what they type reaches the edited policy.
 */
describe("PolicyPanelEditComponent with its fields", () => {
  let component: PolicyPanelEditComponent;
  let fixture: ComponentFixture<PolicyPanelEditComponent>;
  let policyService: MockPolicyService;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const type = async (selector: string, value: string) => {
    const element = fixture.debugElement.query(By.css(selector)).nativeElement as HTMLInputElement;
    element.value = value;
    element.dispatchEvent(new Event("input"));
    await flush();
  };
  const priorityInput = "app-policy-priority-edit input";
  const nameInput = "app-policy-name-edit input";

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelEditComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useValue: { confirm: jest.fn().mockResolvedValue(true) } }
      ]
    })
      .overrideComponent(PolicyPanelEditComponent, {
        set: {
          imports: [
            MatTabsModule,
            PolicyNameEditComponent,
            PolicyScopeEditComponent,
            PolicyPriorityEditComponent,
            PolicyDescriptionEditComponent,
            StubActionTab,
            StubConditionsTab
          ]
        }
      })
      .compileComponents();

    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    fixture = TestBed.createComponent(PolicyPanelEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      ...policyService.getEmptyPolicy(),
      name: "helpdesk",
      scope: "admin",
      priority: 3
    });
    await flush();
  });

  it("should be valid for a policy with a name, a scope and a priority", () => {
    expect(component.valid()).toBe(true);
  });

  it("should be invalid while the name is empty", async () => {
    await type(nameInput, "");

    expect(component.valid()).toBe(false);
  });

  it("should be invalid while the name has characters that are not allowed", async () => {
    await type(nameInput, "my policy");

    expect(component.valid()).toBe(false);
  });

  it("should be invalid while the name is taken", async () => {
    fixture.componentRef.setInput("nameTaken", true);
    await flush();

    expect(component.valid()).toBe(false);
  });

  it("should be invalid while no scope is chosen", async () => {
    fixture.componentRef.setInput("policy", { ...component.policy(), scope: "" });
    await flush();

    expect(component.valid()).toBe(false);
  });

  describe("priority", () => {
    it("should store a typed priority and stay valid", async () => {
      await type(priorityInput, "12");

      expect(component.editedPolicy().priority).toBe(12);
      expect(component.valid()).toBe(true);
    });

    it("should become invalid and keep the last priority when the field is emptied", async () => {
      await type(priorityInput, "");

      expect(component.valid()).toBe(false);
      expect(component.editedPolicy().priority).toBe(3);
      expect(component.isPolicyEdited()).toBe(false);
    });

    it("should become valid again once a priority is typed after the field was emptied", async () => {
      await type(priorityInput, "");
      await type(priorityInput, "4");

      expect(component.valid()).toBe(true);
      expect(component.editedPolicy().priority).toBe(4);
    });

    it.each(["0", "-1"])("should become invalid for the priority %s", async (priority) => {
      await type(priorityInput, priority);

      expect(component.valid()).toBe(false);
      expect(component.editedPolicy().priority).toBe(Number(priority));
    });
  });

  describe("description", () => {
    it("should store a typed description", async () => {
      await type("app-policy-description-edit textarea", "Lets the helpdesk reset PINs");

      expect(component.editedPolicy().description).toBe("Lets the helpdesk reset PINs");
      expect(component.isPolicyEdited()).toBe(true);
    });

    it("should leave the panel valid", async () => {
      await type("app-policy-description-edit textarea", "x");

      expect(component.valid()).toBe(true);
    });
  });
});
