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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FIRST_LOAD_GRACE_MS, TableState } from "@core/models/table_state/table-state";
import { TableStateComponent } from "./table-state.component";

describe("TableStateComponent", () => {
  let fixture: ComponentFixture<TableStateComponent>;

  let value: WritableSignal<unknown>;
  let error: WritableSignal<unknown>;
  let count: WritableSignal<number>;
  let filterActive: WritableSignal<boolean>;
  let reload: jest.Mock;
  let resetFilter: jest.Mock | undefined;

  const buildState = (options: { withResetFilter?: boolean } = {}): TableState => {
    const { withResetFilter = true } = options;
    reload = jest.fn();
    resetFilter = withResetFilter ? jest.fn() : undefined;
    return new TableState({
      resource: {
        hasValue: () => value() !== undefined,
        error: () => error(),
        reload
      },
      count: () => count(),
      filterActive: () => filterActive(),
      resetFilter
    });
  };

  const render = (state: TableState): void => {
    fixture = TestBed.createComponent(TableStateComponent);
    fixture.componentRef.setInput("table", state);
    fixture.componentRef.setInput("heading", "No entries yet");
    fixture.componentRef.setInput("hint", "Create one to get started.");
    fixture.detectChanges();
  };

  const text = (): string => fixture.nativeElement.textContent;
  const buttonLabelled = (label: string): HTMLButtonElement | undefined =>
    Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((button) =>
      button.textContent?.includes(label)
    );

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({ imports: [TableStateComponent] }).compileComponents();

    value = signal<unknown>({});
    error = signal<unknown>(null);
    count = signal(0);
    filterActive = signal(false);
  });

  it("shows the caller's wording when the list is simply empty", () => {
    render(buildState());

    expect(text()).toContain("No entries yet");
    expect(text()).toContain("Create one to get started.");
  });

  it("offers the filter as the way out when a filter hides every row", () => {
    filterActive.set(true);
    const state = buildState();
    render(state);

    expect(state.status()).toBe("filtered");
    expect(text()).toContain("No entries match the filter");

    buttonLabelled("Reset Filter")!.click();
    expect(resetFilter).toHaveBeenCalled();
  });

  it("says so without offering an action when the list may not be read", () => {
    const state = new TableState({
      resource: { hasValue: () => true, error: () => null, reload: jest.fn() },
      count: () => 0,
      allowed: () => false
    });
    render(state);

    expect(state.status()).toBe("denied");
    expect(text()).toContain("Not allowed");
    expect(buttonLabelled("Try Again")).toBeUndefined();
  });

  describe("when the request failed", () => {
    it("offers a retry", () => {
      error.set(new Error("boom"));
      const state = buildState();
      render(state);

      expect(state.status()).toBe("error");
      buttonLabelled("Try Again")!.click();
      expect(reload).toHaveBeenCalled();
    });

    it("also offers to clear the filter, so a filter that causes the failure is not a dead end", () => {
      // The panel replaces the filter row, so retrying is the only control left. Where the request
      // carries the filter, retrying repeats exactly what failed and the user cannot reach the
      // filter to change it.
      error.set(new Error("boom"));
      filterActive.set(true);
      const state = buildState();
      render(state);

      expect(state.status()).toBe("error");
      expect(buttonLabelled("Try Again")).toBeDefined();

      buttonLabelled("Reset Filter")!.click();
      expect(resetFilter).toHaveBeenCalled();
    });

    it("offers only the retry when no filter is narrowing the list", () => {
      error.set(new Error("boom"));
      const state = buildState();
      render(state);

      expect(buttonLabelled("Reset Filter")).toBeUndefined();
    });

    it("offers only the retry when the table has no filter to reset", () => {
      error.set(new Error("boom"));
      filterActive.set(true);
      const state = buildState({ withResetFilter: false });
      render(state);

      expect(buttonLabelled("Reset Filter")).toBeUndefined();
      expect(buttonLabelled("Try Again")).toBeDefined();
    });
  });

  describe("while the first load is still out", () => {
    it("draws neither the table nor the panel, so a short load cannot flash one and take it away", () => {
      value.set(undefined);
      const state = buildState();
      render(state);

      expect(state.status()).toBe("loading");
      expect(state.showTable()).toBe(false);
      expect(text().trim()).toBe("");
      expect(fixture.nativeElement.querySelector("mat-icon")).toBeNull();
    });

    it("hands the table its placeholder rows once the load turns out to be a slow one", async () => {
      value.set(undefined);
      const state = buildState();
      render(state);

      await new Promise((resolve) => setTimeout(resolve, FIRST_LOAD_GRACE_MS + 20));

      expect(state.status()).toBe("loading");
      expect(state.showTable()).toBe(true);
    });

    it("goes straight to the empty panel when the load resolves inside the window", () => {
      value.set(undefined);
      const state = buildState();
      render(state);
      expect(state.showTable()).toBe(false);

      value.set({});
      fixture.detectChanges();

      expect(state.status()).toBe("empty");
      expect(text()).toContain("No entries yet");
    });
  });
});
