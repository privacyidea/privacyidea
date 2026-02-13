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
import { CopyPolicyDialogComponent } from "./copy-policy-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";
import { By } from "@angular/platform-browser";
import { ReactiveFormsModule } from "@angular/forms";

class MockMatDialogRef {
  close = jest.fn();
}

@Component({
  selector: "app-dialog-wrapper",
  template: "<ng-content></ng-content>",
  standalone: true
})
class MockDialogWrapperComponent {
  title = input.required<string>();
  actions = input.required<any[]>();
  close = output<void>();
  onAction = output<any>();
}

describe("CopyPolicyDialogComponent", () => {
  let component: CopyPolicyDialogComponent;
  let fixture: ComponentFixture<CopyPolicyDialogComponent>;
  let dialogRef: MockMatDialogRef;
  const initialPolicyName = "Original_Policy";

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CopyPolicyDialogComponent, NoopAnimationsModule, ReactiveFormsModule],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: initialPolicyName }
      ]
    })
      .overrideComponent(CopyPolicyDialogComponent, {
        set: {
          imports: [MockDialogWrapperComponent, ReactiveFormsModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(CopyPolicyDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize with the provided policy name", () => {
    expect(component.nameControl.value).toBe(initialPolicyName);
  });

  it("should be invalid if the name is the same as the original", () => {
    component.nameControl.setValue(initialPolicyName);
    expect(component.nameControl.hasError("notChanged")).toBeTruthy();
    expect(component.isInvalid()).toBe(true);
  });

  it("should close the dialog with the new name on submit", async () => {
    const newName = "Brand_New_Policy";
    component.nameControl.setValue(newName);
    component.onAction("submit");

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(dialogRef.close).toHaveBeenCalledWith(newName);
  });

  it("should close the dialog with null on cancel", async () => {
    component.onAction(null);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });

  it("should disable the submit action if form is invalid", () => {
    component.nameControl.setValue(initialPolicyName);
    fixture.detectChanges();

    const submitAction = component.actions().find((a) => a.value === "submit");

    expect(submitAction?.disabled).toBe(true);
  });
});
