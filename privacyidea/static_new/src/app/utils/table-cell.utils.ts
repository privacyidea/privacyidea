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

import { Sort } from "@angular/material/sort";
import {
  AUTHENTICATION_VALUES,
  booleanDisplayLabel,
  DisplayableValue,
  ROLLOUT_STATE_VALUES,
  tokenStateLabel,
  valueDisplayLabel
} from "@utils/value-label.utils";

export type TableRow = Record<string, unknown>;
export type TableCellValue = string | number | boolean | null | undefined;

function displayableCell(value: unknown): DisplayableValue | undefined {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? value : undefined;
}

/**
 * Columns whose cell text is more than the raw value. A formatter returning undefined leaves the
 * cell to the raw rendering, so every column keeps working without an entry here.
 */
const CELL_FORMATTERS = new Map<string, (element: TableRow) => string | undefined>([
  [
    "active",
    (element) => {
      const active = element["active"];
      if (active === "") return "";
      if (element["revoked"]) return tokenStateLabel("revoked");
      if (element["locked"]) return tokenStateLabel("locked");
      if (active) return tokenStateLabel("active");
      if (active === false) return tokenStateLabel("deactivated");
      return undefined;
    }
  ],
  [
    "rollout_state",
    (element) => {
      const state = element["rollout_state"];
      return typeof state === "string" ? valueDisplayLabel(state, ROLLOUT_STATE_VALUES, { vocabulary: true }) : "";
    }
  ],
  ["success", (element) => booleanDisplayLabel(displayableCell(element["success"]), "predicate")],
  [
    "authentication",
    (element) =>
      valueDisplayLabel(displayableCell(element["authentication"]), AUTHENTICATION_VALUES, { vocabulary: true })
  ]
]);

export function cellDisplayText(columnKey: string, element: TableRow): string {
  const formatted = CELL_FORMATTERS.get(columnKey)?.(element);
  if (formatted !== undefined) return formatted;
  // Own properties only - a column named "toString" must not render Object.prototype's member.
  const cell = Object.hasOwn(element, columnKey) ? element[columnKey] : undefined;
  return cell == null ? "" : String(cell);
}

export function cellTooltip(columnKey: string, element: TableRow): string {
  if (element["locked"]) return tokenStateLabel("locked");
  if (element["revoked"]) return tokenStateLabel("revoked");

  switch (columnKey) {
    case "active":
      if (element["active"] === "") return "";
      return element["active"]
        ? $localize`:@@token.deactivateToken:Deactivate Token`
        : $localize`:@@token.activateToken:Activate Token`;

    case "failcount":
      return element["failcount"] ? $localize`:@@token.resetFailCounter:Reset Fail Counter` : "";
  }
  return "";
}

export function isLinkColumn(columnKey: string): boolean {
  return (
    columnKey === "container_serial" //||
    //columnKey === 'username' ||
    //columnKey === 'user_realm' ||
    //columnKey === 'users' ||
    //columnKey === 'realms'
  );
}

export function spanClassForKey(args: { key: string; value?: TableCellValue; maxfail?: number }): string {
  const { key, value, maxfail } = args;
  if (key === "success") {
    if (value === "" || value === null || value === undefined) {
      return "";
    }
    if (value) return "highlight-true";
    return "highlight-false";
  }
  if (key === "description") {
    return "details-table-item details-description";
  }
  if (key === "active") {
    if (value === "") {
      return "";
    }
    return value === true ? "highlight-true" : "highlight-false";
  }
  if (key === "authentication" && typeof value === "string") {
    if (value.toLowerCase() === "accept") {
      return "highlight-true";
    } else if (value.toLowerCase() === "challenge") {
      return "highlight-warning";
    } else if (value.toLowerCase() === "reject") {
      return "highlight-false";
    }
  }
  if (key === "failcount") {
    if (value === "") {
      return "";
    } else if (value === 0) {
      return "highlight-true";
    } else if (typeof value === "number" && value >= 1 && maxfail !== undefined && value < maxfail) {
      return "highlight-warning";
    } else {
      return "highlight-false";
    }
  }
  return "details-table-item";
}

export function divClassForKey(key: string): string {
  if (key === "description") {
    return "details-scrollable-container";
  } else if (key === "maxfail" || key === "count_window" || key === "sync_window") {
    return "details-value";
  }

  return "";
}

export function classForColumnKey(columnKey: string): string {
  switch (columnKey) {
    case "failcount":
    case "active":
    case "revoke":
    case "maxfail":
    case "delete":
      return "flex-center";
    case "realms":
    case "description":
      return "table-scroll-container";
    default:
      return "flex-center-vertical";
  }
}

export function childClassForColumnKey(columnKey: string): string {
  if (classForColumnKey(columnKey).includes("table-scroll-container")) {
    return "scroll-item";
  }
  return "";
}

export function tdClassForKey(key: string): string[] {
  const classes = ["width-241"];
  if (key === "description") {
    classes.push("height-127");
  } else if (["realms", "tokengroup"].includes(key)) {
    classes.push("height-78");
  } else {
    classes.push("height-53");
  }
  return classes;
}

export function spanClassForState(state: string, clickable: boolean): string {
  switch (clickable) {
    case false:
      if (state === "active") {
        return "highlight-true";
      } else if (state === "disabled" || state === "damaged" || state === "lost") {
        return "highlight-false";
      } else {
        return "";
      }
    case true:
      if (state === "active") {
        return "highlight-true-clickable";
      } else if (state === "disabled" || state === "damaged" || state === "lost") {
        return "highlight-false-clickable";
      } else {
        return "";
      }
  }
}

export function sortIcon(columnKey: string, sort: Sort): string {
  if (sort.active !== columnKey || !sort.direction) {
    return "unfold_more";
  }
  return sort.direction === "asc" ? "keyboard_arrow_upward" : "keyboard_arrow_downward";
}
