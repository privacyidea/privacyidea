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
import { Component, ViewChild, WritableSignal, inject, linkedSignal } from "@angular/core";
import {
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface
} from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { animate, state, style, transition, trigger } from "@angular/animations";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { FormsModule } from "@angular/forms";
import { KeywordFilterComponent } from "../../shared/keyword-filter/keyword-filter.component";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";

const columnsKeyMap = [
  { key: "select", label: "" },
  { key: "serial", label: "Serial" },
  { key: "type", label: "Type" },
  { key: "states", label: "Status" },
  { key: "description", label: "Description" },
  { key: "user_name", label: "User" },
  { key: "user_realm", label: "Realm" },
  { key: "realms", label: "Container Realms" }
];

@Component({
  selector: "app-container-table",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    KeywordFilterComponent,
    CopyButtonComponent,
    MatCheckboxModule,
    FormsModule,
    ScrollToTopDirective,
    ClearableInputComponent
  ],
  templateUrl: "./container-table.component.html",
  styleUrl: "./container-table.component.scss",
  animations: [
    trigger("detailExpand", [
      state("collapsed", style({ height: "0px", minHeight: "0" })),
      state("expanded", style({ height: "*" })),
      transition("expanded <=> collapsed", animate("225ms cubic-bezier(0.4, 0.0, 0.2, 1)"))
    ])
  ]
})
export class ContainerTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly columnsKeyMap = columnsKeyMap;
  readonly columnKeys: string[] = columnsKeyMap.map((column) => column.key);
  readonly apiFilter = this.containerService.apiFilter;
  readonly advancedApiFilter = this.containerService.advancedApiFilter;
  containerSelection = this.containerService.containerSelection;

  pageSize = this.containerService.pageSize;
  pageIndex = this.containerService.pageIndex;
  sort = this.containerService.sort;
  containerResource = this.containerService.containerResource;

  containerDataSource: WritableSignal<MatTableDataSource<ContainerDetailData>> = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource, previous) => {
      if (containerResource && containerResource.result?.value) {
        const processedData =
          containerResource.result?.value?.containers.map((item) => ({
            ...item,
            user_name: item.users && item.users.length > 0 ? item.users[0].user_name : "",
            user_realm: item.users && item.users.length > 0 ? item.users[0].user_realm : ""
          })) ?? [];
        return new MatTableDataSource<ContainerDetailData>(processedData);
      }
      return previous?.value ?? new MatTableDataSource<ContainerDetailData>([]);
    }
  });

  total: WritableSignal<number> = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource, previous) => {
      if (containerResource) {
        return containerResource.result?.value?.count ?? 0;
      }
      return previous?.value ?? 0;
    }
  });

  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  @ViewChild("filterHTMLInputElement", { static: true })
  filterInput!: HTMLInputElement;
  expandedElement: ContainerDetailData | null = null;

  isAllSelected() {
    return (
      this.containerSelection().length === this.containerDataSource().data.length &&
      this.containerDataSource().data.length > 0
    );
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.containerSelection.set([]);
    } else {
      this.containerSelection.set([...this.containerDataSource().data]);
    }
  }

  toggleRow(row: ContainerDetailData): void {
    const current = this.containerSelection();
    if (current.includes(row)) {
      this.containerSelection.set(current.filter((r) => r !== row));
    } else {
      this.containerSelection.set([...current, row]);
    }
  }

  handleStateClick(element: ContainerDetailData) {
    this.containerService.toggleActive(element.serial, element.states).subscribe({
      next: () => {
        this.containerResource.reload();
      },
      error: (error) => {
        console.error("Failed to toggle active.", error);
      }
    });
  }

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.containerService.eventPageSize = event.pageSize;
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sort.set($event);
  }
}
