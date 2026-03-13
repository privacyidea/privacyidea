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
import { ContainerTemplatesFilterComponent } from "./container-templates-filter.component";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { By } from "@angular/platform-browser";

describe("ContainerTemplatesFilterComponent", () => {
  let component: ContainerTemplatesFilterComponent;
  let fixture: ComponentFixture<ContainerTemplatesFilterComponent>;

  const createFilterWithText = (text: string) => {
    return new FilterValueGeneric<any>({ availableFilters: [] }).setByString(text);
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesFilterComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplatesFilterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize with an empty filter and isEmpty=true", () => {
    expect(component.isEmpty()).toBeTruthy();
    expect(component.filter().rawValue).toBe("");
  });

  it("should update filter when initialFilter input is set", () => {
    const testFilter = createFilterWithText("test-query");
    component.initialFilter = testFilter;

    expect(component.filter().rawValue).toBe("test-query");
    expect(component.isEmpty()).toBeFalsy();
    expect(component.lastFilter?.rawValue).toBe("test-query");
  });

  it("should emit filterChange when input value changes", () => {
    const spy = jest.spyOn(component.filterChange, "emit");
    const inputEl = fixture.debugElement.query(By.css("input")).nativeElement;

    inputEl.value = "new-filter";
    inputEl.dispatchEvent(new Event("input"));
    fixture.detectChanges();

    expect(spy).toHaveBeenCalled();
    expect(component.isEmpty()).toBeFalsy();
    expect(component.lastFilter?.rawValue).toBe("new-filter");
  });

  it("should clear the filter when clearFilter is called", () => {
    const spy = jest.spyOn(component.filterChange, "emit");
    const inputEl = fixture.debugElement.query(By.css("input")).nativeElement;

    component.updateFilterManually(createFilterWithText("something"));
    fixture.detectChanges();
    expect(component.isEmpty()).toBeFalsy();

    component.clearFilter();
    fixture.detectChanges();

    expect(component.filter().rawValue).toBe("");
    expect(component.isEmpty()).toBeTruthy();
    expect(inputEl.value).toBe("");
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ rawValue: "" }));
  });

  it("should focus the input element when focusInput is called", () => {
    const inputEl = fixture.debugElement.query(By.css("input")).nativeElement;
    const focusSpy = jest.spyOn(inputEl, "focus");

    component.focusInput();

    expect(focusSpy).toHaveBeenCalled();
  });

  it("should ignore redundant manual updates", () => {
    const initialFilter = createFilterWithText("fixed");
    component.updateFilterManually(initialFilter);
    fixture.detectChanges();

    const setSpy = jest.spyOn(component.filter, "set");

    component.updateFilterManually(initialFilter);

    expect(setSpy).not.toHaveBeenCalled();
  });

  it("should update isEmpty correctly on manual changes", () => {
    component.updateFilterManually(createFilterWithText("   "));
    expect(component.isEmpty()).toBeTruthy();

    component.updateFilterManually(createFilterWithText("valid"));
    expect(component.isEmpty()).toBeFalsy();
  });
});
