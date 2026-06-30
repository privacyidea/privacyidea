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

import { Type } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { SelectorButtonsComponent } from "./selector-buttons.component";

describe("SelectorButtonsComponent", () => {
  let component: SelectorButtonsComponent<string>;
  let fixture: ComponentFixture<SelectorButtonsComponent<string>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectorButtonsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent<SelectorButtonsComponent<string>>(
      SelectorButtonsComponent as unknown as Type<SelectorButtonsComponent<string>>
    );
    component = fixture.componentInstance;

    fixture.componentRef.setInput("values", ["A", "B", "C"]);
    fixture.componentRef.setInput("initialValue", "A");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have selected-button class on the initial value", () => {
    const selectedBtn = fixture.debugElement.query(By.css(".selected-button"));
    expect(selectedBtn.nativeElement.textContent.trim()).toBe("A");
  });

  it("should not lose selection class when becoming disabled", () => {
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    const selectedBtn = fixture.debugElement.query(By.css(".selected-button"));
    expect(selectedBtn).toBeTruthy();
    expect(selectedBtn.nativeElement.disabled).toBe(true);
  });

  it("should properly apply 'last-button' class to the correct element", () => {
    const buttons = fixture.debugElement.queryAll(By.css(".button-item"));
    expect(buttons[2].nativeElement.classList).toContain("last-button");
  });

  it("selectValue should do nothing when disabled", () => {
    const emitSpy = jest.fn();
    component.selected.subscribe(emitSpy);
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    component.selectValue("B");

    expect(component.selectedValue()).toBe("A");
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it("selectValue should select a new value and emit it", () => {
    const emitSpy = jest.fn();
    component.selected.subscribe(emitSpy);

    component.selectValue("B");

    expect(component.selectedValue()).toBe("B");
    expect(emitSpy).toHaveBeenCalledWith("B");
  });

  it("selectValue should keep selection when reselecting and deselect is not allowed", () => {
    const emitSpy = jest.fn();
    component.selected.subscribe(emitSpy);

    component.selectValue("A");

    expect(component.selectedValue()).toBe("A");
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it("selectValue should deselect when reselecting and deselect is allowed", () => {
    const emitSpy = jest.fn();
    component.selected.subscribe(emitSpy);
    fixture.componentRef.setInput("allowDeselect", true);
    fixture.detectChanges();

    component.selectValue("A");

    expect(component.selectedValue()).toBeUndefined();
    expect(emitSpy).toHaveBeenCalledWith(undefined);
  });

  it("isOverflowing should be true only when scrollWidth exceeds clientWidth", () => {
    const overflowing = { scrollWidth: 120, clientWidth: 80 } as HTMLElement;
    const fitting = { scrollWidth: 80, clientWidth: 80 } as HTMLElement;

    expect(component.isOverflowing(overflowing)).toBe(true);
    expect(component.isOverflowing(fitting)).toBe(false);
  });

  it("focusFirst should focus the first rendered button", () => {
    const firstButton = component.buttons()[0].nativeElement;
    const focusSpy = jest.spyOn(firstButton, "focus");

    component.focusFirst();

    expect(focusSpy).toHaveBeenCalled();
  });
});
