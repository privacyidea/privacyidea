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
import { Component, effect, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
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
import { MatPaginator } from "@angular/material/paginator";
import { MatSort } from "@angular/material/sort";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import {
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-user-details-container-table",
  imports: [
    CopyButtonComponent,
    ClearableInputComponent,
    MatHeaderRowDef,
    MatRowDef,
    MatNoDataRow,
    MatFormField,
    MatLabel,
    MatInput,
    MatPaginator,
    MatTable,
    MatSort,
    MatHeaderCellDef,
    MatColumnDef,
    MatHeaderCell,
    MatCellDef,
    MatCell,
    NgClass,
    MatTooltip,
    MatHeaderRow,
    MatRow,
    MatFormField,
    MatLabel
  ],
  templateUrl: "./user-details-container-table.component.html",
  styleUrl: "./user-details-container-table.component.scss"
})
export class UserDetailsContainerTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "serial",
    "type",
    "states",
    "description",
    "realms"
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  displayedColumns: string[] = this.columnsKeyMap.map(c => c.key);

  dataSource = new MatTableDataSource<ContainerDetailData>([]);
  filterValue = "";

  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  userContainers: WritableSignal<ContainerDetailData[]> = linkedSignal({
    source: this.containerService.containerResource.value,
    computation: (containerResource, previous) => {
      if (!containerResource?.result?.value) {
        return previous?.value ?? [];
      }

      return containerResource.result.value.containers ?? [];
    }
  });

  constructor() {
    effect(() => {
      this.dataSource.data = this.userContainers();
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

    this.dataSource.filterPredicate = (row: ContainerDetailData, filter: string) => {
      const currentState = (row.states?.[0] ?? "").toString();
      const realmsJoined = (row.realms ?? []).join(" ");
      const haystack = [
        row.serial,
        row.type,
        row.description ?? "",
        currentState,
        realmsJoined
      ].join(" ").toLowerCase();

      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    this.filterValue = ($event.target as HTMLInputElement).value.trim().toLowerCase();
    this.dataSource.filter = this.filterValue;
  }

  onPageSizeChange(size: number) {
    this.pageSize = size;
  }

  handleStateClick(element: ContainerDetailData) {
    this.containerService.toggleActive(element.serial, element.states).subscribe({
      next: () => this.containerService.containerResource.reload()
    });
  }
}
