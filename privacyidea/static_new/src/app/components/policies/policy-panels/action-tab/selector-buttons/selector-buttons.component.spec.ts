/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { SelectorButtons } from "./selector-buttons.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
// import "@angular/localize/init";

describe("BoolSelectButtonsComponent", () => {
  let component: SelectorButtons<any>;
  let fixture: ComponentFixture<SelectorButtons<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectorButtons, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectorButtons);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("initialValue", true);
    component.values = [true, false];
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display buttons for each value", () => {
    fixture.detectChanges();
    const buttons = fixture.nativeElement.querySelectorAll("button");
    expect(buttons.length).toBe(component.values.length);
  });

  it("should emit value on button click", () => {
    jest.spyOn(component.onSelect, "emit");
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector("button");
    button.click();
    expect(component.onSelect.emit).toHaveBeenCalledWith(component.values[0]);
  });

  it("should set the selected value on init", () => {
    fixture.componentRef.setInput("initialValue", false);
    fixture.detectChanges();
    expect(component.selectedValue()).toBe(false);
  });
});
