/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { delay, Observable, of, Subject } from "rxjs";

import { LoadingService } from "./loading-service";
import { HttpEvent } from "@angular/common/http";

describe("LoadingService", () => {
  let loadingService: LoadingService;
  const listener = jest.fn();

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    loadingService = TestBed.inject(LoadingService);
    jest.clearAllMocks();
  });

  it("addListener / notifyListeners reflect isLoading()", () => {
    loadingService.addListener("L1", listener);
    loadingService.notifyListeners();
    expect(listener).toHaveBeenCalledWith(false);

    const subj = new Subject<any>();
    loadingService.addLoading({
      key: "k1",
      observable: subj.asObservable(),
      url: "/u"
    });
    expect(listener).toHaveBeenLastCalledWith(true);

    subj.complete();
    expect(listener).toHaveBeenLastCalledWith(false);
  });

  it("getLoadingUrls returns current list; removeLoading prunes it", () => {
    const subj = new Subject<any>();
    loadingService.addLoading({
      key: "abc",
      observable: subj.asObservable(),
      url: "/abc"
    });
    expect(loadingService.getLoadingUrls()).toEqual([{ key: "abc", url: "/abc" }]);

    loadingService.removeLoading("abc");
    expect(loadingService.getLoadingUrls()).toEqual([]);
    expect(loadingService.isLoading()).toBe(false);
  });

  describe("addLoading drops entry after complete / error", () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    it("removes loading when observable completes", () => {
      loadingService.addLoading({
        key: "c1",
        observable: (of(null) as unknown as Observable<HttpEvent<unknown>>).pipe(delay(0)),
        url: "/complete"
      });

      expect(loadingService.isLoading()).toBe(true);

      jest.runOnlyPendingTimers();
      expect(loadingService.isLoading()).toBe(false);
    });

    it("removes loading when observable errors", () => {
      jest.useFakeTimers();

      const error$ = new Observable((observer) => {
        setTimeout(() => observer.error(new Error("fail")), 0);
      });

      loadingService.addLoading({
        key: "e1",
        observable: error$ as Observable<HttpEvent<unknown>>,
        url: "/error"
      });

      // still loading until the timer fires
      expect(loadingService.isLoading()).toBe(true);

      jest.runOnlyPendingTimers(); // flush setTimeout
      expect(loadingService.isLoading()).toBe(false);

      jest.useRealTimers();
    });
  });

  it("clearAllLoadings unsubscribes and resets state", () => {
    const subj1 = new Subject<any>();
    const subj2 = new Subject<any>();

    loadingService.addLoading({
      key: "k1",
      observable: subj1.asObservable(),
      url: "/1"
    });
    loadingService.addLoading({
      key: "k2",
      observable: subj2.asObservable(),
      url: "/2"
    });

    const unsubs = loadingService["loadings"].map((l) => jest.spyOn(l.subscription, "unsubscribe"));
    loadingService.clearAllLoadings();

    unsubs.forEach((spy) => expect(spy).toHaveBeenCalled());
    expect(loadingService.isLoading()).toBe(false);
  });

  it("removeListener deletes the listener", () => {
    loadingService.addListener("toDelete", listener);
    expect(Object.keys(loadingService["listeners"])).toContain("toDelete");
    loadingService.removeListener("toDelete");
    expect(Object.keys(loadingService["listeners"])).not.toContain("toDelete");
  });
});
