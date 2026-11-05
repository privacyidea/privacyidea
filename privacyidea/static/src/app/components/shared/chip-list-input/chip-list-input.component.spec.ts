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
import { TestKey } from "@angular/cdk/testing";
import { TestbedHarnessEnvironment } from "@angular/cdk/testing/testbed";
import { Component, provideZonelessChangeDetection, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatChipGridHarness, MatChipInputHarness, MatChipRowHarness } from "@angular/material/chips/testing";
import { ChipListInputComponent } from "./chip-list-input.component";

@Component({
  imports: [ChipListInputComponent],
  template: `
    <app-chip-list-input
      [values]="values()"
      label="Users"
      gridLabel="User list"
      [chipLabel]="chipLabel"
      (valuesChange)="changes.push($event)">
      <button
        chipListExtras
        class="extra-button">
        Clear
      </button>
    </app-chip-list-input>
  `
})
class HostComponent {
  readonly values = signal<string[]>(["alice", "bob", "carol"]);
  readonly changes: string[][] = [];
  chipLabel = (value: string): string => (value === "pam" ? "PAM Module" : value);
}

describe("ChipListInputComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;
  let chipList: ChipListInputComponent;
  let grid: MatChipGridHarness;
  let input: MatChipInputHarness;

  const root = (): HTMLElement => fixture.nativeElement;
  const render = async (): Promise<void> => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const rows = (): Promise<MatChipRowHarness[]> => grid.getRows();
  const rowTexts = async (): Promise<string[]> => Promise.all((await rows()).map((row) => row.getText()));

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    await render();
    chipList = fixture.debugElement.query(By.directive(ChipListInputComponent)).componentInstance;
    const loader = TestbedHarnessEnvironment.loader(fixture);
    grid = await loader.getHarness(MatChipGridHarness);
    input = (await grid.getInput())!;
  });

  it("carries the chip-list-input class on its host", () => {
    expect(root().querySelector("app-chip-list-input")!.classList).toContain("chip-list-input");
  });

  it("renders one chip row per entry, labelled through chipLabel", async () => {
    host.values.set(["alice", "pam"]);
    await render();

    expect(await rowTexts()).toEqual(["alice", "PAM Module"]);
  });

  it("names the chip grid and the field", () => {
    expect(root().querySelector("mat-chip-grid")!.getAttribute("aria-label")).toBe("User list");
    expect(root().querySelector("mat-label")!.textContent).toBe("Users");
  });

  it("gives every remove button a label that contains the displayed text", async () => {
    host.values.set(["alice", "pam"]);
    await render();

    const labels = Array.from(root().querySelectorAll("[matChipRemove]")).map((b) => b.getAttribute("aria-label"));
    expect(labels).toEqual(["Remove alice", "Remove PAM Module"]);
  });

  it("emits the trimmed entry and clears the draft on a token end", async () => {
    await input.setValue("  dave  ");
    await input.sendSeparatorKey(TestKey.ENTER);
    await render();

    expect(host.changes).toEqual([["alice", "bob", "carol", "dave"]]);
    expect(chipList.draft()).toBe("");
    expect(await input.getValue()).toBe("");
  });

  it("builds on the last emitted list when entries arrive before the parent hands the values back", async () => {
    const tokenEnd = (value: string): void =>
      (chipList as unknown as { onTokenEnd(e: { value: string }): void }).onTokenEnd({ value });

    tokenEnd("dave");
    tokenEnd("erin");

    expect(host.changes).toEqual([
      ["alice", "bob", "carol", "dave"],
      ["alice", "bob", "carol", "dave", "erin"]
    ]);

    host.values.set(["alice", "bob", "carol", "dave", "erin"]);
    await render();
    tokenEnd("frank");

    expect(host.changes[2]).toEqual(["alice", "bob", "carol", "dave", "erin", "frank"]);
  });

  it("emits nothing for an empty or whitespace-only draft", async () => {
    await input.sendSeparatorKey(TestKey.ENTER);
    await input.setValue("   ");
    await input.sendSeparatorKey(TestKey.ENTER);
    await render();

    expect(host.changes).toEqual([]);
    expect(chipList.draft()).toBe("");
  });

  it("emits nothing but clears the draft for a duplicate, which is case-sensitive", async () => {
    await input.setValue("alice");
    await input.sendSeparatorKey(TestKey.ENTER);
    await render();

    expect(host.changes).toEqual([]);
    expect(chipList.draft()).toBe("");

    await input.setValue("Alice");
    await input.sendSeparatorKey(TestKey.ENTER);
    await render();

    expect(host.changes).toEqual([["alice", "bob", "carol", "Alice"]]);
  });

  it("splits a pasted list on commas, trims it and drops blanks and duplicates", async () => {
    await input.setValue("x, y,,x , alice ,z");
    await input.sendSeparatorKey(TestKey.ENTER);
    await render();

    expect(host.changes).toEqual([["alice", "bob", "carol", "x", "y", "z"]]);
  });

  it("adds the draft on the comma key", async () => {
    await input.setValue("erin");
    const element = root().querySelector("input")!;
    const comma = new KeyboardEvent("keydown", { key: ",", keyCode: 188, bubbles: true, cancelable: true });
    Object.defineProperty(comma, "keyCode", { get: () => 188 });
    element.dispatchEvent(comma);
    await render();

    expect(host.changes).toEqual([["alice", "bob", "carol", "erin"]]);
    expect(comma.defaultPrevented).toBe(true);
  });

  it("does not add a non-empty draft on blur", async () => {
    await input.setValue("frank");
    await input.blur();
    await render();

    expect(host.changes).toEqual([]);
    expect(chipList.draft()).toBe("frank");
  });

  it("emits the filtered list when a remove button is clicked", async () => {
    const bob = (await rows())[1];
    await (await bob.getRemoveButton()).click();

    expect(host.changes).toEqual([["alice", "carol"]]);
  });

  it("emits the filtered list when Delete or Backspace is pressed on a focused chip", async () => {
    const [alice, , carol] = await rows();
    await alice.remove();
    await (await carol.host()).sendKeys(TestKey.BACKSPACE);

    expect(host.changes).toEqual([
      ["bob", "carol"],
      ["alice", "bob"]
    ]);
  });

  it("keeps the chip rows when the values input changes", async () => {
    const before = Array.from(root().querySelectorAll("mat-chip-row"));
    host.values.set(["alice", "bob", "carol", "dave"]);
    await render();

    const after = Array.from(root().querySelectorAll("mat-chip-row"));
    expect(after).toHaveLength(4);
    expect(after.slice(0, 3)).toEqual(before);
  });

  it("moves focus to a chip after a middle chip is removed with Delete", async () => {
    const bob = (await rows())[1];
    await (await bob.host()).focus();
    await bob.remove();
    host.values.set(["alice", "carol"]);
    await render();

    expect(document.activeElement!.closest("mat-chip-row")).not.toBeNull();
  });

  it("moves focus to the input after the last chip is removed", async () => {
    host.values.set(["alice"]);
    await render();
    const alice = (await rows())[0];
    await (await alice.host()).focus();
    await alice.remove();
    host.values.set([]);
    await render();

    expect(document.activeElement).toBe(root().querySelector("input"));
  });

  it("gives each chip the displayed label as its title, for an entry the chip clips", async () => {
    host.values.set(["pam", "alice"]);
    await render();

    const titles = Array.from(root().querySelectorAll("mat-chip-row")).map((row) => row.getAttribute("title"));
    expect(titles).toEqual(["PAM Module", "alice"]);
  });

  it("renders the projected extras below the field", () => {
    const extras = root().querySelector(".chip-list-extras .extra-button");
    expect(extras!.textContent!.trim()).toBe("Clear");
  });
});
