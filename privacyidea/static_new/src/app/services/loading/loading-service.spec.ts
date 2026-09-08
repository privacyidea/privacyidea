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
import { LoadingService } from "./loading-service";

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

    loadingService.addLoading("k1", "/u");
    expect(listener).toHaveBeenLastCalledWith(true);

    loadingService.removeLoading("k1");
    expect(listener).toHaveBeenLastCalledWith(false);
  });

  it("getLoadingGroups returns current endpoints; removeLoading prunes them", () => {
    loadingService.addLoading("abc", "/abc");
    expect(loadingService.getLoadingGroups()).toEqual([{ endpoint: "/abc", count: 1 }]);

    loadingService.removeLoading("abc");
    expect(loadingService.getLoadingGroups()).toEqual([]);
    expect(loadingService.isLoading()).toBe(false);
  });

  it("groups requests to the same endpoint regardless of query parameters", () => {
    ["/token/?page=1", "/token/?page=2", "/token/"].forEach((url, index) => loadingService.addLoading(`k${index}`, url));
    loadingService.addLoading("other", "/realm/");

    expect(loadingService.getLoadingGroups()).toEqual([
      { endpoint: "/token/", count: 3 },
      { endpoint: "/realm/", count: 1 }
    ]);

    loadingService.removeLoading("k0");

    expect(loadingService.getLoadingGroups()).toEqual([
      { endpoint: "/token/", count: 2 },
      { endpoint: "/realm/", count: 1 }
    ]);
  });

  it("clearAllLoadings resets state", () => {
    loadingService.addLoading("k1", "/1");
    loadingService.addLoading("k2", "/2");

    loadingService.clearAllLoadings();

    expect(loadingService.isLoading()).toBe(false);
    expect(loadingService.getLoadingGroups()).toEqual([]);
  });

  it("removeListener deletes the listener", () => {
    loadingService.addListener("toDelete", listener);
    expect(Object.keys(loadingService["listeners"])).toContain("toDelete");
    loadingService.removeListener("toDelete");
    expect(Object.keys(loadingService["listeners"])).not.toContain("toDelete");
  });
});
