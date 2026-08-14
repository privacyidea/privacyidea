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
import { DetailsDefaultValueCellComponent } from "./details-default-value-cell.component";

describe("DetailsDefaultValueCellComponent", () => {
  let fixture: ComponentFixture<DetailsDefaultValueCellComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [DetailsDefaultValueCellComponent] });
    fixture = TestBed.createComponent(DetailsDefaultValueCellComponent);
    fixture.componentRef.setInput("value", "42");
  });

  it("shows displayText in a span when not editing", () => {
    fixture.componentRef.setInput("displayText", "forty-two");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("input, textarea")).toBeNull();
    expect(fixture.nativeElement.querySelector("span")?.textContent).toContain("forty-two");
  });

  it("shows a number input when editing and isNumber is true", () => {
    fixture.componentRef.setInput("isEditing", true);
    fixture.componentRef.setInput("isNumber", true);
    fixture.detectChanges();

    const input: HTMLInputElement | null = fixture.nativeElement.querySelector("input[type=number]");
    expect(input).not.toBeNull();
    expect(input?.value).toBe("42");
  });

  it("shows a textarea when editing and isNumber is false", () => {
    fixture.componentRef.setInput("isEditing", true);
    fixture.componentRef.setInput("isNumber", false);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("textarea")).not.toBeNull();
    expect(fixture.nativeElement.querySelector("input[type=number]")).toBeNull();
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
