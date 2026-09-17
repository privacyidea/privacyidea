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
import { signal } from "@angular/core";
import { TableState, TableStateResource } from "./table-state";

/**
 * A fake resembling Angular's own httpResource(): hasValue() drops to false the instant a reload
 * starts, exactly like the real resource.error()/hasValue() do (see _resource-chunk.mjs) - the
 * behaviour this whole file exists to not be destroyed by.
 */
function fakeResource(): TableStateResource & { startReload(): void; resolve(): void; fail(err: unknown): void } {
  const loading = signal(false);
  const hasValue = signal(false);
  const error = signal<unknown>(null);
  return {
    hasValue: () => hasValue(),
    error: () => error(),
    isLoading: () => loading(),
    reload: () => {
      error.set(null);
      hasValue.set(false);
      loading.set(true);
    },
    startReload() {
      error.set(null);
      hasValue.set(false);
      loading.set(true);
    },
    resolve() {
      hasValue.set(true);
      loading.set(false);
    },
    fail(err: unknown) {
      error.set(err);
      loading.set(false);
    }
  };
}

describe("TableState", () => {
  it("reads as loading before the first value ever arrives", () => {
    const resource = fakeResource();
    const count = signal(0);
    const state = new TableState({ resource, count: () => count() });

    expect(state.status()).toBe("loading");
    expect(state.showTable()).toBe(false);
  });

  it("moves to ready once the first value resolves with rows", () => {
    const resource = fakeResource();
    const count = signal(3);
    const state = new TableState({ resource, count: () => count() });

    resource.resolve();

    expect(state.status()).toBe("ready");
    expect(state.showTable()).toBe(true);
  });

  it("reads as empty when the first value resolves with no rows and no filter", () => {
    const resource = fakeResource();
    const count = signal(0);
    const state = new TableState({ resource, count: () => count(), filterActive: () => false });

    resource.resolve();

    expect(state.status()).toBe("empty");
    expect(state.showTable()).toBe(false);
  });

  it("keeps showing the table and its rows while a reload is in flight, instead of collapsing to loading", () => {
    const resource = fakeResource();
    const count = signal(5);
    const state = new TableState({ resource, count: () => count() });
    resource.resolve();
    expect(state.status()).toBe("ready");

    // A debounced filter/page/sort change: Angular's own resource clears hasValue() the instant
    // the reload starts, well before any response arrives - exactly what fakeResource mimics here.
    resource.startReload();

    expect(state.status()).toBe("ready");
    expect(state.showTable()).toBe(true);
  });

  it("keeps the table visible across a reload even if the caller's own count callback resets to 0 mid-flight", () => {
    // Some callers do not retain the previous count themselves - TableState must not depend on
    // that discipline: it tracks the last known count on its own.
    const resource = fakeResource();
    const liveCount = 5;
    const state = new TableState({ resource, count: () => (resource.hasValue() ? liveCount : 0) });
    resource.resolve();
    expect(state.status()).toBe("ready");

    resource.startReload();

    expect(state.status()).toBe("ready");
    expect(state.showTable()).toBe(true);
  });

  it("settles onto the new outcome once the reload resolves", () => {
    const resource = fakeResource();
    const count = signal(5);
    const state = new TableState({ resource, count: () => count(), filterActive: () => true });
    resource.resolve();

    resource.startReload();
    count.set(0);
    resource.resolve();

    expect(state.status()).toBe("filtered");
    expect(state.showTable()).toBe(true);
  });

  it("reports the resource's own error even mid-reload of an already-loaded table", () => {
    const resource = fakeResource();
    const count = signal(5);
    const state = new TableState({ resource, count: () => count() });
    resource.resolve();

    resource.startReload();
    resource.fail(new Error("network down"));

    expect(state.status()).toBe("error");
    expect(state.showTable()).toBe(false);
  });

  it("still reads as denied regardless of a previously loaded value", () => {
    const resource = fakeResource();
    const count = signal(5);
    let allowed = true;
    const state = new TableState({ resource, count: () => count(), allowed: () => allowed });
    resource.resolve();

    allowed = false;
    // allowed() is read directly by the status computed each evaluation, so forcing a recompute
    // (any signal read inside status changing) is enough - resource.hasValue() itself is unchanged.
    resource.startReload();

    expect(state.status()).toBe("denied");
    expect(state.showTable()).toBe(false);
  });

  it("still shows the cancel panel for a first load that is cancelled before anything ever resolved", () => {
    const resource = fakeResource();
    const count = signal(0);
    const cancel = jest.fn();
    const state = new TableState({ resource, count: () => count(), cancel });

    resource.startReload();
    state.cancel();

    expect(state.status()).toBe("cancelled");
    expect(state.showTable()).toBe(false);
  });
});
