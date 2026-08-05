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
import { LightSourceDialComponent, LightSourceDialItem } from "./light-source-dial.component";

describe("LightSourceDialComponent", () => {
  let fixture: ComponentFixture<LightSourceDialComponent>;
  let component: LightSourceDialComponent;

  const items: LightSourceDialItem[] = [
    { slot: 1, value: "a", label: "Item A" },
    { slot: 5, value: "b", label: "Item B" },
    { slot: 12, value: "c", label: "Item C" }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LightSourceDialComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(LightSourceDialComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("items", items);
    fixture.componentRef.setInput("legend", "Test dial");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render one radio per item, in a single native group", () => {
    const radios = fixture.nativeElement.querySelectorAll<HTMLInputElement>(".dial__slot input");

    expect(radios).toHaveLength(items.length);
    expect([...radios].every((radio) => radio.name === "light-source-dial")).toBe(true);
  });

  it("should honor a custom group name", () => {
    fixture.componentRef.setInput("groupName", "appearance-preset");
    fixture.detectChanges();

    const radios = fixture.nativeElement.querySelectorAll<HTMLInputElement>(".dial__slot input");
    expect([...radios].every((radio) => radio.name === "appearance-preset")).toBe(true);
  });

  it("should place each slot at its stop's angle", () => {
    const slots = fixture.nativeElement.querySelectorAll<HTMLElement>(".dial__slot");

    expect(slots[0].className).toContain("dial__slot--1");
    expect(slots[1].className).toContain("dial__slot--5");
    expect(slots[2].className).toContain("dial__slot--12");
  });

  it("should check the item matching the selected value", () => {
    fixture.componentRef.setInput("selected", "b");
    fixture.detectChanges();

    const checked = [...fixture.nativeElement.querySelectorAll<HTMLInputElement>(".dial__slot input")].filter(
      (radio) => radio.checked
    );

    expect(checked).toHaveLength(1);
    expect(checked[0].closest(".dial__slot")?.className).toContain("dial__slot--5");
  });

  it("should check nothing when the selected value matches no item", () => {
    fixture.componentRef.setInput("selected", "does-not-exist");
    fixture.detectChanges();

    const checked = [...fixture.nativeElement.querySelectorAll<HTMLInputElement>(".dial__slot input")].filter(
      (radio) => radio.checked
    );

    expect(checked).toHaveLength(0);
  });

  it("should emit the value of the item turned to", () => {
    const values: string[] = [];
    component.pick.subscribe((value) => values.push(value));

    const radios = fixture.nativeElement.querySelectorAll<HTMLInputElement>(".dial__slot input");
    radios[2].checked = true;
    radios[2].dispatchEvent(new Event("change"));

    expect(values).toEqual(["c"]);
  });

  it("should use each item's label as its tooltip and accessible text", () => {
    const labels = fixture.nativeElement.querySelectorAll<HTMLElement>(".dial__hidden-text");
    // First hidden-text node is the legend; the rest are one per slot.
    expect(labels[1].textContent?.trim()).toBe("Item A");
    expect(labels[2].textContent?.trim()).toBe("Item B");
    expect(labels[3].textContent?.trim()).toBe("Item C");
  });
});
