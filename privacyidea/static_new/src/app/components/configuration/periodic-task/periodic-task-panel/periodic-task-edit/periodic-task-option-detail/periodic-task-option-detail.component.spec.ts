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

import { PeriodicTaskOptionDetailComponent } from "./periodic-task-option-detail.component";

describe("PeriodicTaskOptionDetailComponent", () => {
  let component: PeriodicTaskOptionDetailComponent;
  let fixture: ComponentFixture<PeriodicTaskOptionDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskOptionDetailComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskOptionDetailComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("option", {
      name: "total_tokens",
      description: "Total number of tokens",
      type: "bool",
      value: ""
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render option name and description", () => {
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain("total_tokens");
    expect(compiled.textContent).toContain("Total number of tokens");
  });

  it("should emit newValue with entered value", () => {
    component.value.set("value");
    const spy = jest.spyOn(component.newValue, "emit");
    component.addOption();
    expect(spy).toHaveBeenCalledWith("value");
  });

  it("should set value to 'True' if empty and emit", () => {
    component.value.set("");
    const spy = jest.spyOn(component.newValue, "emit");
    component.addOption();
    expect(component.value()).toBe("True");
    expect(spy).toHaveBeenCalledWith("True");
  });

  it("should show add button if showAddButton is true", () => {
    fixture.componentRef.setInput("showAddButton", true);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector("button")).not.toBeNull();
    expect(compiled.textContent).toContain("Add Option");
  });

  it("should show no button if showAddButton is false and type is bool", () => {
    fixture.componentRef.setInput("showAddButton", false);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const button = compiled.querySelector("button");
    expect(button).toBeNull();
  });

  it("should show apply changes button if showAddButton is false and type is str", () => {
    fixture.componentRef.setInput("option", {
      name: "event_counter",
      description: "The name of the event counter to read.",
      required: true,
      type: "str"
    });
    fixture.componentRef.setInput("showAddButton", false);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const button = compiled.querySelector("button");
    expect(button).not.toBeNull();
    expect(button?.textContent).toContain("Apply Changes");
  });
});
