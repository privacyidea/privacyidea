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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PickerChoice, WidgetHeaderPickerComponent } from "./widget-header-picker.component";

const CHOICES: PickerChoice[] = [
  { id: "a", label: "Alpha" },
  { id: "b", label: "Beta" },
  { id: "c", label: "Gamma" }
];

describe("WidgetHeaderPickerComponent", () => {
  let fixture: ComponentFixture<WidgetHeaderPickerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetHeaderPickerComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(WidgetHeaderPickerComponent);
    fixture.componentRef.setInput("choices", CHOICES);
    fixture.componentRef.setInput("selected", CHOICES[0]);
    fixture.componentRef.setInput("tooltip", "Choose one");
    fixture.detectChanges();
  });

  function trigger(): HTMLButtonElement {
    return fixture.nativeElement.querySelector(".picker-trigger");
  }

  it("should create", () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it("should name the selected choice on the trigger, so it is legible without opening the menu", () => {
    const label = fixture.nativeElement.querySelector(".picker-label") as HTMLElement;
    expect(label.textContent?.trim()).toBe("Alpha");
  });

  it("should follow the selection it is given", () => {
    fixture.componentRef.setInput("selected", CHOICES[2]);
    fixture.detectChanges();

    const label = fixture.nativeElement.querySelector(".picker-label") as HTMLElement;
    expect(label.textContent?.trim()).toBe("Gamma");
  });

  it("should give the trigger its tooltip as accessible name", () => {
    expect(trigger().getAttribute("aria-label")).toBe("Choose one");
  });

  it("should show an icon only when one is given", () => {
    expect(trigger().querySelector("mat-icon")).toBeNull();

    fixture.componentRef.setInput("icon", "schedule");
    fixture.detectChanges();

    expect(trigger().querySelector("mat-icon")?.textContent?.trim()).toBe("schedule");
  });

  it("should report the id of the choice picked from the menu", () => {
    const picked: string[] = [];
    fixture.componentInstance.picked.subscribe((id) => picked.push(id));

    trigger().click();
    fixture.detectChanges();
    const items = Array.from(document.querySelectorAll<HTMLButtonElement>("[role=menuitemradio]"));
    expect(items.map((item) => item.getAttribute("aria-checked"))).toEqual(["true", "false", "false"]);
    items[1].click();

    expect(picked).toEqual(["b"]);
  });
});
