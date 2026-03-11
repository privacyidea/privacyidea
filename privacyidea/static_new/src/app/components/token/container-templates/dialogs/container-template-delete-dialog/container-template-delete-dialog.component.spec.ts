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
import { ContainerTemplate } from "../../../../../services/container/container.service";

describe("ContainerTemplateDeleteDialogComponent", () => {
  let component: ContainerTemplateDeleteDialogComponent;
  let fixture: ComponentFixture<ContainerTemplateDeleteDialogComponent>;
  let dialogRefMock: MockMatDialogRef<any, boolean>;

  const mockData: ContainerTemplate[] = [
    {
      name: "Template-Alpha",
      container_type: "type-1",
      default: false,
      template_options: { tokens: [] }
    },
    {
      name: "Template-Beta",
      container_type: "type-2",
      default: true,
      template_options: { tokens: [] }
    }
  ];

  async function createComponent(data: ContainerTemplate[] = mockData) {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateDeleteDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateDeleteDialogComponent);
    component = fixture.componentInstance;
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any, boolean>;
    fixture.detectChanges();
  }

  describe("Initial State & Rendering", () => {
    it("should create", async () => {
      await createComponent();
      expect(component).toBeTruthy();
    });

    it("should display simple text without a list when only one template is provided", async () => {
      const singleData = [mockData[0]];
      await createComponent(singleData);

      const list = fixture.debugElement.query(By.css("ul.template-list"));
      const boldElement = fixture.debugElement.query(By.css("b"));
      const paragraph = fixture.debugElement.query(By.css("p")).nativeElement;

      expect(list).toBeFalsy();
      expect(boldElement.nativeElement.textContent).toContain("Template-Alpha");
      expect(paragraph.textContent).toContain("Are you sure you want to delete the template");
    });

    it("should display a list when multiple templates are provided", async () => {
      await createComponent(mockData);

      const list = fixture.debugElement.query(By.css("ul.template-list"));
      const listItems = fixture.debugElement.queryAll(By.css("li b"));
      const paragraph = fixture.debugElement.query(By.css("p")).nativeElement;

      expect(list).toBeTruthy();
      expect(listItems.length).toBe(2);
      expect(listItems[0].nativeElement.textContent).toContain("Template-Alpha");
      expect(listItems[1].nativeElement.textContent).toContain("Template-Beta");
      expect(paragraph.textContent).toContain("delete the following templates");
    });

    it("should render the warning icon", async () => {
      await createComponent();
      const icon = fixture.debugElement.query(By.css("mat-icon.warn-icon"));
      expect(icon).toBeTruthy();
      expect(icon.nativeElement.textContent).toContain("warning");
    });

    it("should pass correct configuration to the dialog wrapper", async () => {
      await createComponent();
      const wrapper = fixture.debugElement.query(By.directive(DialogWrapperComponent)).componentInstance;

      const showCancelValue =
        typeof wrapper.showCancelButton === "function" ? wrapper.showCancelButton() : wrapper.showCancelButton;

      const actionsValue = typeof wrapper.actions === "function" ? wrapper.actions() : wrapper.actions;

      expect(showCancelValue).toBe(true);
      expect(actionsValue).toEqual(component.actions());
    });
  });

  describe("Actions", () => {
    beforeEach(async () => {
      await createComponent();
    });

    it("should define a destructive delete action", () => {
      const actions = component.actions();
      const deleteAction = actions.find((a) => a.value === "delete");
      expect(deleteAction?.type).toBe("destruct");
      expect(deleteAction?.icon).toBe("delete_forever");
    });

    it("should close the dialog with true when onAction is called with 'delete'", () => {
      component.onAction("delete");
      expect(dialogRefMock.close).toHaveBeenCalledWith(true);
    });

    it("should not close the dialog when an unknown action is triggered", () => {
      component.onAction("unknown");
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });
  });

  describe("Edge Cases", () => {
    it("should handle an empty template list gracefully", async () => {
      await createComponent([]);
      const listItems = fixture.debugElement.queryAll(By.css("li"));
      expect(listItems.length).toBe(0);
    });
  });
});
