/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { WritableSignal, signal } from "@angular/core";
import { MatTableDataSource } from "@angular/material/table";
import { Sort } from "@angular/material/sort";
import { ColumnDef, ColumnKey, TableUtilsServiceInterface } from "../../app/services/table-utils/table-utils.service";
import { ContainerDetailToken } from "../../app/services/container/container.service";
import { TokenApplication } from "../../app/services/machine/machine.service";

export class MockTableUtilsService implements TableUtilsServiceInterface {
  pageSizeOptions: WritableSignal<number[]> = signal([5, 10, 25, 50]);
  emptyDataSource = jest.fn().mockImplementation((_pageSize: number, _columns: { key: string; label: string }[]) => {
    const dataSource = new MatTableDataSource<TokenApplication>([]);
    (dataSource as any).isEmpty = true;
    return dataSource;
  });
  toggleKeywordInFilter = jest.fn();
  public toggleBooleanInFilter = jest.fn();
  isLink = jest.fn().mockReturnValue(false);
  getClassForColumn = jest.fn();
  getTooltipForColumn = jest.fn();
  getDisplayText = jest.fn();
  getSpanClassForKey = jest.fn().mockReturnValue("");
  getDivClassForKey = jest.fn().mockReturnValue("");
  getClassForColumnKey = jest.fn();
  getChildClassForColumnKey = jest.fn().mockReturnValue("");
  getDisplayTextForKeyAndRevoked = jest.fn().mockReturnValue("");
  getTdClassForKey = jest.fn().mockReturnValue("");
  getSpanClassForState = jest.fn().mockReturnValue("");
  getDisplayTextForState = jest.fn().mockReturnValue("");

  pickColumns<const K extends readonly ColumnKey[]>(...keys: K) {
    return keys.map((k) => ({ key: k as any, label: String(k) })) as any;
  }

  getColumnKeys<const C extends readonly ColumnDef[]>(cols: C) {
    return cols.map((c) => c.key) as any;
  }

  getSortIcon(_columnKey: string, _sort: Sort): string {
    return "";
  }

  onSortButtonClick(_key: string, _sort: WritableSignal<Sort>): void {}

  clientsideSortTokenData(data: ContainerDetailToken[], _s: Sort): ContainerDetailToken[] {
    return data;
  }

  handleColumnClick = jest.fn();
}
