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
import { Component, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FilterAutocompleteDirective, filterKeywordCompletion } from "./filter-autocomplete.directive";

const KEYWORDS = ["serial", "type", "user", "userid", "rollout_state"];

@Component({
  standalone: true,
  imports: [FilterAutocompleteDirective],
  template: `<div class="input-container">
    <input
      #field
      [appFilterAutocomplete]="keywords" />
  </div>`
})
class HostComponent {
  @ViewChild("field") field!: { nativeElement: HTMLInputElement };
  keywords = KEYWORDS;
}

describe("filterKeywordCompletion", () => {
  it("completes a unique prefix and appends the separator", () => {
    expect(filterKeywordCompletion("ser", 3, KEYWORDS)).toBe("ial: ");
  });

  it("returns only the separator when the token is already a keyword", () => {
    expect(filterKeywordCompletion("user", 4, KEYWORDS)).toBe(": ");
  });

  it("prefers the shortest match on an ambiguous prefix", () => {
    expect(filterKeywordCompletion("us", 2, KEYWORDS)).toBe("er: ");
  });

  it("ignores case", () => {
    expect(filterKeywordCompletion("ROLL", 4, KEYWORDS)).toBe("out_state: ");
  });

  it("completes the token at the cursor, not the whole value", () => {
    expect(filterKeywordCompletion("type: hotp ser", 14, KEYWORDS)).toBe("ial: ");
  });

  it("treats a comma as a separator", () => {
    expect(filterKeywordCompletion("type: hotp,ser", 14, KEYWORDS)).toBe("ial: ");
  });

  it("returns nothing without a token", () => {
    expect(filterKeywordCompletion("type: hotp ", 11, KEYWORDS)).toBe("");
  });

  it("returns nothing once the token has a value part", () => {
    expect(filterKeywordCompletion("type:", 5, KEYWORDS)).toBe("");
  });

  it("returns nothing for an unknown prefix", () => {
    expect(filterKeywordCompletion("xyz", 3, KEYWORDS)).toBe("");
  });
});

describe("FilterAutocompleteDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let input: HTMLInputElement;

  const type = (value: string) => {
    input.value = value;
    input.setSelectionRange(value.length, value.length);
    input.dispatchEvent(new Event("input"));
  };

  const ghostSuffix = () => fixture.nativeElement.querySelector(".filter-autocomplete-suffix") as HTMLElement | null;

  const ghost = () => fixture.nativeElement.querySelector(".filter-autocomplete-ghost") as HTMLElement;

  const pressTab = () => {
    const event = new KeyboardEvent("keydown", { key: "Tab", cancelable: true });
    input.dispatchEvent(event);
    return event;
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    input = fixture.componentInstance.field.nativeElement;
    input.focus();
  });

  it("shows the completion of the current token", () => {
    type("ser");
    expect(ghostSuffix()?.textContent).toBe("ial: ");
    expect(ghost().style.display).toBe("flex");
  });

  it("mirrors the typed text so the completion lines up", () => {
    type("type: hotp us");
    const prefix = fixture.nativeElement.querySelector(".filter-autocomplete-prefix") as HTMLElement;
    expect(prefix.textContent).toBe("type: hotp us");
    expect(ghostSuffix()?.textContent).toBe("er: ");
  });

  it("accepts the completion on Tab and notifies the host", () => {
    const onInput = jest.fn();
    input.addEventListener("input", onInput);
    type("ser");
    onInput.mockClear();

    const event = pressTab();

    expect(event.defaultPrevented).toBe(true);
    expect(input.value).toBe("serial: ");
    expect(input.selectionStart).toBe(8);
    expect(onInput).toHaveBeenCalledTimes(1);
  });

  it("leaves Tab alone when there is nothing to complete", () => {
    type("xyz");
    expect(pressTab().defaultPrevented).toBe(false);
  });

  it("hides the completion on Escape", () => {
    type("ser");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", cancelable: true }));
    expect(ghost().style.display).toBe("none");
    expect(pressTab().defaultPrevented).toBe(false);
  });

  it("hides the completion when the cursor is not at the end", () => {
    input.value = "ser hotp";
    input.setSelectionRange(3, 3);
    input.dispatchEvent(new Event("input"));
    expect(ghost().style.display).toBe("none");
  });

  it("hides the completion on blur", () => {
    type("ser");
    input.dispatchEvent(new Event("blur"));
    expect(ghost().style.display).toBe("none");
  });

  it("removes the ghost element on destroy", () => {
    fixture.destroy();
    expect(fixture.nativeElement.querySelector(".filter-autocomplete-ghost")).toBeNull();
  });
});
