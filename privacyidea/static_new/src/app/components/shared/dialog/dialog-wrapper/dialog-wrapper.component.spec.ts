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

describe("DialogWrapperComponent", () => {
  let component: DialogWrapperComponent;
  let fixture: ComponentFixture<DialogWrapperComponent<DialogAction[]>>;
  let nativeElement: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DialogWrapperComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(DialogWrapperComponent<DialogAction[]>);
    component = fixture.componentInstance;
    nativeElement = fixture.nativeElement;
    fixture.componentRef.setInput("showCancelButton", true);
    fixture.componentRef.setInput("title", "Test Title");
    fixture.componentRef.setInput("actions", [
      { value: "confirm", label: "Confirm", type: "confirm" },
      { value: "delete", label: "Delete", type: "destruct" },
      { value: "reject", label: "Reject", type: "cancel" },
      { value: "help", label: "Help", type: "auxiliary" }
    ]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the title", () => {
    const titleEl = nativeElement.querySelector("h2");
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
    expect(actionButtons[1].classList).toContain("action-button-1");
    expect(actionButtons[2].classList).toContain("action-button-delete");
    expect(actionButtons[3].classList).toContain("action-button-cancel");
    expect(actionButtons[4].classList).toContain("action-button-1");
  });
  it("should emit onAction event with correct value when an action button is clicked", () => {
    jest.spyOn(component, "onActionClick");
    const actionButtons = nativeElement.querySelectorAll<HTMLButtonElement>(".pi-dialog-footer button");
    actionButtons[1].click();
    expect(component.onActionClick).toHaveBeenCalledWith({ value: "confirm", label: "Confirm", type: "confirm" });
  });

  it("should throw an error if no actions and no close button", () => {
    const fixtureWrapper = TestBed.createComponent(DialogWrapperComponent);
    fixtureWrapper.componentRef.setInput("actions", []);
    fixtureWrapper.componentRef.setInput("showCancelButton", false);
    expect(() => fixtureWrapper.detectChanges()).toThrow("Dialog must have at least one action or a close button.");
  });
});
