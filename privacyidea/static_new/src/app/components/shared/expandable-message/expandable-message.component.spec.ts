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
import { ExpandableMessageComponent } from "./expandable-message.component";

const LONG = "Your account is locked. Please try again in about {duration}.";
const SHORT = "Locked.";

describe("ExpandableMessageComponent", () => {
  let fixture: ComponentFixture<ExpandableMessageComponent>;
  let component: ExpandableMessageComponent;

  const withText = (text: string | null) => {
    fixture.componentRef.setInput("text", text);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpandableMessageComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ExpandableMessageComponent);
    component = fixture.componentInstance;
  });

  it("shows a dash when there is nothing to show", () => {
    withText(null);
    expect(fixture.nativeElement.textContent.trim()).toBe("-");
    expect(fixture.nativeElement.querySelector("button")).toBeNull();
  });

  it("offers no toggle for text the clamp would not hide", () => {
    withText(SHORT);
    expect(fixture.nativeElement.textContent).toContain(SHORT);
    expect(fixture.nativeElement.querySelector("button")).toBeNull();
  });

  it("expands and collapses long text in place", () => {
    withText(LONG);
    const button = fixture.nativeElement.querySelector("button");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    // Clamped, but present in the DOM either way - so the text stays selectable and reachable by search.
    expect(fixture.nativeElement.querySelector(".expandable-message__text--clamped")).toBeTruthy();

    button.click();
    fixture.detectChanges();
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(fixture.nativeElement.querySelector(".expandable-message__text--clamped")).toBeNull();
  });

  it("keeps the whole message in the DOM while it is clamped", () => {
    // The clamp is CSS. Shortening the string instead would look the same on screen but put the rest of the
    // message out of reach of selection, copy, browser search and a screen reader - so what the element
    // *contains* is the part worth pinning. Whether it renders on one line is a layout question jsdom cannot
    // answer: it has no layout engine, so text-overflow and max-width have no measurable effect here.
    withText(LONG);
    const text = fixture.nativeElement.querySelector(".expandable-message__text");
    expect(text.classList).toContain("expandable-message__text--clamped");
    expect(text.textContent.trim()).toBe(LONG);

    fixture.nativeElement.querySelector("button").click();
    fixture.detectChanges();
    expect(text.textContent.trim()).toBe(LONG);
  });

  it("points aria-controls at its own text", () => {
    // A table renders one of these per row; each has to control its own text and not another row's.
    withText(LONG);
    const button = fixture.nativeElement.querySelector("button");
    const text = fixture.nativeElement.querySelector(".expandable-message__text");
    expect(button.getAttribute("aria-controls")).toBe(text.id);
    expect(text.id).toBeTruthy();
  });

  it("collapses again when the row is handed different text", () => {
    // Table rows are reused across pages and sorts; a cell that kept its height would describe the old row.
    withText(LONG);
    fixture.nativeElement.querySelector("button").click();
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    withText(LONG + " Contact your administrator.");
    expect(component.expanded()).toBe(false);
  });
});
