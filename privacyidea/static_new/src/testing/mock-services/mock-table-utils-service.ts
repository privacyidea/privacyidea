import { WritableSignal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource } from "@angular/material/table";
import { ContainerDetailToken } from "src/app/services/container/container.service";
import { TokenApplication } from "src/app/services/machine/machine.service";
import { TableUtilsServiceInterface, ColumnKey, ColumnDef } from "src/app/services/table-utils/table-utils.service";

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

  pickColumns<const K extends readonly ColumnKey[]>(
    ...keys: K
  ): {
    readonly [I in keyof K]: Readonly<{
      key: Extract<K[I], ColumnKey>;
      label: string;
    }>;
  } {
    return keys.map((k) => ({ key: k as Extract<typeof k, ColumnKey>, label: String(k) })) as any;
  }

  getColumnKeys<const C extends readonly ColumnDef[]>(
    cols: C
  ): {
    readonly [I in keyof C]: C[I] extends Readonly<{
      key: infer KK extends ColumnKey;
      label: string;
    }>
      ? KK
      : never;
  } {
    return cols.map((c) => c.key) as any;
  }

  getSortIcon(columnKey: string, sort: Sort): string {
    return "";
  }

  onSortButtonClick(key: string, sort: WritableSignal<Sort>): void {}

  clientsideSortTokenData(data: ContainerDetailToken[], s: Sort): ContainerDetailToken[] {
    return data;
  }

  handleColumnClick = jest.fn();
}
