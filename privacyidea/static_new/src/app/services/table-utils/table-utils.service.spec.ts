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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService, JwtData } from "@services/auth/auth.service";
import { ContainerDetailToken } from "@services/container/container.service";
import { TableUtilsService } from "./table-utils.service";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";

describe("TableUtilsService", () => {
  let service: TableUtilsService;
  let authService: AuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        TableUtilsService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    });
    service = TestBed.inject(TableUtilsService);
    authService = TestBed.inject(AuthService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("toggleKeywordInFilter", () => {
    it("adds a missing keyword placeholder", () => {
      // expect(service.toggleKeywordInFilter("", "username")).toBe("username: ");
      expect(service.toggleKeywordInFilter({ keyword: "username", currentValue: new FilterValue() }).filterString).toBe(
        "username: "
      );
    });

    it("removes an existing keyword (idempotent)", () => {
      const once = service.toggleKeywordInFilter({
        keyword: "username",
        currentValue: new FilterValue({ value: "username: " })
      }).filterString;
      expect(once).toBe("");
      const twice = service.toggleKeywordInFilter({
        keyword: "machineid & resolver",
        currentValue: new FilterValue({ value: "machineid: 1 resolver: x" })
      }).filterString;
      expect(twice).toBe("");
    });

    it("adds a composite keyword placeholder", () => {
      const value = service.toggleKeywordInFilter({
        keyword: "machineid & resolver",
        currentValue: new FilterValue()
      }).filterString;
      expect(value).toBe("machineid: resolver: ");
    });
  });

  describe("toggleBooleanInFilter", () => {
    it("cycles through true → false → (removed)", () => {
      const step1 = service.toggleBooleanInFilter({
        keyword: "active",
        currentValue: new FilterValue()
      });
      expect(step1.filterString).toBe("active: true");
      const step2 = service.toggleBooleanInFilter({
        keyword: "active",
        currentValue: step1
      });
      expect(step2.filterString).toBe("active: false");
      const step3 = service.toggleBooleanInFilter({
        keyword: "active",
        currentValue: step2
      });
      expect(step3.filterString).toBe("");
    });

    it("converts non‑boolean value to true", () => {
      const out = service.toggleBooleanInFilter({
        keyword: "flag",
        currentValue: new FilterValue({ value: "flag: maybe" })
      });
      expect(out.filterString).toBe("flag: true");
    });
  });

  describe("getClassForColumn", () => {
    it("returns highlight-disabled when locked", () => {
      expect(service.getClassForColumn("any", { locked: true })).toBe("highlight-disabled");
    });

    it("returns the correct class for active column", () => {
      // No enable / disable rights
      expect(service.getClassForColumn("active", { active: true })).toBe("highlight-true");
      expect(service.getClassForColumn("active", { active: false })).toBe("highlight-false");
      // Allow enable / disable
      const jwtData = {
        username: "",
        realm: "",
        nonce: "",
        role: "",
        authtype: "",
        exp: 0,
        rights: ["disable", "enable"]
      };
      authService.jwtData.set(jwtData as JwtData);
      expect(service.getClassForColumn("active", { active: true })).toBe("highlight-true-clickable");
      expect(service.getClassForColumn("active", { active: false })).toBe("highlight-false-clickable");
    });

    it("returns the correct class for failcount column", () => {
      expect(service.getClassForColumn("failcount", { failcount: 0, maxfail: 5 })).toBe("highlight-true");
      // reset not allowed
      expect(service.getClassForColumn("failcount", { failcount: 2, maxfail: 5 })).toBe("highlight-warning");
      expect(service.getClassForColumn("failcount", { failcount: 5, maxfail: 5 })).toBe("highlight-false");
      // Allow reset failcount
      const jwtData = {
        username: "",
        realm: "",
        nonce: "",
        role: "",
        authtype: "",
        exp: 0,
        rights: ["reset"]
      };
      authService.jwtData.set(jwtData as JwtData);
      expect(service.getClassForColumn("failcount", { failcount: 2, maxfail: 5 })).toBe("highlight-warning-clickable");
      expect(service.getClassForColumn("failcount", { failcount: 5, maxfail: 5 })).toBe("highlight-false-clickable");
    });

    it('returns "" when failcount is empty string', () => {
      expect(service.getClassForColumn("failcount", { failcount: "", maxfail: 5 })).toBe("");
    });

    it('returns "" when active is undefined', () => {
      expect(service.getClassForColumn("active", { active: undefined })).toBe("");
    });
  });

  // The cell formatting itself lives in table-cell.utils and is covered by its own spec; these
  // only pin that the template-facing facade forwards to it.
  it("forwards cell rendering to the table cell utils", () => {
    expect(service.getDisplayText("active", { active: true })).toBe("Active");
    expect(service.getTooltipForColumn("active", { active: true })).toBe("Deactivate Token");
    expect(service.getSpanClassForKey({ key: "success", value: true })).toBe("highlight-true");
    expect(service.getClassForColumnKey("realms")).toBe("table-scroll-container");
    expect(service.getChildClassForColumnKey("realms")).toBe("scroll-item");
    expect(service.getDivClassForKey("description")).toBe("details-scrollable-container");
    expect(service.getTdClassForKey("description")).toContain("height-127");
    expect(service.getSpanClassForState("active", false)).toBe("highlight-true");
    expect(service.getSortIcon("serial", { active: "serial", direction: "asc" })).toBe("keyboard_arrow_upward");
    expect(service.isLink("container_serial")).toBe(true);
  });

  it.each([
    ["active", "Active"],
    ["disabled", "Deactivated"],
    ["lost", "Lost"],
    ["damaged", "Damaged"],
    ["mystery", "mystery"]
  ])('getDisplayTextForState("%s") → %s', (state, expected) => {
    expect(service.getDisplayTextForState(state)).toBe(expected);
  });

  describe("clientsideSortTokenData", () => {
    const makeToken = (overrides: Partial<ContainerDetailToken> & Record<string, unknown> = {}) =>
      ({
        active: true,
        container_serial: "C1",
        count: 0,
        count_window: 0,
        description: "",
        failcount: 0,
        id: 0,
        revoked: false,
        serial: "",
        sync_window: 0,
        tokengroup: [],
        tokentype: "hotp",
        user_editable: false,
        user_id: "",
        user_realm: "",
        username: "",
        ...overrides
      }) as unknown as ContainerDetailToken;

    it("returns the input untouched when direction is empty", () => {
      const data = [makeToken({ serial: "B" }), makeToken({ serial: "A" })];
      const result = service.clientsideSortTokenData(data, { active: "serial", direction: "" });
      expect(result).toBe(data);
      expect(result.map((t) => t.serial)).toEqual(["B", "A"]);
    });

    it("sorts ascending by the chosen key (case-insensitive)", () => {
      const data = [makeToken({ serial: "beta" }), makeToken({ serial: "Alpha" }), makeToken({ serial: "gamma" })];
      const result = service.clientsideSortTokenData(data, { active: "serial", direction: "asc" });
      expect(result.map((t) => t.serial)).toEqual(["Alpha", "beta", "gamma"]);
    });

    it("sorts descending by the chosen key", () => {
      const data = [
        makeToken({ description: "banana" }),
        makeToken({ description: "apple" }),
        makeToken({ description: "cherry" })
      ];
      const result = service.clientsideSortTokenData(data, { active: "description", direction: "desc" });
      expect(result.map((t) => t.description)).toEqual(["cherry", "banana", "apple"]);
    });

    it("treats undefined / null values as empty strings (sorted first ascending)", () => {
      const data = [
        makeToken({ serial: "x", resolver: "zeta" }),
        makeToken({ serial: "y", resolver: undefined }),
        makeToken({ serial: "z", resolver: "alpha" })
      ];
      const result = service.clientsideSortTokenData(data, { active: "resolver", direction: "asc" });
      expect(result.map((t) => t.serial)).toEqual(["y", "z", "x"]);
    });

    it("sorts numeric fields by their stringified value", () => {
      const data = [makeToken({ failcount: 2 }), makeToken({ failcount: 10 }), makeToken({ failcount: 1 })];
      const result = service.clientsideSortTokenData(data, { active: "failcount", direction: "asc" });
      expect(result.map((t) => t.failcount)).toEqual([1, 10, 2]);
    });

    it("mutates and returns the same array reference", () => {
      const data = [makeToken({ serial: "b" }), makeToken({ serial: "a" })];
      const result = service.clientsideSortTokenData(data, { active: "serial", direction: "asc" });
      expect(result).toBe(data);
    });
  });

  describe("onSortButtonClick", () => {
    it("cycles a column through ascending -> descending -> cleared (default serial fallback)", () => {
      const sort = signal({ active: "serial", direction: "asc" as const });

      service.onSortButtonClick("event_type", sort);
      expect(sort()).toEqual({ active: "event_type", direction: "asc" });

      service.onSortButtonClick("event_type", sort);
      expect(sort()).toEqual({ active: "event_type", direction: "desc" });

      service.onSortButtonClick("event_type", sort);
      expect(sort()).toEqual({ active: "serial", direction: "asc" });
    });

    it("uses the provided fallback when clearing", () => {
      const sort = signal({ active: "timestamp", direction: "desc" as const });
      const fallback = { active: "timestamp", direction: "" as const };

      service.onSortButtonClick("event_type", sort, fallback);
      service.onSortButtonClick("event_type", sort, fallback);
      service.onSortButtonClick("event_type", sort, fallback);
      expect(sort()).toEqual({ active: "timestamp", direction: "" });
    });

    it("switching to a different column restarts at ascending", () => {
      const sort = signal({ active: "event_type", direction: "desc" as const });

      service.onSortButtonClick("username", sort);
      expect(sort()).toEqual({ active: "username", direction: "asc" });
    });
  });
});
