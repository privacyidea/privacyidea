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
import { MatIconButton } from "@angular/material/button";
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

@Component({
  selector: "app-user-details-token-table",
  imports: [
    CopyableComponent,
    MatCell,
    MatCellDef,
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
    const columns: string[] = this.columnsKeyMap.map((column) => column.key);
    if (this.authService.actionAllowed("unassign")) {
      columns.push("remove");
    }
    if (this.authService.actionAllowed("delete")) {
      columns.push("delete");
    }
    return columns;
  }

  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
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

  toggleActive(token: TokenDetails): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.tokenService.userTokenResource.reload();
      }
    });
  }

  resetFailCount(element: TokenDetails): void {
    if (!element.revoked && !element.locked && this.authService.actionAllowed("reset")) {
      this.tokenService.resetFailCount(element.serial).subscribe({
        next: () => {
          this.tokenService.userTokenResource.reload();
        }
      });
    }
  }

  unassignToken(element: TokenDetails): void {
    this.tokenService.unassignUser(element.serial).subscribe({
      next: () => {
        this.tokenService.userTokenResource.reload();
      }
    });
  }

  deleteToken(element: TokenDetails): void {
    this.tokenService.deleteToken(element.serial).subscribe({
      next: () => {
        this.tokenService.userTokenResource.reload();
      }
    });
  }
}
