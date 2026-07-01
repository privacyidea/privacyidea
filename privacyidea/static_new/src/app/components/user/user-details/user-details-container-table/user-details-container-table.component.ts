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
import { Component, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
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
import {
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

@Component({
  selector: "app-user-details-container-table",
  imports: [
    CopyableComponent,
    MatHeaderRowDef,
    MatRowDef,
    MatNoDataRow,
    MatTable,
    MatHeaderCellDef,
    MatColumnDef,
    MatHeaderCell,
    MatCellDef,
    MatCell,
    NgClass,
    MatTooltip,
    MatHeaderRow,
    MatRow,
    MatIcon,
    MatIconButton
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

  readonly columnsKeyMap = this.tableUtilsService.pickColumns("serial", "type", "states", "description", "realms");
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];

  get displayedColumns(): string[] {
    const columns: string[] = this.columnsKeyMap.map((c) => c.key);
    if (this.authService.actionAllowed("container_unassign_user")) {
      columns.push("remove");
    }
    if (this.authService.actionAllowed("container_delete")) {
      columns.push("delete");
    }
    return columns;
  }

  dataSource = new MatTableDataSource<ContainerDetailData>([]);
  sort = signal({ active: "serial", direction: "asc" } as Sort);

  userContainers: WritableSignal<ContainerDetailData[]> = linkedSignal({
    source: () => ({
      value: this.containerService.userContainersResource.hasValue()
        ? this.containerService.userContainersResource.value()
        : undefined,
      isLoading: this.containerService.userContainersResource.isLoading(),
      error: this.containerService.userContainersResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return [];
      if (!source.value) return source.isLoading ? (previous?.value ?? []) : [];

      return source.value.result?.value?.containers ?? [];
    }
  });

  constructor() {
    (this.dataSource as unknown as { _sort: WritableSignal<Sort> })._sort = this.sort;

    effect(() => {
      const base = this.userContainers();
      this.dataSource.data = this.clientsideSortContainerData(base, this.sort());
    });

    effect(() => {
      const s = this.sort();
      this.dataSource.data = this.clientsideSortContainerData([...this.dataSource.data], s);
    });
  }

  handleStateClick(element: ContainerDetailData) {
    this.containerService.toggleActive(element.serial, element.states).subscribe({
      next: () => this.containerService.userContainersResource.reload()
    });
  }

  unassignUser(element: ContainerDetailData) {
    const assignedUser = element.users?.[0];
    const username = assignedUser?.user_name ?? element.user_name ?? "";
    const userRealm = assignedUser?.user_realm ?? element.user_realm ?? "";
    this.containerService.unassignUser(element.serial, username, userRealm).subscribe({
      next: () => this.containerService.userContainersResource.reload()
    });
  }

  deleteContainer(element: ContainerDetailData) {
    this.containerService.deleteContainer(element.serial).subscribe({
      next: () => this.containerService.userContainersResource.reload()
    });
  }

  private clientsideSortContainerData(data: ContainerDetailData[], s: Sort) {
    if (!s.direction) return data;
    const dir = s.direction === "asc" ? 1 : -1;
    const key = s.active as keyof ContainerDetailData;
    return data.sort((a: ContainerDetailData, b: ContainerDetailData) => {
      const va = (a[key] ?? "").toString().toLowerCase();
      const vb = (b[key] ?? "").toString().toLowerCase();
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }
}
