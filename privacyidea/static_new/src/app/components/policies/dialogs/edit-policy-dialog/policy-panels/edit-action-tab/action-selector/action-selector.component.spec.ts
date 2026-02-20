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

import { Component, input, model, output, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule } from "@angular/forms";
import { CommonModule } from "@angular/common";
import { By } from "@angular/platform-browser";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { PolicyDetail, PolicyService } from "src/app/services/policies/policies.service";
import { ActionSelectorComponent } from "./action-selector.component";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { ClearableInputComponent } from "src/app/components/shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-policy-action-item-new",
  template: "<div></div>",
  standalone: true
})
class MockPolicyActionItemComponent {
  actionName = input.required<string>();
  actionDetail = input.required<any>();
  actionValue = input.required<any>();
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
  onSelect = output<string | null>();
}

@Component({
  standalone: true,
  imports: [ActionSelectorComponent, CommonModule, ClearableInputComponent, FormsModule],
  template: ` <app-action-selector [(policy)]="policy" /> `
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
      providers: [{ provide: PolicyService, useClass: MockPolicyService }, provideNoopAnimations()]
    })
      .overrideComponent(ActionSelectorComponent, {
        set: {
          imports: [
            CommonModule,
            FormsModule,
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

  it("should handle null group selection by falling back to empty string", () => {
    component.selectActionGroup(null);
    expect(component.selectedActionGroup()).toBe("");
  });

  it("should handle scope change", () => {
    const spy = jest.spyOn(component.scopeChange, "emit");
    component.selectActionScope("admin");
    TestBed.flushEffects();
    fixture.detectChanges();

    expect(spy).toHaveBeenCalledWith("admin");
  });
});
