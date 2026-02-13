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
import { PolicyPanelNewComponent } from "./policy-panel-new.component";
import { PolicyService } from "../../../../../../services/policies/policies.service";
import { DialogService } from "../../../../../../services/dialog/dialog.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { Component, input, output } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";
import { By } from "@angular/platform-browser";
import { MockDialogService } from "src/testing/mock-services/mock-dialog-service";

/**
 * Mock for PolicyPanelEditComponent to isolate PolicyPanelNewComponent.
 */
@Component({
  selector: "app-policy-panel-edit",
  standalone: true,
  template: ""
})
class MockPolicyPanelEditComp {
  policy = input.required<any>();
  onPolicyEdit = output<any>();
}

describe("PolicyPanelNewComponent", () => {
  let component: PolicyPanelNewComponent;
  let fixture: ComponentFixture<PolicyPanelNewComponent>;
  let policyService: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPanelNewComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(PolicyPanelNewComponent, {
        set: { imports: [MockPolicyPanelEditComp] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyPanelNewComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  /**
   * This test requires the MockPolicyService to return no available scopes.
   * If scopes are empty, the linkedSignal falls back to the empty policy's scope.
   */
  it("should initialize with default empty policy no scope selected", () => {
    jest.spyOn(policyService, "allPolicyScopes").mockReturnValue([]);
    jest.spyOn(policyService, "getEmptyPolicy").mockReturnValue({
      priority: 0,
      name: "",
      scope: "",
      action: {},
      conditions: []
    });

    fixture.detectChanges();

    expect(component.newPolicy().scope).toBe("");
  });

  it("should update draft when child component emits onPolicyEdit", () => {
    fixture.detectChanges();
    const editComp = fixture.debugElement.query(By.directive(MockPolicyPanelEditComp)).componentInstance;

    editComp.onPolicyEdit.emit({ name: "Updated via Child" });

    expect(component.newPolicy().name).toBe("Updated via Child");
  });

  it("should reset state after successful save", async () => {
    fixture.detectChanges();
    const saveSpy = jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue({});

    component.updatePolicy({ name: "Test Save" });
    await component.savePolicy();

    expect(saveSpy).toHaveBeenCalled();
    // After reset trigger, name should be empty again
    expect(component.newPolicy().name).toBe("");
  });
});
