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
import { Component, effect, inject, linkedSignal, ViewChild, WritableSignal, ElementRef, signal } from "@angular/core";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
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
import { MatInput, MatLabel } from "@angular/material/input";
import { MatIconButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatPaginator } from "@angular/material/paginator";
import { MatTooltip } from "@angular/material/tooltip";
import { NgClass } from "@angular/common";
import { ContainerDetailToken } from "../../../../services/container/container.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { Sort } from "@angular/material/sort";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";

@Component({
  selector: "app-user-details-token-table",
  imports: [
    CopyButtonComponent,
    MatCell,
    MatCellDef,
    MatColumnDef,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatHeaderRowDef,
    MatIcon,
    MatIconButton,
    MatInput,
    MatLabel,
    MatPaginator,
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
export class UserDetailsTokenTableComponent {
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
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
  displayedColumns: string[] = [...this.columnsKeyMap.map((column) => column.key)];
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  filterValue = "";
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
  @ViewChild('filterInput', { static: false }) filterInput!: ElementRef<HTMLInputElement>;
  userTokenData: WritableSignal<MatTableDataSource<any, MatPaginator>> = linkedSignal({
    source: this.tokenService.userTokenResource.value,
    computation: (userTokenResource, previous) => {
      if (!userTokenResource) {
        return previous?.value ?? new MatTableDataSource<any, MatPaginator>([]);
      }
      return new MatTableDataSource<any, MatPaginator>(userTokenResource.result?.value?.tokens ?? []);
    }
  });
  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  constructor() {
    this.tokenService.userRealm.set(this.userService.selectedUserRealm());
    effect(() => {
      if (!this.userTokenData) {
        return;
      }
      const base = this.userTokenData().data ?? [];
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData(base, this.sort());
    });

    effect(() => {
      const s = this.sort();
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData([...this.dataSource.data], s);
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    (this.dataSource as any)._sort = this.sort;
    this.dataSource.filterPredicate = (row: ContainerDetailToken, filter: string) => {
      const haystack = [
        row.serial,
        row.tokentype as any,
        String(row.active),
        row.description ?? "",
        String(row.failcount ?? ""),
        String(row.maxfail ?? ""),
        row.container_serial ?? ""
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    const raw = ($event.target as HTMLInputElement).value ?? "";
    // Keep the original case but trim surrounding whitespace for display
    this.filterValue = raw.trim();
    const normalised = raw.replace(/\b\w+\s*:\s*/g, " ").trim().toLowerCase();
    this.dataSource.filter = normalised;
    if (this.userTokenData) {
      this.userTokenData().filter = normalised;
    }
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
}
