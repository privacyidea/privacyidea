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
import { TestBed } from "@angular/core/testing";
import { of, Subject, throwError } from "rxjs";
import { DashboardDataStore } from "./dashboard-data-store.service";

describe("DashboardDataStore", () => {
  let store: DashboardDataStore;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [DashboardDataStore] });
    store = TestBed.inject(DashboardDataStore);
  });

  it("exposes the loaded value once the request emits", () => {
    const ref = store.load("k", () => of(42));
    expect(ref.value()).toBe(42);
    expect(ref.revalidating()).toBe(false);
    expect(ref.error()).toBe(false);
  });

  it("deduplicates concurrent loads for the same key (single request)", () => {
    const subject = new Subject<number>();
    const factory = jest.fn(() => subject.asObservable());

    const refA = store.load("k", factory);
    const refB = store.load("k", factory);

    expect(factory).toHaveBeenCalledTimes(1);
    expect(refA).toBe(refB);
    expect(refA.revalidating()).toBe(true);

    subject.next(7);
    subject.complete();
    expect(refA.value()).toBe(7);
    expect(refB.value()).toBe(7);
  });

  it("keeps the previous value while revalidating (stale-while-revalidate)", () => {
    store.load("k", () => of(1));

    const subject = new Subject<number>();
    const ref = store.load("k", () => subject.asObservable());

    // old value is still visible while the new request is in flight
    expect(ref.value()).toBe(1);
    expect(ref.revalidating()).toBe(true);

    subject.next(2);
    subject.complete();
    expect(ref.value()).toBe(2);
    expect(ref.revalidating()).toBe(false);
  });

  it("sets the error flag but retains the last value on failure", () => {
    store.load("k", () => of(5));
    const ref = store.load("k", () => throwError(() => new Error("boom")));

    expect(ref.error()).toBe(true);
    expect(ref.value()).toBe(5);
    expect(ref.revalidating()).toBe(false);
  });

  it("does not cancel or restart an in-flight request when a widget remounts (per key)", () => {
    const subject = new Subject<number>();
    const factory = jest.fn(() => subject.asObservable());

    // first visit: widget mounts and starts the request
    const ref1 = store.load("dashboard:tokens", factory);
    expect(ref1.revalidating()).toBe(true);

    // user leaves and returns while the request is still running: the widget
    // remounts and calls load() again with the same key
    const ref2 = store.load("dashboard:tokens", factory);

    // no second request was started and the same entry is reused
    expect(factory).toHaveBeenCalledTimes(1);
    expect(ref2).toBe(ref1);

    // the original request was never cancelled: it still resolves the entry
    subject.next(99);
    subject.complete();
    expect(ref2.value()).toBe(99);
    expect(ref2.revalidating()).toBe(false);
  });

  it("checks in-flight state independently per key", () => {
    const tokens = new Subject<number>();
    const events = new Subject<number>();
    const tokensFactory = jest.fn(() => tokens.asObservable());
    const eventsFactory = jest.fn(() => events.asObservable());

    store.load("dashboard:tokens", tokensFactory);
    tokens.next(1);
    tokens.complete();

    store.load("dashboard:events", eventsFactory);

    // revisiting reloads tokens (its request finished) but events stays deduped
    store.load("dashboard:tokens", tokensFactory);
    store.load("dashboard:events", eventsFactory);

    expect(tokensFactory).toHaveBeenCalledTimes(2);
    expect(eventsFactory).toHaveBeenCalledTimes(1);
  });

  it("refetches after invalidate", () => {
    const factory = jest.fn(() => of(1));
    store.load("k", factory);
    store.invalidate("k");
    store.load("k", factory);

    expect(factory).toHaveBeenCalledTimes(2);
  });
});
