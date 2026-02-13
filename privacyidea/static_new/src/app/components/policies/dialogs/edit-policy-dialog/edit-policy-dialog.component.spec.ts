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
import { EditPolicyDialogComponent } from "./edit-policy-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { PolicyService } from "../../../../services/policies/policies.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { MockDialogService } from "src/testing/mock-services/mock-dialog-service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";

@Component({ selector: "app-dialog-wrapper", standalone: true, template: "<ng-content></ng-content>" })
class MockWrapper {
  title = input<string>();
  actions = input<any[]>();
  close = output();
  onAction = output<any>();
}

@Component({ selector: "app-policy-panel-edit", standalone: true, template: "" })
class MockPanel {
  policy = input.required<any>();
  onPolicyEdit = output<any>();
}

describe("EditPolicyDialogComponent", () => {
  let component: EditPolicyDialogComponent;
  let fixture: ComponentFixture<EditPolicyDialogComponent>;
  let policyService: MockPolicyService;

  const mockData = {
    policyDetail: { name: "TestPolicy", scope: "user" },
    mode: "edit"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditPolicyDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(EditPolicyDialogComponent, {
        set: { imports: [MockWrapper, MockPanel] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(EditPolicyDialogComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should merge edits into the policy", () => {
    component.addPolicyEdit({ priority: 99 });
    expect(component.editedPolicy().priority).toBe(99);
  });

  it("should call policyService save when submitting", () => {
    const spy = jest.spyOn(policyService, "savePolicyEdits");
    component.addPolicyEdit({ priority: 99 });
    component.onAction("submit");
    expect(spy).toHaveBeenCalled();
  });
});
