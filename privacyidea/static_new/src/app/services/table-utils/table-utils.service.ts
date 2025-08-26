import { Injectable, WritableSignal, signal } from "@angular/core";

import { MatTableDataSource } from "@angular/material/table";

export interface TableUtilsServiceInterface {
  pageSizeOptions: WritableSignal<number[]>;

  emptyDataSource<T>(pageSize: number, columnsKeyMap: { key: string; label: string }[]): MatTableDataSource<T>;

  toggleKeywordInFilter(currentValue: string, keyword: string): string;

  toggleBooleanInFilter(args: { keyword: string; currentValue: string }): string;

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
}

@Injectable({
  providedIn: "root"
})
export class TableUtilsService implements TableUtilsServiceInterface {
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

  toggleKeywordInFilter(currentValue: string, keyword: string): string {
    if (keyword.includes("&")) {
      const keywords = keyword.split("&").map((k) => k.trim());
      let newValue = currentValue;
      for (const key of keywords) {
        newValue = this.toggleKeywordInFilter(newValue, key);
      }
      return newValue;
    }
    const keywordPattern = new RegExp(`\\b${keyword}:.*?(?=(\\s+\\w+:|$))`, "i");
    if (keywordPattern.test(currentValue)) {
      return currentValue
        .replace(keywordPattern, " ")
        .trimStart()
        .replace(/\s{2,}/g, " ");
    } else {
      if (currentValue.length > 0) {
        return (currentValue + ` ${keyword}: `).replace(/\s{2,}/g, " ");
      } else {
        return `${keyword}: `;
      }
    }
  }

  public toggleBooleanInFilter(args: { keyword: string; currentValue: string }): string {
    const { keyword, currentValue } = args;
    const regex = new RegExp(`\\b${keyword}:\\s?([\\w\\d]*)(?![\\w\\d]*:)`, "i");
    const match = currentValue.match(regex);

    if (!match) {
      return (currentValue.trim() + ` ${keyword}: true`).trim();
    } else {
      const existingValue = match[1].toLowerCase();

      if (existingValue === "true") {
        return currentValue.replace(regex, keyword + ": false");
      } else if (existingValue === "false") {
        const removed = currentValue.replace(regex, "").trim();
        return removed.replace(/\s{2,}/g, " ");
      } else {
        return currentValue.replace(regex, keyword + ": true");
      }
    }
  }

  public recordsFromText(textValue: string): Record<string, string> {
    const mapValue = {} as Record<string, string>;
    const regex = /(\w+):\s*([^:]*?)(?=\s+\w+:|$)/g;
    let match;
    while ((match = regex.exec(textValue)) !== null) {
      const key = match[1].trim();
      const value = match[2].trim();
      if (key) {
        mapValue[key] = value;
      }
    }
    return mapValue;
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
        if (element["active"]) return "highlight-true-clickable";
        if (element["active"] === false) return "highlight-false-clickable";
        return "";

      case "failcount":
        if (element["failcount"] === "") return "";
        if (element["failcount"] <= 0) return "highlight-true";
        if (element["failcount"] < element["maxfail"]) {
          return "highlight-warning-clickable";
        }
        return "highlight-false-clickable";
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
}
