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
import {
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  WritableSignal,
  computed,
  inject,
  linkedSignal
} from "@angular/core";
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
import { ContainerTableActionsComponent } from "@components/container/container-table/container-table-actions/container-table-actions.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { inlineFilterHint } from "@utils/filter-hint.utils";
@Component({
  selector: "app-container-table",
  standalone: true,
  imports: [
    FilterAutocompleteDirective,
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
    ContainerTableActionsComponent,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    ScrollEdgesDirective
  ],
  templateUrl: "./container-table.component.html",
  styleUrl: "./container-table.component.scss"
})
export class ContainerTableComponent implements OnDestroy {
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
  readonly apiFilterKeys = this.containerService.apiFilterKeys;
  readonly advancedApiFilterKeys = this.containerService.advancedApiFilterKeys;
  readonly filterKeywords = [...this.containerService.apiFilterKeys, ...this.containerService.advancedApiFilterKeys];
  readonly filterHint = inlineFilterHint();
  // The `user` and `realm` filters are exact values that the backend resolves against the user store, so
  // they are only applied when the input is confirmed with enter. All other filters are applied while typing.
  protected readonly filterInputValue = linkedSignal({
    source: () => this.containerService.activeFilter().filterString,
    computation: (filterString) => filterString
  });
  readonly showFilterHint = computed(() => {
    const current = this.filterInputValue().trim().toLowerCase();
    const applied = this.containerService.activeFilter().filterString.trim().toLowerCase();

    if (current !== applied) {
      return /(^|\s)user:/.test(current) || /(^|\s)realm:/.test(current);
    }
    return false;
  });
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
    user_realm: "realm",
    realms: "container_realm"
  } as const;

  ngOnDestroy(): void {
    this.containerSelection.deselectAllRows();
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

  onFilterInput($event: Event) {
    const input = $event.target as HTMLInputElement;
    this.filterInputValue.set(input.value);
    const value = input.value.toLowerCase();
    const hasUser = /(^|\s)user:/.test(value);
    const hasRealm = /(^|\s)realm:/.test(value);
    if (!hasUser && !hasRealm) {
      this.containerService.handleFilterInput($event);
    }
  }

  toggleFilter(filterKeyword: string): void {
    this.containerService.updateFilter((current) =>
      this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: current
      })
    );
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    const isSelected = this.isFilterSelected(keyword, this.containerService.activeFilter());
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  onItemSelected(keyword: string, value: string | undefined): void {
    this.containerService.updateFilter((current) =>
      value ? current.addEntry(keyword, value) : current.removeKey(keyword)
    );
  }
}
