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
import { Component, ElementRef, ViewChild, WritableSignal, inject, linkedSignal } from "@angular/core";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import {
  CONTAINER_STATE_OPTIONS,
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface
} from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { NgClass } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDividerModule } from "@angular/material/divider";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ContainerTableActionsComponent } from "@components/container/container-table/container-table-actions/container-table-actions.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { FilterHintComponent } from "@components/shared/filter-hint/filter-hint.component";
import { filterColumnHint } from "@utils/filter-hint.utils";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
@Component({
  selector: "app-container-table",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    NgClass,
    CopyButtonComponent,
    CopyableComponent,
    MatCheckboxModule,
    ScrollToTopDirective,
    ClearableInputComponent,
    FilterHintComponent,
    ContainerTableActionsComponent,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    MatTooltipModule,
    ScrollEdgesDirective
  ],
  templateUrl: "./container-table.component.html",
  styleUrl: "./container-table.component.scss"
})
export class ContainerTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "select",
    "serial",
    "type",
    "states",
    "description",
    "user_name",
    "user_realm",
    "realms"
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  readonly apiFilter = this.containerService.apiFilter;
  readonly advancedApiFilter = this.containerService.advancedApiFilter;
  containerSelection = this.containerService.containerSelection;

  pageSize = this.containerService.pageSize;
  pageIndex = this.containerService.pageIndex;
  sort = this.containerService.sort;
  containerResource = this.containerService.containerResource;

  readonly containerStateOptions = CONTAINER_STATE_OPTIONS;

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

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;
  expandedElement: ContainerDetailData | null = null;

  readonly apiFilterKeyMap: Record<string, string> = {
    serial: "container_serial",
    type: "type",
    states: "state",
    description: "description",
    user_name: "user",
    realms: "container_realm"
  } as const;

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
    this.containerService.eventPageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sort.set($event);
  }

  toggleFilter(filterKeyword: string): void {
    const newValue = this.tableUtilsService.toggleKeywordInFilter({
      keyword: filterKeyword,
      currentValue: this.containerService.containerFilter()
    });
    this.containerService.containerFilter.set(newValue);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    const isSelected = this.isFilterSelected(keyword, this.containerService.containerFilter());
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  filterColumnTooltip(label: string, keyword: string): string {
    return filterColumnHint(label, {
      exactMatch: this.containerService.exactMatchKeys.has(keyword),
      caseSensitive: this.containerService.caseSensitiveKeys.has(keyword),
      isBoolean: this.containerService.booleanKeys.has(keyword)
    });
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  onItemSelected(keyword: string, value: string | undefined): void {
    if (!value) {
      this.containerService.containerFilter.set(this.containerService.containerFilter().removeKey(keyword));
    } else {
      this.containerService.containerFilter.set(this.containerService.containerFilter().addEntry(keyword, value));
    }
  }
}
