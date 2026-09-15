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
import { DetailsDescriptionCellComponent } from "./details-description-cell.component";

describe("DetailsDescriptionCellComponent", () => {
  let fixture: ComponentFixture<DetailsDescriptionCellComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [DetailsDescriptionCellComponent] });
    fixture = TestBed.createComponent(DetailsDescriptionCellComponent);
    fixture.componentRef.setInput("value", "a description");
  });

  it("shows plain text when not editing", () => {
    fixture.componentRef.setInput("isEditing", false);
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector("textarea")).toBeNull();
    expect(el.querySelector(".details-description-div")?.textContent).toContain("a description");
  });

  it("shows an editable textarea when editing", () => {
    fixture.componentRef.setInput("isEditing", true);
    fixture.detectChanges();

    const textarea: HTMLTextAreaElement | null = fixture.nativeElement.querySelector("textarea");
    expect(textarea).not.toBeNull();
    expect(textarea?.value).toBe("a description");
  });

  it("updates the value model on input", () => {
    fixture.componentRef.setInput("isEditing", true);
    fixture.detectChanges();

    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector("textarea");
    textarea.value = "changed";
    textarea.dispatchEvent(new Event("input"));

    expect(fixture.componentInstance.value()).toBe("changed");
  });
});
