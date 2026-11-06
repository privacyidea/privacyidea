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
import { Component, provideZonelessChangeDetection, signal, viewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatTooltip } from "@angular/material/tooltip";
import { ToggleGroupComponent } from "./toggle-group.component";

@Component({
  imports: [ToggleGroupComponent],
  template: `
    <app-toggle-group
      [values]="values()"
      [labels]="labels()"
      groupLabel="Mode"
      [disabled]="disabled()"
      [hideSelectionIndicator]="hideIndicator()"
      [value]="value()"
      (valueChange)="changes.push($event)" />
  `
})
class HostComponent {
  readonly group = viewChild.required(ToggleGroupComponent);
  readonly values = signal<readonly (string | number)[]>(["a", "b", "c"]);
  readonly labels = signal<readonly string[] | undefined>(undefined);
  readonly disabled = signal(false);
  readonly hideIndicator = signal(false);
  readonly value = signal<string | number | undefined>("b");
  readonly changes: (string | number | undefined)[] = [];
}

describe("ToggleGroupComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  const root = (): HTMLElement => fixture.nativeElement;
  const radios = (): HTMLButtonElement[] => Array.from(root().querySelectorAll<HTMLButtonElement>("[role=radio]"));
  const checked = (): string[] =>
    radios()
      .filter((radio) => radio.getAttribute("aria-checked") === "true")
      .map((radio) => radio.textContent!.trim());
  const tabStops = (): string[] =>
    radios()
      .filter((radio) => radio.tabIndex === 0)
      .map((radio) => radio.textContent!.trim());
  const render = async (): Promise<void> => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const press = (button: HTMLElement, keyCode: number): void => {
    button.dispatchEvent(new KeyboardEvent("keydown", { keyCode, bubbles: true, cancelable: true }));
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    await render();
  });

  it("carries the app-toggle-group class on its host", () => {
    expect(root().querySelector("app-toggle-group")!.classList).toContain("app-toggle-group");
  });

  it("renders one radio per value inside a labelled radiogroup", () => {
    expect(radios().map((radio) => radio.textContent!.trim())).toEqual(["a", "b", "c"]);
    const group = root().querySelector("[role=radiogroup]")!;
    expect(group.getAttribute("aria-label")).toBe("Mode");
  });

  it("marks exactly the bound value as checked and moves the mark on a click", async () => {
    expect(checked()).toEqual(["b"]);

    radios()[2].click();
    await render();

    expect(checked()).toEqual(["c"]);
  });

  it("emits valueChange for a click but not for a programmatic value change", async () => {
    host.value.set("c");
    await render();
    expect(host.changes).toEqual([]);
    expect(checked()).toEqual(["c"]);

    radios()[0].click();
    await render();

    expect(host.changes).toEqual(["a"]);
  });

  it("selects and emits the neighbour on ArrowRight and ArrowLeft", async () => {
    press(radios()[1], 39);
    await render();
    expect(checked()).toEqual(["c"]);
    expect(host.changes).toEqual(["c"]);

    press(radios()[2], 37);
    await render();
    expect(checked()).toEqual(["b"]);
    expect(host.changes).toEqual(["c", "b"]);
  });

  it("ignores clicks while disabled and keeps showing the selection", async () => {
    host.disabled.set(true);
    await render();

    radios()[0].click();
    await render();

    expect(host.changes).toEqual([]);
    expect(checked()).toEqual(["b"]);
    expect(radios().every((radio) => radio.disabled)).toBe(true);
  });

  it("shows the check mark by default and drops it with hideSelectionIndicator", async () => {
    expect(root().querySelector(".mat-pseudo-checkbox")).not.toBeNull();

    host.hideIndicator.set(true);
    await render();

    expect(root().querySelector(".mat-pseudo-checkbox")).toBeNull();
  });

  it("selects a numeric value", async () => {
    host.values.set([1, 2, 3]);
    host.value.set(2);
    await render();

    expect(checked()).toEqual(["2"]);
    radios()[2].click();
    await render();
    expect(host.changes).toEqual([3]);
  });

  it("selects the empty-string value and labels it from labels", async () => {
    host.values.set(["", "x"]);
    host.labels.set(["None", "X"]);
    host.value.set("");
    await render();

    expect(checked()).toEqual(["None"]);
  });

  it("shows no selection for a value that is not in values", async () => {
    host.value.set("zzz");
    await render();

    expect(checked()).toEqual([]);
    expect(tabStops()).toEqual(["a"]);
  });

  it("shows no selection for an undefined value", async () => {
    host.value.set(undefined);
    await render();

    expect(checked()).toEqual([]);
  });

  it("keeps exactly one Tab stop on the selected toggle", () => {
    expect(tabStops()).toEqual(["b"]);
  });

  it("keeps exactly one Tab stop when values are appended after init", async () => {
    host.values.set(["a", "b", "c", "d", "e"]);
    await render();

    expect(tabStops()).toEqual(["b"]);
  });

  it("keeps exactly one Tab stop when a value is prepended after init", async () => {
    host.values.set(["z", "a", "b", "c"]);
    await render();

    expect(checked()).toEqual(["b"]);
    expect(tabStops()).toEqual(["b"]);
  });

  it("makes a toggle prepended after init the only Tab stop while nothing is selected", async () => {
    host.value.set(undefined);
    await render();
    host.values.set(["z", "a", "b", "c"]);
    await render();

    expect(checked()).toEqual([]);
    expect(tabStops()).toEqual(["z"]);
  });

  it("moves the Tab stop with the selection", async () => {
    radios()[0].click();
    await render();
    host.value.set("a");
    await render();

    expect(tabStops()).toEqual(["a"]);
  });

  it("falls back from a label to the value, also for an empty label", async () => {
    host.labels.set(["Alpha", "", undefined as unknown as string]);
    await render();

    expect(radios().map((radio) => radio.textContent!.trim())).toEqual(["Alpha", "b", "c"]);
  });

  it("falls back to String(value) when no labels are given", async () => {
    host.values.set([1, 2]);
    await render();

    expect(radios().map((radio) => radio.textContent!.trim())).toEqual(["1", "2"]);
  });

  it("shows the full label as a tooltip on the toggle when its label content is clipped", async () => {
    host.labels.set(["Alpha", "Beta", "Gamma"]);
    await render();
    const toggle = fixture.debugElement.queryAll(By.css("mat-button-toggle"))[0];
    const content = toggle.nativeElement.querySelector(".mat-button-toggle-label-content") as HTMLElement;
    Object.defineProperty(content, "scrollWidth", { value: 300, configurable: true });
    Object.defineProperty(content, "clientWidth", { value: 100, configurable: true });

    toggle.nativeElement.dispatchEvent(new MouseEvent("mouseenter"));

    const tooltip = toggle.injector.get(MatTooltip);
    expect(tooltip.disabled).toBe(false);
    expect(tooltip.message).toBe("Alpha");
  });

  it("shows no tooltip on a toggle whose label fits", () => {
    const toggle = fixture.debugElement.queryAll(By.css("mat-button-toggle"))[1];

    toggle.nativeElement.dispatchEvent(new MouseEvent("mouseenter"));

    expect(toggle.injector.get(MatTooltip).disabled).toBe(true);
  });

  describe("focus()", () => {
    beforeEach(() => {
      root()
        .querySelectorAll("button")
        .forEach((button) => button.blur());
    });

    it("focuses the checked toggle", () => {
      host.group().focus();

      expect(document.activeElement).toBe(radios()[1]);
    });

    it("falls back to the first toggle while nothing is checked", async () => {
      host.value.set(undefined);
      await render();

      host.group().focus();

      expect(document.activeElement).toBe(radios()[0]);
    });

    it("does nothing for an empty group", async () => {
      host.values.set([]);
      await render();

      expect(() => host.group().focus()).not.toThrow();
    });
  });
});
