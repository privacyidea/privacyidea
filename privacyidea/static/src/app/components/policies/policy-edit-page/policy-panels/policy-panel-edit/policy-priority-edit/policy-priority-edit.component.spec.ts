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
import { PolicyPriorityEditComponent } from "./policy-priority-edit.component";

describe("PolicyPriorityEditComponent", () => {
  let component: PolicyPriorityEditComponent;
  let fixture: ComponentFixture<PolicyPriorityEditComponent>;

  const input = (): HTMLInputElement => fixture.debugElement.query(By.css("input")).nativeElement;
  const kinds = (): string[] =>
    component
      .priorityField()
      .errors()
      .map((error) => error.kind);
  const errorTexts = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) => (e as HTMLElement).textContent!.trim());
  const type = (value: string): void => {
    input().value = value;
    input().dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };
  /** jsdom has no validity.badInput, so a bad number input is simulated by stubbing it. */
  const typeUnparsable = (): void => {
    jest.spyOn(input(), "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
    type("");
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyPriorityEditComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyPriorityEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("priority", 10);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show the priority in the number input", () => {
    expect(input().type).toBe("number");
    expect(input().value).toBe("10");
    expect(component.valid()).toBe(true);
  });

  it("should write a typed number to the model and mark the field dirty", () => {
    expect(component.priorityField().dirty()).toBe(false);

    type("20");

    expect(component.priority()).toBe(20);
    expect(component.priorityField().dirty()).toBe(true);
    expect(component.valid()).toBe(true);
  });

  it("should emit priorityChange with the typed number", () => {
    const emitted: (number | null)[] = [];
    component.priority.subscribe((value) => emitted.push(value));

    type("7");

    expect(emitted).toEqual([7]);
  });

  it("should write null, not 0, when the input is emptied and report it as required", () => {
    type("");

    expect(component.priority()).toBeNull();
    expect(kinds()).toEqual(["required"]);
    expect(component.valid()).toBe(false);
  });

  it.each([0, -3])("should reject the priority %s with a min error", (priority) => {
    type(String(priority));

    expect(component.priority()).toBe(priority);
    expect(kinds()).toEqual(["min"]);
    expect(component.valid()).toBe(false);
  });

  it("should accept the lowest priority 1", () => {
    type("1");

    expect(kinds()).toEqual([]);
    expect(component.valid()).toBe(true);
  });

  it("should keep the model and report a parse error for text the browser cannot parse", () => {
    typeUnparsable();

    expect(component.priority()).toBe(10);
    expect(kinds()).toEqual(["parse"]);
    expect(component.valid()).toBe(false);
  });

  it("should accept a priority that the parent sets to 0 and report it as too small", async () => {
    fixture.componentRef.setInput("priority", 0);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(kinds()).toEqual(["min"]);
  });

  describe("error messages", () => {
    it("should show no message while the priority is valid", () => {
      expect(errorTexts()).toEqual([]);
    });

    it("should show the required message once the field was touched", () => {
      type("");
      expect(errorTexts()).toEqual([]);

      input().dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(errorTexts()).toEqual(["Priority is required."]);
    });

    it("should show the minimum message for a priority below 1", () => {
      type("0");
      input().dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(errorTexts()).toEqual(["Priority must be at least 1."]);
    });

    it("should show the number message for text the browser cannot parse", () => {
      typeUnparsable();
      input().dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(errorTexts()).toContain("Enter a valid number.");
    });
  });
});
