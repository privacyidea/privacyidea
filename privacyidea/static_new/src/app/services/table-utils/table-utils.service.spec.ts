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
import { TableUtilsService } from "./table-utils.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MatTableDataSource } from "@angular/material/table";
import { FilterValue } from "../../core/models/filter_value";
import { AuthService, JwtData } from "../auth/auth.service";

describe("TableUtilsService", () => {
  let service: TableUtilsService;
  let authService: AuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [TableUtilsService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(TableUtilsService);
    authService = TestBed.inject(AuthService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("emptyDataSource", () => {
    it.each([2, 3])("returns a MatTableDataSource with %i blank rows", (rows) => {
      const ds = service.emptyDataSource<{ id: string; name: string }>(rows, [
        { key: "id", label: "ID" },
        { key: "name", label: "Name" }
      ]);
      expect(ds).toBeInstanceOf(MatTableDataSource);
      expect(ds.data.length).toBe(rows);
      ds.data.forEach((row) => expect(row).toEqual({ id: "", name: "" }));
    });
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

  it.each([
    // TODO should be true once these links are reachable
    ["username", false],
    ["realms", false],
    ["unknown", false]
  ])('isLink("%s") → %s', (key, expected) => {
    expect(service.isLink(key)).toBe(expected);
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
      let jwtData = {
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
      let jwtData = {
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

  describe("getTooltipForColumn", () => {
    it("returns tooltip for active column", () => {
      expect(service.getTooltipForColumn("active", { active: true })).toBe("Deactivate Token");
      expect(service.getTooltipForColumn("active", { active: false })).toBe("Activate Token");
    });

    it("returns Locked / Revoked first", () => {
      expect(service.getTooltipForColumn("active", { locked: true })).toBe("Locked");
      expect(service.getTooltipForColumn("failcount", { revoked: true })).toBe("Revoked");
    });

    it('returns empty string when active = ""', () => {
      expect(service.getTooltipForColumn("active", { active: "" })).toBe("");
    });

    it("returns Reset Fail Counter only when failcount > 0", () => {
      expect(service.getTooltipForColumn("failcount", { failcount: 3 })).toBe("Reset Fail Counter");
      expect(service.getTooltipForColumn("failcount", { failcount: 0 })).toBe("");
    });
  });

  describe("getDisplayText", () => {
    it.each([
      [{ active: true }, "active"],
      [{ active: false }, "deactivated"],
      [{ active: true, locked: true }, "locked"],
      [{ active: false, revoked: true }, "revoked"],
      [{ active: "" }, ""]
    ])('maps element → "%s"', (element, expected) => {
      expect(service.getDisplayText("active", element)).toBe(expected);
    });

    it("returns raw value for non‑special column", () => {
      expect(service.getDisplayText("name", { name: "bob" })).toBe("bob");
    });
  });

  describe("getSpanClassForKey", () => {
    it.each([
      [{ key: "success", value: "" }, ""],
      [{ key: "success", value: true }, "highlight-true"],
      [{ key: "success", value: false }, "highlight-false"],
      [{ key: "description", value: "x" }, "details-table-item details-description"],
      [{ key: "active", value: "" }, ""],
      [{ key: "active", value: true }, "highlight-true"],
      [{ key: "active", value: false }, "highlight-false"],
      [{ key: "failcount", value: "", maxfail: 5 }, ""],
      [{ key: "failcount", value: 0, maxfail: 5 }, "highlight-true"],
      [{ key: "failcount", value: 2, maxfail: 5 }, "highlight-warning"],
      [{ key: "failcount", value: 5, maxfail: 5 }, "highlight-false"],
      [{ key: "other", value: null }, "details-table-item"]
    ])("maps %o → %s", (args, expected) => {
      expect(service.getSpanClassForKey(args)).toBe(expected);
    });
  });

  it.each([
    ["description", "details-scrollable-container"],
    ["maxfail", "details-value"],
    ["count_window", "details-value"],
    ["sync_window", "details-value"],
    ["other", ""]
  ])('getDivClassForKey("%s") → "%s"', (key, expected) => {
    expect(service.getDivClassForKey(key)).toBe(expected);
  });

  it.each([
    ["active", "flex-center"],
    ["failcount", "flex-center"],
    ["realms", "table-scroll-container"],
    ["description", "table-scroll-container"],
    ["xyz", "flex-center-vertical"]
  ])('getClassForColumnKey("%s") → "%s"', (col, expected) => {
    expect(service.getClassForColumnKey(col)).toBe(expected);
  });

  it('getChildClassForColumnKey returns "scroll-item" only for scroll containers', () => {
    expect(service.getChildClassForColumnKey("realms")).toBe("scroll-item");
    expect(service.getChildClassForColumnKey("active")).toBe("");
  });

  it.each([
    ["active", "", false, ""],
    ["active", true, false, "active"],
    ["active", false, false, "deactivated"],
    ["active", true, true, "revoked"],
    ["title", "hello", false, "hello"]
  ])("getDisplayTextForKeyAndRevoked(%s, %s, %s) → %s", (k, v, r, expected) => {
    expect(service.getDisplayTextForKeyAndRevoked(k, v, r)).toBe(expected);
  });

  it.each([
    ["description", "height-104"],
    ["realms", "height-78"],
    ["tokengroup", "height-78"],
    ["id", "height-52"]
  ])('getTdClassForKey("%s") includes %s', (key, expectedPart) => {
    expect(service.getTdClassForKey(key)).toContain(expectedPart);
  });

  it.each([
    ["active", false, "highlight-true"],
    ["disabled", false, "highlight-false"],
    ["other", false, ""],
    ["active", true, "highlight-true-clickable"],
    ["disabled", true, "highlight-false-clickable"],
    ["other", true, ""]
  ])('getSpanClassForState("%s", %s) → %s', (state, clickable, expected) => {
    expect(service.getSpanClassForState(state, clickable)).toBe(expected);
  });

  it.each([
    ["active", "active"],
    ["disabled", "deactivated"],
    ["mystery", "mystery"]
  ])('getDisplayTextForState("%s") → %s', (state, expected) => {
    expect(service.getDisplayTextForState(state)).toBe(expected);
  });
});
