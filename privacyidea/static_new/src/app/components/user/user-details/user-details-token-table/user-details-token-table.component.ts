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
import { NgClass } from "@angular/common";
import { AfterViewInit, Component, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIcon } from "@angular/material/icon";
import { Sort } from "@angular/material/sort";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerDetailToken } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { forkJoin } from "rxjs";

@Component({
  selector: "app-user-details-token-table",
  imports: [
    CopyableComponent,
    MatButton,
    MatCell,
    MatCellDef,
    MatCheckbox,
    MatColumnDef,
    MatHeaderCell,
    MatHeaderRow,
    MatHeaderRowDef,
    MatIcon,
    MatIconButton,
    MatRow,
    MatRowDef,
    MatTable,
    MatTooltip,
    NgClass,
    MatHeaderCellDef,
    MatNoDataRow
  ],
  templateUrl: "./user-details-token-table.component.html",
  styleUrl: "./user-details-token-table.component.scss"
})
export class UserDetailsTokenTableComponent implements AfterViewInit {
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "serial",
    "tokentype",
    "active",
    "description",
    "failcount",
    "maxfail",
    "container_serial"
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];

  get displayedColumns(): string[] {
    return ["select", ...this.columnsKeyMap.map((column) => column.key)];
  }

  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
  selection: WritableSignal<ContainerDetailToken[]> = linkedSignal({
    source: () =>
      this.tokenService.userTokenResource.hasValue() ? this.tokenService.userTokenResource.value() : undefined,
    computation: () => []
  });
  userTokenData: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: () =>
      this.tokenService.userTokenResource.hasValue() ? this.tokenService.userTokenResource.value() : undefined,
    computation: (userTokenResource, previous) => {
      if (!userTokenResource) {
        return previous?.value ?? new MatTableDataSource<TokenDetails>([]);
      }
      return new MatTableDataSource<TokenDetails>(userTokenResource.result?.value?.tokens ?? []);
    }
  });

  constructor() {
    effect(() => {
      if (!this.userTokenData) {
        return;
      }
      const base = this.userTokenData().data ?? [];
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData(
        base as unknown as ContainerDetailToken[],
        this.sort()
      );
    });

    effect(() => {
      const s = this.sort();
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData([...this.dataSource.data], s);
    });
  }

  ngAfterViewInit(): void {
    (this.dataSource as unknown as { _sort: WritableSignal<Sort> })._sort = this.sort;
  }

  isAllSelected(): boolean {
    return this.selection().length === this.dataSource.data.length && this.dataSource.data.length > 0;
  }

  toggleAllRows(): void {
    if (this.isAllSelected()) {
      this.selection.set([]);
    } else {
      this.selection.set([...this.dataSource.data]);
    }
  }

  toggleRow(row: ContainerDetailToken): void {
    const current = this.selection();
    if (current.includes(row)) {
      this.selection.set(current.filter((r) => r !== row));
    } else {
      this.selection.set([...current, row]);
    }
  }

  deleteSelected(): void {
    const serials = this.selection().map((r) => r.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serials, () => this.tokenService.userTokenResource.reload());
  }

  unassignSelected(): void {
    const serials = this.selection().map((r) => r.serial);
    forkJoin(serials.map((s) => this.tokenService.unassignUser(s))).subscribe({
      next: () => this.tokenService.userTokenResource.reload()
    });
  }

  toggleActiveSelected(): void {
    const rows = this.selection();
    forkJoin(rows.map((r) => this.tokenService.toggleActive(r.serial, r.active))).subscribe({
      next: () => this.tokenService.userTokenResource.reload()
    });
  }

  resetFailcountSelected(): void {
    const serials = this.selection().map((r) => r.serial);
    forkJoin(serials.map((s) => this.tokenService.resetFailCount(s))).subscribe({
      next: () => this.tokenService.userTokenResource.reload()
    });
  }
}
