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

import { FilterValueButtonComponent } from "./filter-value-button.component";

describe("FilterValueButtonComponent", () => {
  let component: FilterValueButtonComponent;
  let fixture: ComponentFixture<FilterValueButtonComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({ imports: [FilterValueButtonComponent] }).compileComponents();
    fixture = TestBed.createComponent(FilterValueButtonComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("value", "alice");
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("emits the value and stops propagation on click", () => {
    let emitted: string | undefined;
    component.filterValue.subscribe((v) => (emitted = v));
    const event = new MouseEvent("click");
    const stop = jest.spyOn(event, "stopPropagation");

    component.emit(event);

    expect(emitted).toBe("alice");
    expect(stop).toHaveBeenCalled();
  });

  it.each([
    ["empty", ""],
    ["blank", "   "],
    ["null", null],
    ["undefined", undefined]
  ])("renders no button for a %s cell value", (_, value) => {
    fixture.componentRef.setInput("value", value);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("button")).toBeNull();
  });

  it("hides the whole element without a value, so its spacing leaves no gap", () => {
    fixture.componentRef.setInput("value", "");
    fixture.detectChanges();

    expect(fixture.nativeElement.style.display).toBe("none");
  });

  it("names the column it filters by", () => {
    fixture.componentRef.setInput("column", "serial");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("button").getAttribute("aria-label")).toBe("Filter by this serial");
  });

  it("falls back to the generic label for a column without its own", () => {
    fixture.componentRef.setInput("column", "endpoint");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("button").getAttribute("aria-label")).toBe("Filter by this value");
  });
});
