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
import { DialogWrapperComponent } from "./dialog-wrapper.component";
import { DialogAction } from "../../../../models/dialog";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";
import { MatDialogRef } from "@angular/material/dialog";

describe("DialogWrapperComponent", () => {
  let component: DialogWrapperComponent;
  let fixture: ComponentFixture<DialogWrapperComponent<DialogAction[]>>;
  let nativeElement: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DialogWrapperComponent],
      providers: [{ provide: MatDialogRef, useClass: MockMatDialogRef }]
    }).compileComponents();

    fixture = TestBed.createComponent(DialogWrapperComponent<DialogAction[]>);
    component = fixture.componentInstance;
    nativeElement = fixture.nativeElement;
    fixture.componentRef.setInput("showCancelButton", true);
    fixture.componentRef.setInput("title", "Test Title");
    fixture.componentRef.setInput("actions", [
      { value: "confirm", label: "Confirm", type: "confirm", primary: true },
      { value: "delete", label: "Delete", type: "destruct", primary: true },
      { value: "reject", label: "Reject", type: "cancel" },
      { value: "help", label: "Help", type: "auxiliary", primary: true }
    ]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the title", () => {
    const titleEl = nativeElement.querySelector("h3");
    expect(titleEl?.textContent).toContain("Test Title");
  });

  it("should display the icon", () => {
    fixture.componentRef.setInput("icon", "test_icon");
    fixture.detectChanges();
    const iconEl = nativeElement.querySelector("mat-icon");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.textContent).toBe("test_icon");
  });

  it("should show the close button when showCancelButton is true", () => {
    const buttons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    const closeButton = Array.from(buttons).find((btn) => btn.textContent?.trim() === "Cancel");
    expect(closeButton?.textContent?.trim()).toBe("Cancel");
    expect(closeButton).toBeTruthy();
  });

  it("should not show the close button when showCancelButton is false", () => {
    fixture.componentRef.setInput("showCancelButton", false);
    fixture.detectChanges();
    const buttons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    const closeButton = Array.from(buttons).find((btn) => btn.textContent?.trim() === "Close");
    expect(closeButton).toBeUndefined();
  });

  it("should render action buttons", () => {
    const actionButtons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    expect(actionButtons.length).toBe(5);
    expect(actionButtons[0].textContent?.trim()).toBe("Cancel");
    expect(actionButtons[1].textContent?.trim()).toBe("Confirm");
    expect(actionButtons[2].textContent?.trim()).toBe("Delete");
    expect(actionButtons[3].textContent?.trim()).toBe("Reject");
    expect(actionButtons[4].textContent?.trim()).toBe("Help");
  });
  it("should apply correct classes to action buttons", () => {
    const actionButtons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    expect(actionButtons[1].classList).toContain("action-button-primary");
    expect(actionButtons[2].classList).toContain("action-button-delete-primary");
    expect(actionButtons[3].classList).toContain("action-button-secondary");
    expect(actionButtons[4].classList).toContain("action-button-primary");
  });
  it("should apply action-button-primary class when primary is true regardless of type", () => {
    fixture.componentRef.setInput("actions", [{ value: "p", label: "P", type: "cancel", primary: true }]);
    fixture.detectChanges();
    const btn = nativeElement.querySelector(".pi-dialog-footer button:last-child");
    expect(btn?.classList).toContain("action-button-primary");
  });
  it("should apply cdkFocusInitial to primary action", () => {
    fixture.componentRef.setInput("actions", [
      { value: "1", label: "1", primary: false },
      { value: "2", label: "2", primary: true }
    ]);
    fixture.detectChanges();
    const buttons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    expect(buttons[0].hasAttribute("cdkfocusinitial")).toBe(false);
    expect(buttons[1].hasAttribute("cdkfocusinitial")).toBe(false);
    expect(buttons[2].hasAttribute("cdkfocusinitial")).toBe(true);
  });
  it("should apply cdkFocusInitial to cancel button when cancelButtonPrimary is true", () => {
    fixture.componentRef.setInput("cancelButtonPrimary", true);
    fixture.detectChanges();
    const cancelButton = nativeElement.querySelector(".pi-dialog-footer button:first-child");
    expect(cancelButton?.hasAttribute("cdkfocusinitial")).toBe(true);
  });
  it("should emit onAction event with correct value when an action button is clicked", () => {
    jest.spyOn(component, "onActionClick");
    const actionButtons = nativeElement.querySelectorAll<HTMLButtonElement>(".pi-dialog-footer button");
    actionButtons[1].click();
    expect(component.onActionClick).toHaveBeenCalledWith({
      value: "confirm",
      label: "Confirm",
      type: "confirm",
      primary: true
    });
  });

  it("should throw an error if no actions and no close button", () => {
    const fixtureWrapper = TestBed.createComponent(DialogWrapperComponent);
    fixtureWrapper.componentRef.setInput("title", "Error Test");
    fixtureWrapper.componentRef.setInput("actions", []);
    fixtureWrapper.componentRef.setInput("showCancelButton", false);

    expect(() => fixtureWrapper.detectChanges()).toThrow("Dialog must have at least one action or a cancel button.");
  });

  it("should display the custom cancel button label", () => {
    fixture.componentRef.setInput("showCancelButton", true);
    fixture.componentRef.setInput("cancelButtonLabel", "Discard Changes");
    fixture.detectChanges();

    const buttons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    // The cancel button is always the first button when showCancelButton is true
    const cancelButton = buttons[0];

    expect(cancelButton?.textContent?.trim()).toBe("Discard Changes");
  });

  it("should respect hidden and disabled states of actions", () => {
    fixture.componentRef.setInput("actions", [
      { value: "visible", label: "Visible", disabled: true },
      { value: "hidden", label: "Hidden", hidden: true }
    ]);
    fixture.detectChanges();

    const buttons = nativeElement.querySelectorAll(".pi-dialog-footer button");
    expect(buttons.length).toBe(2); // "Visible" and "Cancel" buttons should be rendered, "Hidden" should not

    const actionBtn = Array.from(buttons).find((b) => b.textContent?.trim() === "Visible") as HTMLButtonElement;
    expect(actionBtn.disabled).toBe(true);
    const hiddenBtn = Array.from(buttons).find((b) => b.textContent?.trim() === "Hidden");
    expect(hiddenBtn).toBeUndefined();
  });
});
