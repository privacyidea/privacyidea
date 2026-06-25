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

import { MultiSelectFilterComponent } from "./multi-select-filter.component";

describe("MultiSelectFilterComponent", () => {
  let component: MultiSelectFilterComponent;
  let fixture: ComponentFixture<MultiSelectFilterComponent>;
  let emitted: string[][];

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({ imports: [MultiSelectFilterComponent] }).compileComponents();
    fixture = TestBed.createComponent(MultiSelectFilterComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("options", ["LOGIN_SUCCESS", "MFA_FAIL", "PIN_FAIL"]);
    fixture.componentRef.setInput("selected", []);
    emitted = [];
    component.selectionChange.subscribe((value) => emitted.push(value));
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("normalizes plain string options to label/value pairs", () => {
    expect(component.normalizedOptions()).toEqual([
      { label: "LOGIN_SUCCESS", value: "LOGIN_SUCCESS" },
      { label: "MFA_FAIL", value: "MFA_FAIL" },
      { label: "PIN_FAIL", value: "PIN_FAIL" }
    ]);
  });

  it("isSelected reflects the selected input", () => {
    fixture.componentRef.setInput("selected", ["MFA_FAIL"]);
    expect(component.isSelected({ label: "MFA_FAIL", value: "MFA_FAIL" })).toBe(true);
    expect(component.isSelected({ label: "LOGIN_SUCCESS", value: "LOGIN_SUCCESS" })).toBe(false);
  });

  it("toggle adds a value not yet selected", () => {
    fixture.componentRef.setInput("selected", ["LOGIN_SUCCESS"]);
    component.toggle({ label: "MFA_FAIL", value: "MFA_FAIL" });
    expect(emitted).toEqual([["LOGIN_SUCCESS", "MFA_FAIL"]]);
  });

  it("toggle removes an already-selected value", () => {
    fixture.componentRef.setInput("selected", ["LOGIN_SUCCESS", "MFA_FAIL"]);
    component.toggle({ label: "LOGIN_SUCCESS", value: "LOGIN_SUCCESS" });
    expect(emitted).toEqual([["MFA_FAIL"]]);
  });

  it("clear emits an empty selection", () => {
    fixture.componentRef.setInput("selected", ["LOGIN_SUCCESS", "MFA_FAIL"]);
    component.clear();
    expect(emitted).toEqual([[]]);
  });

  it("applies valueSuffix and matches it against the selected values (display stays the raw label)", () => {
    fixture.componentRef.setInput("options", [{ label: "Keycloak", value: "privacyIDEA-Keycloak" }]);
    fixture.componentRef.setInput("valueSuffix", "*");
    const option = { label: "Keycloak", value: "privacyIDEA-Keycloak" };

    component.toggle(option);
    expect(emitted).toEqual([["privacyIDEA-Keycloak*"]]);

    fixture.componentRef.setInput("selected", ["privacyIDEA-Keycloak*"]);
    expect(component.isSelected(option)).toBe(true);
  });

  it("onAddCustom emits the addCustom event", () => {
    let fired = false;
    component.addCustom.subscribe(() => (fired = true));
    component.onAddCustom();
    expect(fired).toBe(true);
  });
});
