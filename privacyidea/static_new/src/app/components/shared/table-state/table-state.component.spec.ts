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
import { Component, signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TableState } from "@core/models/table_state/table-state";
import { TableStateComponent } from "./table-state.component";

// The pages that own a table project their way out of an empty list into the panel - the realm
// selector above all, which the panel replaces while it is on screen.
@Component({
  imports: [TableStateComponent],
  template: `
    <app-table-state
      [table]="table"
      heading="No entries yet">
      <button>Select Realm</button>
    </app-table-state>
  `
})
class ProjectedActionHostComponent {
  table!: TableState;
}

describe("TableStateComponent", () => {
  let fixture: ComponentFixture<TableStateComponent>;

  let value: WritableSignal<unknown>;
  let error: WritableSignal<unknown>;
  let count: WritableSignal<number>;
  let filterActive: WritableSignal<boolean>;
  let isLoading: WritableSignal<boolean>;
  let reload: jest.Mock;
  let resetFilter: jest.Mock | undefined;
  let cancel: jest.Mock | undefined;

  const buildState = (options: { withResetFilter?: boolean; withCancel?: boolean } = {}): TableState => {
    const { withResetFilter = true, withCancel = false } = options;
    reload = jest.fn();
    resetFilter = withResetFilter ? jest.fn() : undefined;
    cancel = withCancel
      ? jest.fn(() => {
          value.set(undefined);
          isLoading.set(false);
        })
      : undefined;
    return new TableState({
      resource: {
        hasValue: () => value() !== undefined,
        error: () => error(),
        isLoading: () => isLoading(),
        reload
      },
      count: () => count(),
      filterActive: () => filterActive(),
      resetFilter,
      cancel
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
    isLoading = signal(false);
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
      resource: { hasValue: () => true, error: () => null, isLoading: () => false, reload: jest.fn() },
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

  describe("while the request is still out", () => {
    it("speaks for the load itself rather than letting a table of placeholders do it", () => {
      value.set(undefined);
      const state = buildState();
      render(state);

      expect(state.status()).toBe("loading");
      // The page draws this panel instead of the table, so the load and both of its outcomes all
      // happen in the same place and nothing is put on screen only to be taken away.
      expect(state.showTable()).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-progress-spinner")).not.toBeNull();
      expect(fixture.nativeElement.querySelector("mat-icon")).toBeNull();
      expect(text()).not.toContain("No entries yet");
    });

    it("fills in around the spinner when the list turns out to be empty", () => {
      value.set(undefined);
      const state = buildState();
      render(state);
      expect(fixture.nativeElement.querySelector("mat-progress-spinner")).not.toBeNull();

      value.set({});
      fixture.detectChanges();

      expect(state.status()).toBe("empty");
      expect(fixture.nativeElement.querySelector("mat-progress-spinner")).toBeNull();
      expect(text()).toContain("No entries yet");
    });

    it("hands the page its table once rows arrive", () => {
      value.set(undefined);
      const state = buildState();
      render(state);
      expect(state.showTable()).toBe(false);

      value.set({});
      count.set(3);
      fixture.detectChanges();

      expect(state.status()).toBe("ready");
      expect(state.showTable()).toBe(true);
    });
  });

  describe("when a load hangs and the user stops waiting", () => {
    const startHangingLoad = (options: { withCancel?: boolean } = {}): TableState => {
      value.set(undefined);
      isLoading.set(true);
      const state = buildState({ withCancel: options.withCancel ?? true });
      render(state);
      return state;
    };

    it("leaves the panel as it was where the table cannot stop its load", () => {
      const state = startHangingLoad({ withCancel: false });

      expect(state.status()).toBe("loading");
      expect(state.canCancel).toBe(false);
      expect(buttonLabelled("Cancel")).toBeUndefined();
    });

    it("offers to stop the load, held back until the load has run a moment", () => {
      const state = startHangingLoad();
      const button = buttonLabelled("Cancel")!;

      expect(state.canCancel).toBe(true);
      expect(button).toBeDefined();
      // The wait before the offer appears is the animation's delay, which nothing here can measure.
      // The class is what carries it, and losing it would put the button on screen right away.
      expect(button.classList).toContain("delayed-reveal");

      button.click();
      expect(cancel).toHaveBeenCalled();
    });

    it("reports the stopped load rather than a spinner no request stands behind", () => {
      const state = startHangingLoad();
      expect(fixture.nativeElement.querySelector("mat-progress-spinner")).not.toBeNull();

      buttonLabelled("Cancel")!.click();
      fixture.detectChanges();

      expect(state.status()).toBe("cancelled");
      // The page keeps drawing the panel instead of the table, as it did while the load was out.
      expect(state.showTable()).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-progress-spinner")).toBeNull();
      expect(text()).toContain("Loading cancelled");
    });

    it("takes the load up again when it is retried", () => {
      const state = startHangingLoad();
      buttonLabelled("Cancel")!.click();
      fixture.detectChanges();

      buttonLabelled("Try Again")!.click();
      fixture.detectChanges();

      expect(reload).toHaveBeenCalled();
      expect(state.status()).toBe("loading");
    });

    it("clears the stopped state as soon as a request is in flight again", () => {
      // A realm picked after the cancel starts a new request without going through the retry button,
      // so the panel has to follow the resource rather than stay on the outcome of the load before.
      const state = startHangingLoad();
      buttonLabelled("Cancel")!.click();
      expect(state.status()).toBe("cancelled");

      isLoading.set(true);

      expect(state.status()).toBe("loading");
    });

    it("keeps the page's own way out reachable once the load was stopped", () => {
      // The panel replaces the realm selector while it is on screen. Without it a stopped load is a
      // dead end, because the realm is what the user has to change to get a list at all.
      value.set(undefined);
      isLoading.set(true);
      const state = buildState({ withCancel: true });
      const hostFixture = TestBed.createComponent(ProjectedActionHostComponent);
      hostFixture.componentInstance.table = state;
      hostFixture.detectChanges();

      expect(hostFixture.nativeElement.textContent).not.toContain("Select Realm");

      state.cancel();
      hostFixture.detectChanges();

      expect(state.status()).toBe("cancelled");
      expect(hostFixture.nativeElement.textContent).toContain("Select Realm");
    });
  });
});
