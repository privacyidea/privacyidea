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
import { By } from "@angular/platform-browser";
import { PolicyActionSearchComponent } from "./policy-action-search.component";

describe("PolicyActionSearchComponent", () => {
  let component: PolicyActionSearchComponent;
  let fixture: ComponentFixture<PolicyActionSearchComponent>;
  let input: HTMLInputElement;
  const clearButton = (): HTMLButtonElement =>
    fixture.debugElement.query(By.css("app-clear-button button")).nativeElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [PolicyActionSearchComponent] }).compileComponents();
    fixture = TestBed.createComponent(PolicyActionSearchComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("actionFilter", "token");
    fixture.detectChanges();
    input = fixture.debugElement.query(By.css("input")).nativeElement;
  });

  it("reports no selection while focus is elsewhere", () => {
    expect(component.focusState()).toBeNull();
  });

  it("reports the caret range and its direction while the input has focus", () => {
    input.focus();
    input.setSelectionRange(1, 3, "backward");

    expect(component.focusState()).toEqual({ start: 1, end: 3, direction: "backward" });
  });

  it("reports the clear button while it has focus", () => {
    clearButton().focus();

    expect(component.focusState()).toBe("clear-button");
  });

  it("takes focus at the given caret range and direction", () => {
    component.takeFocus({ start: 2, end: 4, direction: "backward" });

    expect(document.activeElement).toBe(input);
    expect([input.selectionStart, input.selectionEnd, input.selectionDirection]).toEqual([2, 4, "backward"]);
  });

  it("puts focus back on the clear button when that is where it was", () => {
    component.takeFocus("clear-button");

    expect(document.activeElement).toBe(clearButton());
  });
});
