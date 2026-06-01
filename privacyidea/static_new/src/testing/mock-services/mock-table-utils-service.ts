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
import { signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource } from "@angular/material/table";
import { ContainerDetailToken } from "@services/container/container.service";
import { TokenApplication } from "@services/machine/machine.service";
import { ColumnDef, ColumnKey, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

export class MockTableUtilsService implements TableUtilsServiceInterface {
  pageSizeOptions = signal([5, 10, 25, 50]);
  emptyDataSource = jest.fn().mockImplementation(() => new MatTableDataSource<TokenApplication>([]));
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
    return keys.map((k) => ({ key: k, label: String(k) })) as {
      readonly [I in keyof K]: ColumnDef<Extract<K[I], ColumnKey>>;
    };
  }

  getColumnKeys<const C extends readonly ColumnDef[]>(cols: C) {
    return cols.map((c) => c.key) as {
      readonly [I in keyof C]: C[I] extends ColumnDef<infer KK> ? KK : never;
    };
  }

  getSortIcon = jest.fn().mockReturnValue("");
  onSortButtonClick = jest.fn();
  clientsideSortTokenData(data: ContainerDetailToken[], _s: Sort): ContainerDetailToken[] {
    void _s;
    return data;
  }

  handleColumnClick = jest.fn();
}
