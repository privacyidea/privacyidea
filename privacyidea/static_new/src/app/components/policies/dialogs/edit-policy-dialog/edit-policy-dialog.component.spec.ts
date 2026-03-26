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
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";
import { of, Subject } from "rxjs";

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
  let dialogService: MockDialogService;
  let mockDialogRef: any;

  const mockData = {
    policyDetail: { name: "TestPolicy", scope: "user" },
    mode: "edit"
  };

  beforeEach(async () => {
    mockDialogRef = {
      backdropClick: () => mockDialogRef._backdropClick,
      keydownEvents: () => mockDialogRef._keydownEvents,
      _backdropClick: new Subject<any>(),
      _keydownEvents: new Subject<any>(),
      close: jest.fn()
    };
    await TestBed.configureTestingModule({
      imports: [EditPolicyDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
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
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should merge edits into the policy", () => {
    component.addPolicyEdit({ priority: 99 });
    expect(component.editedPolicy().priority).toBe(99);
  });

  it("canSave returns false if no edits", () => {
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns false if name is missing", () => {
    component.addPolicyEdit({ name: "" });
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns true if edits and name present", () => {
    // TODO: Not only name, but also scope and at least one action should be required
    component.addPolicyEdit({ name: "ValidName" });
    expect(component.canSave()).toBe(true);
  });

  it("onAction does not call savePolicy if value is not submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction(null);
    expect(spy).not.toHaveBeenCalled();
  });

  it("onAction calls savePolicy if value is submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction("submit");
    expect(spy).toHaveBeenCalled();
  });

  it("close does not opens discard dialog if there are no changes", () => {
    const saveSpy = jest.spyOn(component, "onSave").mockResolvedValue(true);

    component["close"]();

    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("savePolicy calls savePolicyEdits in edit mode", async () => {
    const spy = jest.spyOn(policyService, "savePolicyEdits").mockResolvedValue(true);
    await component.onSave();
    expect(spy).toHaveBeenCalledWith("TestPolicy", expect.any(Object));
  });
});

describe("Create Policy in EditPolicyDialogComponent", () => {
  let component: EditPolicyDialogComponent;
  let fixture: ComponentFixture<EditPolicyDialogComponent>;
  let policyService: MockPolicyService;

  const mockData = {
    policyDetail: { name: "TestPolicy", scope: "user" },
    mode: "create"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditPolicyDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
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

  it("savePolicy calls saveNewPolicy in create mode", async () => {
    const spy = jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue(true);
    await component.onSave();
    expect(spy).toHaveBeenCalled();
  });
});
