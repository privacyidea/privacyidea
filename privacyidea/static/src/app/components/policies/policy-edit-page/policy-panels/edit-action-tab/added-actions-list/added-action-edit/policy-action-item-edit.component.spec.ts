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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { PolicyActionDetail, PolicyService } from "@services/policies/policies.service";
import { MockSelectorButtonsComponent } from "@testing/mock-components/mock-selector-buttons.component";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { PolicyActionItemEditComponent } from "./policy-action-item-edit.component";

describe("PolicyActionItemEditComponent", () => {
  let component: PolicyActionItemEditComponent;
  let fixture: ComponentFixture<PolicyActionItemEditComponent>;
  const defaultAction = { name: "test_action", value: "test_value" };
  const defaultDetail: PolicyActionDetail = {
    type: "str",
    desc: "Test Description",
    value: ["val1", "val2", "val3"]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyActionItemEditComponent, CommonModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    })
      .overrideComponent(PolicyActionItemEditComponent, {
        set: {
          imports: [
            CommonModule,
            MockSelectorButtonsComponent,
            MatButtonModule,
            MatIconModule,
            MatFormFieldModule,
            MatSelectModule,
            HighlightPipe
          ]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", defaultAction);
    fixture.componentRef.setInput("actionDetail", defaultDetail);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly identify numbers", () => {
    expect(component.isNumber("123")).toBe(true);
    expect(component.isNumber(123)).toBe(true);
    expect(component.isNumber("abc")).toBe(false);
    expect(component.isNumber("")).toBe(false);
    expect(component.isNumber(null)).toBe(false);
  });

  it("should identify boolean actions correctly", () => {
    fixture.componentRef.setInput("actionDetail", { type: "bool", desc: "" });
    fixture.detectChanges();
    expect(component.isBooleanAction()).toBe(true);
  });

  it("should offer three or more values in a dropdown", () => {
    expect(fixture.debugElement.query(By.directive(MockSelectorButtonsComponent))).toBeNull();

    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => option.componentInstance.value)).toEqual(["val1", "val2", "val3"]);
  });

  it("should offer fewer than three values as buttons", () => {
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "switch", value: ["val1", "val2"] });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(MockSelectorButtonsComponent))).not.toBeNull();
    expect(fixture.debugElement.query(By.directive(MatSelect))).toBeNull();
  });

  it("should highlight the search term in the action name", () => {
    fixture.componentRef.setInput("highlight", "action");
    fixture.detectChanges();

    const label = fixture.debugElement.query(By.css(".detail-label")).nativeElement as HTMLElement;
    expect(label.querySelector(".highlight")?.textContent).toBe("action");
  });

  it("should emit onUpdateAction when updateAction is called", () => {
    const spy = jest.spyOn(component.updateAction, "emit");
    component.handleUpdateAction("new_value");
    expect(spy).toHaveBeenCalledWith("new_value");
  });

  it("should emit onRemoveAction when delete button is clicked", () => {
    const spy = jest.spyOn(component.removeAction, "emit");
    const deleteBtn = fixture.debugElement.query(By.css(".delete-icon-button"));
    deleteBtn.nativeElement.click();
    expect(spy).toHaveBeenCalled();
  });
});
