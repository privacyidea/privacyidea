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

import { signal } from "@angular/core";
import { EditableElement, EditButtonsComponent } from "./edit-buttons.component";

describe("EditButtonsComponent", () => {
  let component: EditButtonsComponent<EditableElement>;
  let fixture: ComponentFixture<EditButtonsComponent<EditableElement>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditButtonsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(EditButtonsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("element", {
      keyMap: { key: "value", label: "label" },
      isEditing: signal(false)
    });
    fixture.componentRef.setInput("isEditingUser", false);
    fixture.componentRef.setInput("isEditingInfo", false);
    fixture.componentRef.setInput("shouldHideEdit", false);
    fixture.componentRef.setInput("toggleEdit", jest.fn());
    fixture.componentRef.setInput("saveEdit", jest.fn());
    fixture.componentRef.setInput("cancelEdit", jest.fn());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("save button", () => {
    const saveButton = (): HTMLButtonElement | null => fixture.nativeElement.querySelector("button[aria-label='Save']");

    const startEditing = (valid?: ReturnType<typeof signal<boolean>>) => {
      fixture.componentRef.setInput("element", {
        keyMap: { key: "value", label: "label" },
        isEditing: signal(true),
        value: "",
        valid
      });
      fixture.componentRef.setInput("shouldHideEdit", true);
      fixture.detectChanges();
    };

    it("is enabled when the element has no validity channel", () => {
      startEditing();
      expect(saveButton()?.disabled).toBe(false);
    });

    it("follows the validity channel of the element", () => {
      const valid = signal(false);
      startEditing(valid);
      expect(saveButton()?.disabled).toBe(true);

      valid.set(true);
      fixture.detectChanges();
      expect(saveButton()?.disabled).toBe(false);
    });
  });

  describe("buttons of the edited row", () => {
    const button = (label: string): HTMLButtonElement | null =>
      fixture.nativeElement.querySelector(`button[aria-label='${label}']`);

    const showRow = (key: string, isEditing = false) => {
      const element = { keyMap: { key }, isEditing: signal(isEditing), value: "" };
      fixture.componentRef.setInput("element", element);
      fixture.componentRef.setInput("shouldHideEdit", true);
      fixture.detectChanges();
      return element;
    };

    it.each(["username", "user_name"])("shows save and cancel on the %p row while the user is edited", (key) => {
      fixture.componentRef.setInput("isEditingUser", true);
      showRow(key);

      expect(button("Save")).not.toBeNull();
      expect(button("Cancel")).not.toBeNull();
    });

    it("shows save and cancel on the info row while the info is edited", () => {
      fixture.componentRef.setInput("isEditingInfo", true);
      showRow("info");

      expect(button("Save")).not.toBeNull();
      expect(button("Cancel")).not.toBeNull();
    });

    it("shows neither save nor cancel on another row while the user or the info is edited", () => {
      fixture.componentRef.setInput("isEditingUser", true);
      fixture.componentRef.setInput("isEditingInfo", true);
      showRow("description");

      expect(button("Save")).toBeNull();
      expect(button("Cancel")).toBeNull();
    });

    it("hands the element to toggleEdit when edit is clicked", () => {
      const element = showRow("description");
      fixture.componentRef.setInput("shouldHideEdit", false);
      fixture.detectChanges();

      button("Edit")!.click();

      expect(component.toggleEdit()).toHaveBeenCalledWith(element);
      expect(component.saveEdit()).not.toHaveBeenCalled();
      expect(component.cancelEdit()).not.toHaveBeenCalled();
    });

    it("hands the element to saveEdit when save is clicked", () => {
      const element = showRow("description", true);

      button("Save")!.click();

      expect(component.saveEdit()).toHaveBeenCalledWith(element);
      expect(component.cancelEdit()).not.toHaveBeenCalled();
    });

    it("hands the element to cancelEdit and does not save when cancel is clicked", () => {
      const element = showRow("description", true);

      button("Cancel")!.click();

      expect(component.cancelEdit()).toHaveBeenCalledWith(element);
      expect(component.saveEdit()).not.toHaveBeenCalled();
    });
  });
});
