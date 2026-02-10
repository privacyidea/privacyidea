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
import { PolicyActionItemComponent } from "./policy-action-item-new.component";
import { PolicyService, PolicyActionDetail } from "../../../../../../../../services/policies/policies.service";
import { Component, input, output } from "@angular/core";
import { By } from "@angular/platform-browser";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { FormsModule } from "@angular/forms";
import { MatSelectModule } from "@angular/material/select";

@Component({
  selector: "app-selector-buttons",
  template: "",
  standalone: true
})
class MockSelectorButtonsComponent {
  initialValue = input<any>();
  values = input.required<any[]>();
  onSelect = output<any>();
  focusFirst = jest.fn();
}

describe("PolicyActionItemComponent", () => {
  let component: PolicyActionItemComponent;
  let fixture: ComponentFixture<PolicyActionItemComponent>;
  let policyServiceMock: jest.Mocked<PolicyService>;

  const mockActionDetail: PolicyActionDetail = {
    type: "str",
    desc: "Test Description",
    value: ["val1", "val2"]
  };

  beforeEach(async () => {
    policyServiceMock = {
      actionValueIsValid: jest.fn().mockReturnValue(true)
    } as any;

    await TestBed.configureTestingModule({
      imports: [PolicyActionItemComponent, NoopAnimationsModule, FormsModule, MatSelectModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }]
    })
      .overrideComponent(PolicyActionItemComponent, {
        set: {
          imports: [MockSelectorButtonsComponent, FormsModule, MatSelectModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput("actionName", "testAction");
    fixture.componentRef.setInput("actionValue", "defaultVal");
    fixture.componentRef.setInput("actionDetail", mockActionDetail);

    fixture.detectChanges();
  });

  it("should create and apply correct flex classes", () => {
    const label = fixture.debugElement.query(By.css(".detail-label"));
    const desc = fixture.debugElement.query(By.css(".detail-description"));
    expect(label).toBeTruthy();
    expect(desc).toBeTruthy();
  });

  it("should update currentAction when actionDetail changes via linkedSignal", () => {
    fixture.componentRef.setInput("actionDetail", { type: "int", desc: "new", value: undefined });
    fixture.detectChanges();
    expect(component.currentAction().name).toBe("testAction");
  });

  it("should emit actionAdd with current value when add button is clicked", async () => {
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "desc", value: undefined });
    fixture.detectChanges();

    const spy = jest.spyOn(component.actionAdd, "emit");
    const addButton = fixture.debugElement.query(By.css(".add-action-button"));

    addButton.nativeElement.click();

    expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "defaultVal" });
  });

  it("should call addAction on Enter key if input is valid", () => {
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "desc", value: undefined });
    fixture.detectChanges();

    const spy = jest.spyOn(component, "addAction");
    const input = fixture.debugElement.query(By.css("input"));

    input.triggerEventHandler("keydown.enter", {});

    expect(spy).toHaveBeenCalled();
  });

  it("should not call addAction on Enter key if input is invalid", () => {
    policyServiceMock.actionValueIsValid.mockReturnValue(false);
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "desc", value: undefined });
    fixture.detectChanges();

    const spy = jest.spyOn(component, "addAction");
    const input = fixture.debugElement.query(By.css("input"));

    input.triggerEventHandler("keydown.enter", {});

    expect(spy).not.toHaveBeenCalled();
  });

  it("should focus the selector component if it is active", async () => {
    fixture.detectChanges();
    const selectorInstance = component.selectorComponent();
    const focusSpy = jest.spyOn(selectorInstance!, "focusFirst");

    component.focusFirstInput();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(focusSpy).toHaveBeenCalled();
  });

  it("should handle multi-value actions with mat-select if > 3 values", () => {
    fixture.componentRef.setInput("actionDetail", {
      type: "str",
      desc: "large list",
      value: ["1", "2", "3", "4", "5"]
    });
    fixture.detectChanges();

    const select = fixture.debugElement.query(By.css("mat-select"));
    expect(select).toBeTruthy();
  });
});
