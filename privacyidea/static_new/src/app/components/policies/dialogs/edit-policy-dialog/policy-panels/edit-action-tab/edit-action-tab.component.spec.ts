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
import { EditActionTabComponent } from "./edit-action-tab.component";
import { DialogService } from "../../../../../../services/dialog/dialog.service";
import { PolicyDetail } from "../../../../../../services/policies/policies.service";
import { Component, input, output } from "@angular/core";
import { provideNoopAnimations } from "@angular/platform-browser/animations";

@Component({
  selector: "app-added-actions-list",
  template: "",
  standalone: true
})
class MockAddedActionsListComponent {
  isEditMode = input.required<boolean>();
  actions = input.required<any[]>();
  actionsChange = output<any[]>();
  actionRemove = output<string>();
}

@Component({
  selector: "app-action-selector",
  template: "",
  standalone: true
})
class MockActionSelectorComponent {
  policy = input.required<any>();
  actionAdd = output<any>();
}

class MockDialogService {}

describe("EditActionTabComponent", () => {
  let component: EditActionTabComponent;
  let fixture: ComponentFixture<EditActionTabComponent>;

  const mockPolicy: PolicyDetail = {
    name: "test-policy",
    scope: "admin",
    action: {
      "action-1": "value-1",
      "action-2": "value-2"
    }
  } as any;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditActionTabComponent],
      providers: [{ provide: DialogService, useClass: MockDialogService }, provideNoopAnimations()]
    })
      .overrideComponent(EditActionTabComponent, {
        set: {
          imports: [MockAddedActionsListComponent, MockActionSelectorComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(EditActionTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", mockPolicy);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should transform policy actions into an array for children", () => {
    const actions = component.actions();
    expect(actions.length).toBe(2);
    expect(actions).toContainEqual({ name: "action-1", value: "value-1" });
    expect(actions).toContainEqual({ name: "action-2", value: "value-2" });
  });

  it("should emit actionsUpdate as an object when onActionsChange is called", () => {
    const spy = jest.spyOn(component.actionsUpdate, "emit");
    const updatedArray = [
      { name: "action-1", value: "new-value" },
      { name: "action-3", value: "value-3" }
    ];

    component.onActionsChange(updatedArray);

    expect(spy).toHaveBeenCalledWith({
      "action-1": "new-value",
      "action-3": "value-3"
    });
  });

  it("should handle adding a new action", () => {
    const spy = jest.spyOn(component.actionsUpdate, "emit");
    const action = { name: "action-new", value: "val-new" };

    component.onActionAdd({ action });

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        "action-1": "value-1",
        "action-2": "value-2",
        "action-new": "val-new"
      })
    );
  });

  it("should handle adding a new action with a new scope", () => {
    const actionsUpdateSpy = jest.spyOn(component.actionsUpdate, "emit");
    const scopeChangeSpy = jest.spyOn(component.policyScopeChange, "emit");
    const action = { name: "action-new", value: "val-new" };
    const newScope = "user";

    component.onActionAdd({ action, newScope });

    expect(actionsUpdateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        "action-1": "value-1",
        "action-2": "value-2",
        "action-new": "val-new"
      })
    );
    expect(scopeChangeSpy).toHaveBeenCalledWith(newScope);
  });

  it("should handle removing an action", () => {
    const spy = jest.spyOn(component.actionsUpdate, "emit");

    component.onActionRemove("action-1");

    expect(spy).toHaveBeenCalledWith({
      "action-2": "value-2"
    });
  });

  it("should reset selectedAction when the policy scope changes (linkedSignal)", () => {
    component.selectedAction.set({ name: "some", value: "val" });

    fixture.componentRef.setInput("policy", { ...mockPolicy, scope: "user" });
    fixture.detectChanges();

    expect(component.selectedAction()).toBeNull();
  });
});
