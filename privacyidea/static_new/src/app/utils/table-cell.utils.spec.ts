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
import {
  cellDisplayText,
  cellTooltip,
  childClassForColumnKey,
  classForColumnKey,
  divClassForKey,
  isLinkColumn,
  sortIcon,
  spanClassForKey,
  spanClassForState,
  TableCellValue,
  tdClassForKey
} from "./table-cell.utils";

describe("cellDisplayText", () => {
  it.each([
    [{ active: true }, "Active"],
    [{ active: false }, "Deactivated"],
    [{ active: true, locked: true }, "Locked"],
    [{ active: false, revoked: true }, "Revoked"],
    [{ active: "" }, ""]
  ])('maps element → "%s"', (element, expected) => {
    expect(cellDisplayText("active", element)).toBe(expected);
  });

  const rolloutStateCases: [string, string][] = [
    ["clientwait", "Client wait"],
    ["pending", "Pending"],
    ["enrolled", "Enrolled"],
    ["mystery", "mystery"]
  ];
  it.each(rolloutStateCases)('maps rollout_state "%s" → "%s"', (state, expected) => {
    expect(cellDisplayText("rollout_state", { rollout_state: state })).toBe(expected);
  });

  it("returns an empty string for a rollout_state that is not a string", () => {
    expect(cellDisplayText("rollout_state", {})).toBe("");
  });

  const auditCellCases: [string, TableCellValue, string][] = [
    ["success", true, "Yes"],
    ["success", false, "No"],
    ["success", 1, "Yes"],
    ["success", 0, "No"],
    ["authentication", "accept", "Accept"],
    ["authentication", "challenge", "Challenge"],
    ["authentication", "reject", "Reject"],
    ["authentication", "declined", "Declined"],
    ["authentication", "DECLINED", "Declined"],
    ["authentication", "mystery", "mystery"],
    ["action", "/auth", "/auth"],
    ["success", "", ""],
    ["success", null, ""],
    ["success", undefined, ""]
  ];
  it.each(auditCellCases)('maps "%s" = %s → "%s"', (key, value, expected) => {
    expect(cellDisplayText(key, { [key]: value })).toBe(expected);
  });

  it("returns raw value for non‑special column", () => {
    expect(cellDisplayText("name", { name: "bob" })).toBe("bob");
  });

  it("renders a column named like an Object member as a raw cell", () => {
    expect(cellDisplayText("constructor", { constructor: "acme" })).toBe("acme");
    expect(cellDisplayText("toString", {})).toBe("");
  });
});

describe("cellTooltip", () => {
  it("returns tooltip for active column", () => {
    expect(cellTooltip("active", { active: true })).toBe("Deactivate Token");
    expect(cellTooltip("active", { active: false })).toBe("Activate Token");
  });

  it("returns Locked / Revoked first", () => {
    expect(cellTooltip("active", { locked: true })).toBe("Locked");
    expect(cellTooltip("failcount", { revoked: true })).toBe("Revoked");
  });

  it('returns empty string when active = ""', () => {
    expect(cellTooltip("active", { active: "" })).toBe("");
  });

  it("returns Reset Fail Counter only when failcount > 0", () => {
    expect(cellTooltip("failcount", { failcount: 3 })).toBe("Reset Fail Counter");
    expect(cellTooltip("failcount", { failcount: 0 })).toBe("");
  });
});

describe("spanClassForKey", () => {
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
    expect(spanClassForKey(args)).toBe(expected);
  });
});

describe("column classes", () => {
  it.each([
    // TODO should be true once these links are reachable
    ["username", false],
    ["realms", false],
    ["unknown", false]
  ])('isLinkColumn("%s") → %s', (key, expected) => {
    expect(isLinkColumn(key)).toBe(expected);
  });

  it.each([
    ["description", "details-scrollable-container"],
    ["maxfail", "details-value"],
    ["count_window", "details-value"],
    ["sync_window", "details-value"],
    ["other", ""]
  ])('divClassForKey("%s") → "%s"', (key, expected) => {
    expect(divClassForKey(key)).toBe(expected);
  });

  it.each([
    ["active", "flex-center"],
    ["failcount", "flex-center"],
    ["realms", "table-scroll-container"],
    ["description", "table-scroll-container"],
    ["xyz", "flex-center-vertical"]
  ])('classForColumnKey("%s") → "%s"', (col, expected) => {
    expect(classForColumnKey(col)).toBe(expected);
  });

  it('childClassForColumnKey returns "scroll-item" only for scroll containers', () => {
    expect(childClassForColumnKey("realms")).toBe("scroll-item");
    expect(childClassForColumnKey("active")).toBe("");
  });

  it.each([
    ["description", "height-127"],
    ["realms", "height-78"],
    ["tokengroup", "height-78"],
    ["id", "height-53"]
  ])('tdClassForKey("%s") includes %s', (key, expectedPart) => {
    expect(tdClassForKey(key)).toContain(expectedPart);
  });

  it.each([
    ["active", false, "highlight-true"],
    ["disabled", false, "highlight-false"],
    ["damaged", false, "highlight-false"],
    ["lost", false, "highlight-false"],
    ["other", false, ""],
    ["active", true, "highlight-true-clickable"],
    ["disabled", true, "highlight-false-clickable"],
    ["damaged", true, "highlight-false-clickable"],
    ["lost", true, "highlight-false-clickable"],
    ["other", true, ""]
  ])('spanClassForState("%s", %s) → %s', (state, clickable, expected) => {
    expect(spanClassForState(state, clickable)).toBe(expected);
  });
});

describe("sortIcon", () => {
  it.each([
    ["serial", { active: "serial", direction: "asc" as const }, "keyboard_arrow_upward"],
    ["serial", { active: "serial", direction: "desc" as const }, "keyboard_arrow_downward"],
    ["serial", { active: "serial", direction: "" as const }, "unfold_more"],
    ["serial", { active: "other", direction: "asc" as const }, "unfold_more"]
  ])('sortIcon("%s", %o) → %s', (columnKey, sort, expected) => {
    expect(sortIcon(columnKey, sort)).toBe(expected);
  });
});
