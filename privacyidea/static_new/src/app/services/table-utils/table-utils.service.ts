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
import { inject, Injectable, signal, WritableSignal } from "@angular/core";
import { MatTableDataSource } from "@angular/material/table";
import { FilterValue } from "../../core/models/filter_value";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

export interface FilterPair {
  key: string;
  value: string;
}

export type ColumnKey =
  | "select"
  | "serial"
  | "type"
  | "states"
  | "description"
  | "user_name"
  | "user_realm"
  | "realms"
  | "tokentype"
  | "active"
  | "username"
  | "failcount"
  | "maxfail"
  | "container_serial"
  | "count"
  | "rounds"
  | "service_id"
  | "user";

export type ColumnDef<K extends ColumnKey = ColumnKey> = Readonly<{
  key: K;
  label: string;
}>;

export const COLUMN_REGISTRY: Readonly<Record<ColumnKey, ColumnDef>> = {
  select: { key: "select", label: "" },
  serial: { key: "serial", label: "Serial" },
  type: { key: "type", label: "Type" },
  states: { key: "states", label: "Status" },
  description: { key: "description", label: "Description" },
  user_name: { key: "user_name", label: "User" },
  user_realm: { key: "user_realm", label: "Realm" },
  realms: { key: "realms", label: "Container Realms" },
  tokentype: { key: "tokentype", label: "Type" },
  active: { key: "active", label: "Active" },
  username: { key: "username", label: "User" },
  failcount: { key: "failcount", label: "Fail Counter" },
  maxfail: { key: "maxfail", label: "Maxfail" },
  container_serial: { key: "container_serial", label: "Container" },
  count: { key: "count", label: "Count" },
  rounds: { key: "rounds", label: "Rounds" },
  service_id: { key: "service_id", label: "Service ID" },
  user: { key: "user", label: "SSH User" }
} as const;

type ColumnsTuple<K extends readonly ColumnKey[]> = {
  readonly [I in keyof K]: ColumnDef<Extract<K[I], ColumnKey>>;
};

type KeysOfColumns<C extends readonly ColumnDef[]> = {
  readonly [I in keyof C]: C[I] extends ColumnDef<infer KK> ? KK : never;
};

export interface TableUtilsServiceInterface {
  pageSizeOptions: WritableSignal<number[]>;

  emptyDataSource<T>(pageSize: number, columnsKeyMap: { key: string; label: string }[]): MatTableDataSource<T>;

  toggleKeywordInFilter(args: { keyword: string; currentValue: FilterValue }): FilterValue;

  toggleBooleanInFilter(args: { keyword: string; currentValue: FilterValue }): FilterValue;

  isLink(columnKey: string): boolean;

  getClassForColumn(columnKey: string, element: any): string;

  getTooltipForColumn(columnKey: string, element: any): string;

  getDisplayText(columnKey: string, element: any): string;

  getSpanClassForKey(args: { key: string; value?: any; maxfail?: any }): string;

  getDivClassForKey(key: string): string;

  getClassForColumnKey(columnKey: string): string;

  getChildClassForColumnKey(columnKey: string): string;

  getDisplayTextForKeyAndRevoked(key: string, value: any, revoked: boolean): string;

  getTdClassForKey(key: string): string[];

  getSpanClassForState(state: string, clickable: boolean): string;

  getDisplayTextForState(state: string): string;

  pickColumns<const K extends readonly ColumnKey[]>(...keys: K): ColumnsTuple<K>;

  getColumnKeys<const C extends readonly ColumnDef[]>(cols: C): KeysOfColumns<C>;
}

