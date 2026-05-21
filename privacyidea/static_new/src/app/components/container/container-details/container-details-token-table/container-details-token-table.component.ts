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
import {
  Component,
  computed,
  ElementRef,
  inject,
  Input,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { MatFormField, MatLabel } from "@angular/material/select";
import { Sort } from "@angular/material/sort";
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableDataSource,
  MatTableModule
} from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";

type ComparisonStatus = "excess" | "missing" | "correct";

type ContainerDetailTokenData = {
  token: ContainerDetailToken;
  columnKey: string;
  status: ComparisonStatus;
};

@Component({
  selector: "app-container-details-token-table",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatLabel,
    MatRow,
    MatTable,
    MatTableModule,
    MatIconButton,
    CopyableComponent,
    MatPaginatorModule,
    NgClass,
    MatIconModule,
    MatTooltipModule,
    MatInput,
    ClearableInputComponent
  ],
  templateUrl: "./container-details-token-table.component.html",
  styleUrl: "./container-details-token-table.component.scss"
})
export class ContainerDetailsTokenTableComponent {
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns("serial", "tokentype", "active", "username");
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  displayedColumns: string[] = [...this.columnKeys, "actions"];
  pageSize = 5;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  pageIndex = this.tokenService.pageIndex;
  @Input() containerTokenData!: WritableSignal<MatTableDataSource<ContainerDetailToken, MatPaginator>>;

  filterValue: WritableSignal<string> = signal("");
  containerSerial = this.containerService.containerSerial;

  assignedUser: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }> = linkedSignal({
    source: () => this.containerService.containerDetails(),
    computation: (source) =>
      source.containers[0]?.users[0] ?? {
        user_realm: "",
        user_name: "",
        user_resolver: "",
        user_id: ""
      }
  });
  tokenSerial = this.tokenService.tokenSerial;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
  @ViewChild("filterInput", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  protected readonly sortedData = computed(() => {
    const source = this.containerTokenData();
    const data = source?.data ?? [];
    return this.tableUtilsService.clientsideSortTokenData([...data], this.sort());
  });

  dataSource: WritableSignal<MatTableDataSource<ContainerDetailTokenData>> = linkedSignal({
    source: () => {
      return {
        sortedData: this.sortedData(),
        comparison: this.containerService.templateComparison(),
        containerSerial: this.containerService.containerSerial()
      };
    },
    computation: (source, previous) => {
      const { sortedData, comparison, containerSerial } = source;
      const ds = previous?.value ?? new MatTableDataSource<ContainerDetailTokenData>([]);
      const comp = comparison?.[containerSerial];

      if (!comp || comp.tokens.equal) {
        ds.data = sortedData.map((token) => ({ token, columnKey: token.serial, status: "correct" }));
        return ds;
      }

      const actualCounts = new Map<string, number>();
      sortedData.forEach((t) => actualCounts.set(t.tokentype, (actualCounts.get(t.tokentype) ?? 0) + 1));

      const trackedCounts = new Map<string, number>();
      const mappedData: ContainerDetailTokenData[] = sortedData.map((token) => {
        const type = token.tokentype;
        const currentCount = (trackedCounts.get(type) ?? 0) + 1;
        trackedCounts.set(type, currentCount);

        let status: ComparisonStatus = "correct";
        const excessCountForType = comp.tokens.additional.filter((t) => t === type).length;
        const totalActualForType = actualCounts.get(type) ?? 0;

        if (currentCount > totalActualForType - excessCountForType) {
          status = "excess";
        }
        return { token, columnKey: token.serial, status };
      });

      comp.tokens.missing.forEach((missingType) => {
        mappedData.push({
          token: { tokentype: missingType, serial: "MISSING" } as ContainerDetailToken,
          columnKey: missingType,
          status: "missing"
        });
      });

      const statusPriority: Record<ComparisonStatus, number> = {
        missing: 1,
        excess: 2,
        correct: 3
      };

      mappedData.sort((a, b) => {
        if (statusPriority[a.status] !== statusPriority[b.status]) {
          return statusPriority[a.status] - statusPriority[b.status];
        }
        return a.token.tokentype.localeCompare(b.token.tokentype);
      });

      ds.data = mappedData;
      return ds;
    }
  });

  isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.assignedUser();
    if (assignedUser.user_name === "") {
      return false;
    }
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username === "");
  });

  isUnassignableFromAllToken = computed<boolean>(() => {
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username !== "");
  });

  ngAfterViewInit(): void {
    const dataSource = this.dataSource();
    dataSource.paginator = this.paginator;

    if (this.containerTokenData) {
      const externalDataSource = this.containerTokenData();
      externalDataSource.paginator = this.paginator;
      (externalDataSource as any)._sort = this.sort;
    }
    (dataSource as any)._sort = this.sort;

    dataSource.filterPredicate = (data: ContainerDetailTokenData, filter: string) => {
      const row = data.token;
      const haystack = [row.serial, row.tokentype, row.username, String(row.active)].join(" ").toLowerCase();
      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    const raw = ($event.target as HTMLInputElement).value ?? "";
    const trimmed = raw.trim();
    this.filterValue.set(trimmed);
    const normalised = trimmed.toLowerCase();
    this.dataSource().filter = normalised;

    if (this.containerTokenData) {
      this.containerTokenData().filter = normalised;
    }
  }

  clearFilter(): void {
    this.filterValue.set("");
    this.dataSource().filter = "";

    if (this.containerTokenData) {
      this.containerTokenData().filter = "";
    }
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Remove Token",
          items: [tokenSerial],
          itemType: "token",
          confirmAction: { label: "Remove", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeTokenFromContainer(containerSerial, tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailsResource.reload();
              }
            });
          }
        }
      });
  }

  handleColumnClick(columnKey: string, token: ContainerDetailToken) {
    if (columnKey === "active") {
      this.toggleActive(token);
    }
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailsResource.reload();
      }
    });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData().data.map((token) => token.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serialList, this.containerService.containerDetailsResource.reload);
  }

  deleteTokenFromContainer(tokenSerial: string) {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete Token",
          items: [tokenSerial],
          itemType: "token",
          confirmAction: { label: "Delete", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailsResource.reload();
              }
            });
          }
        }
      });
  }

  assignUserToToken(token: TokenDetails): void {
    const user = this.assignedUser();
    this.tokenService
      .assignUser({
        tokenSerial: token.serial,
        username: user.user_name,
        realm: user.user_realm
      })
      .subscribe({
        next: () => {
          this.notificationService.success("User assigned to token");
          this.containerService.containerDetailsResource.reload();
        }
      });
  }
}
