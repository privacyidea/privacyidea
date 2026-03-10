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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContainerTemplateDeleteDialogComponent } from "./container-template-delete-dialog.component";
import { MockMatDialogRef } from "src/testing/mock-mat-dialog-ref";
import { By } from "@angular/platform-browser";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";

describe("ContainerTemplateDeleteDialogComponent", () => {
  let component: ContainerTemplateDeleteDialogComponent;
  let fixture: ComponentFixture<ContainerTemplateDeleteDialogComponent>;
  let dialogRefMock: MockMatDialogRef<any, boolean>;

  const mockData = {
    name: "TestTemplate",
    container_type: "test-type",
    template_options: { tokens: [] }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateDeleteDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockData }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateDeleteDialogComponent);
    component = fixture.componentInstance;
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any, boolean>;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the template name in the confirmation message", () => {
    const boldElement = fixture.debugElement.query(By.css("b")).nativeElement;
    expect(boldElement.textContent).toContain(mockData.name);
  });

  it("should define a destructive delete action", () => {
    const actions = component.actions();
    expect(actions.length).toBe(1);
    expect(actions[0].value).toBe("delete");
    expect(actions[0].type).toBe("destruct");
  });

  it("should close the dialog with 'true' when the delete action is triggered", () => {
    component.onAction("delete");
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });

  it("should not close the dialog when an unknown action is triggered", () => {
    component.onAction("unknown");
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("should pass showCancelButton=true to the dialog wrapper", () => {
    const wrapperDebugEl = fixture.debugElement.query(By.directive(DialogWrapperComponent));
    const wrapperInstance = wrapperDebugEl.componentInstance as DialogWrapperComponent;

    const showCancelValue =
      typeof wrapperInstance.showCancelButton === "function"
        ? wrapperInstance.showCancelButton()
        : wrapperInstance.showCancelButton;

    expect(showCancelValue).toBe(true);
  });

  it("should pass the correct actions to the dialog wrapper", () => {
    const wrapperDebugEl = fixture.debugElement.query(By.directive(DialogWrapperComponent));
    const wrapperInstance = wrapperDebugEl.componentInstance as DialogWrapperComponent;

    const actionsValue =
      typeof wrapperInstance.actions === "function" ? wrapperInstance.actions() : wrapperInstance.actions;

    expect(actionsValue[0].value).toBe("delete");
  });
});