@Injectable({
  providedIn: "root"
})
export class TableUtilsService implements TableUtilsServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  pageSizeOptions = signal([5, 10, 25, 50]);

  emptyDataSource<T>(pageSize: number, columnsKeyMap: { key: string; label: string }[]): MatTableDataSource<T> {
    return new MatTableDataSource(
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = "";
        });
        return emptyRow;
      })
    );
  }

  toggleKeywordInFilter(args: { keyword: string; currentValue: FilterValue }): FilterValue {
    const { keyword, currentValue } = args;

    if (keyword.includes("&")) {
      const keywords = keyword.split("&").map((k) => k.trim());
      let newValue = currentValue;
      for (const key of keywords) {
        newValue = this.toggleKeywordInFilter({ keyword: key, currentValue: newValue });
      }
      return newValue;
    }
    if (currentValue.hasKey(keyword)) {
      return currentValue.removeKey(keyword);
    } else {
      return currentValue.addKey(keyword);
    }
  }

  public toggleBooleanInFilter(args: { keyword: string; currentValue: FilterValue }): FilterValue {
    const { keyword, currentValue } = args;
    const booleanValue = currentValue.getValueOfKey(keyword)?.toLowerCase();

    if (!booleanValue) {
      return currentValue.addEntry(keyword, "true");
    } else {
      const existingValue = booleanValue;

      if (existingValue === "true") {
        return currentValue.addEntry(keyword, "false");
      } else if (existingValue === "false") {
        return currentValue.removeKey(keyword);
      } else {
        return currentValue.addEntry(keyword, "true");
      }
    }
  }

  isLink(columnKey: string): boolean {
    return (
      columnKey === "container_serial" //||
      //columnKey === 'username' ||
      //columnKey === 'user_realm' ||
      //columnKey === 'users' ||
      //columnKey === 'realms'
    );
  }

  getClassForColumn(columnKey: string, element: any): string {
    if (element["locked"] || element["revoked"]) return "highlight-disabled";

    switch (columnKey) {
      case "active":
        if (element["active"]) {
          if (this.authService.actionAllowed("disable")) return "highlight-true-clickable";
          else return "highlight-true";
        }
        if (element["active"] === false) {
          if (this.authService.actionAllowed("enable")) return "highlight-false-clickable";
          else return "highlight-false";
        }
        return "";

      case "failcount":
        if (element["failcount"] === "") return "";
        if (element["failcount"] <= 0) return "highlight-true";
        if (element["failcount"] < element["maxfail"]) {
          if (this.authService.actionAllowed("reset")) return "highlight-warning-clickable";
          else return "highlight-warning";
        }
        if (this.authService.actionAllowed("reset")) return "highlight-false-clickable";
        else return "highlight-false";
    }
    return "";
  }

  getTooltipForColumn(columnKey: string, element: any): string {
    if (element["locked"]) return "Locked";
    if (element["revoked"]) return "Revoked";

    switch (columnKey) {
      case "active":
        if (element["active"] === "") return "";
        return element["active"] ? "Deactivate Token" : "Activate Token";

      case "failcount":
        return element["failcount"] ? "Reset Fail Counter" : "";
    }
    return "";
  }

  getDisplayText(columnKey: string, element: any): string {
    switch (columnKey) {
      case "active":
        if (element["active"] === "") return "";
        if (element["revoked"]) return "revoked";
        if (element["locked"]) return "locked";
        if (element["active"]) return "active";
        if (element["active"] === false) return "deactivated";
        break;
    }
    return element[columnKey];
  }

  getSpanClassForKey(args: { key: string; value?: any; maxfail?: any }): string {
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
    if (key === "failcount") {
      if (value === "") {
        return "";
      } else if (value === 0) {
        return "highlight-true";
      } else if (value >= 1 && value < maxfail) {
        return "highlight-warning";
      } else {
        return "highlight-false";
      }
    }
    return "details-table-item";
  }

  getDivClassForKey(key: string) {
    if (key === "description") {
      return "details-scrollable-container";
    } else if (key === "maxfail" || key === "count_window" || key === "sync_window") {
      return "details-value";
    }

    return "";
  }

  getClassForColumnKey(columnKey: string): string {
    switch (columnKey) {
      case "failcount":
      case "active":
      case "revoke":
      case "delete":
        return "flex-center";
      case "realms":
      case "description":
        return "table-scroll-container";
      default:
        return "flex-center-vertical";
    }
  }

  getChildClassForColumnKey(columnKey: string): string {
    if (this.getClassForColumnKey(columnKey).includes("table-scroll-container")) {
      return "scroll-item";
    }
    return "";
  }

  getDisplayTextForKeyAndRevoked(key: string, value: any, revoked: boolean): string {
    if (value === "") {
      return "";
    }
    if (key === "active") {
      return revoked ? "revoked" : value ? "active" : "deactivated";
    }
    return value;
  }

  getTdClassForKey(key: string) {
    const classes = ["fix-width-20-padr-0"];
    if (key === "description") {
      classes.push("height-104");
    } else if (["realms", "tokengroup"].includes(key)) {
      classes.push("height-78");
    } else {
      classes.push("height-52");
    }
    return classes;
  }

  getSpanClassForState(state: string, clickable: boolean): string {
    switch (clickable) {
      case false:
        if (state === "active") {
          return "highlight-true";
        } else if (state === "disabled") {
          return "highlight-false";
        } else {
          return "";
        }
      case true:
        if (state === "active") {
          return "highlight-true-clickable";
        } else if (state === "disabled") {
          return "highlight-false-clickable";
        } else {
          return "";
        }
    }
  }

  getDisplayTextForState(state: string) {
    if (state === "active") {
      return "active";
    } else if (state === "disabled") {
      return "deactivated";
    } else {
      return state;
    }
  }

  pickColumns<const K extends readonly ColumnKey[]>(
    ...keys: K
  ) {
    return keys.map(k => COLUMN_REGISTRY[k]) as {
      readonly [I in keyof K]: ColumnDef<Extract<K[I], ColumnKey>>;
    };
  }

  getColumnKeys<const C extends readonly ColumnDef[]>(
    cols: C
  ) {
    return cols.map(c => c.key) as {
      readonly [I in keyof C]: C[I] extends ColumnDef<infer KK> ? KK : never;
    };
  }
}
