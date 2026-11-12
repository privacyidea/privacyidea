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
import { TableActionsTriggerComponent } from "@components/shared/table-actions/table-actions-trigger.component";
import { MatSuffix } from "@angular/material/form-field";
import { MatTooltip } from "@angular/material/tooltip";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import {
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  viewChild,
  WritableSignal,
  computed,
  effect,
  inject,
  linkedSignal,
  signal,
  untracked
} from "@angular/core";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import {
  CONTAINER_STATE_OPTIONS,
  ContainerDetailData,
  ContainerService,
  ContainerTemplateComparisonRow,
  ContainerServiceInterface,
  TEMPLATE_FILTER_ANY,
  TEMPLATE_FILTER_NONE
} from "@services/container/container.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { RefocusAfterReloadDirective } from "@components/shared/directives/refocus-after-reload.directive";

import { NgClass } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDividerModule } from "@angular/material/divider";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerTableActionsComponent } from "@components/container/container-table/container-table-actions/container-table-actions.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "@services/container-template/container-template.service";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { PaginatorPageSizeTooltipDirective } from "@components/shared/directives/paginator-page-size-tooltip.directive";
import { PaginatorCompactRangeDirective } from "@components/shared/directives/paginator-compact-range.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { TableState } from "@core/models/table_state/table-state";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { filterMatchTooltip, inlineFilterHint } from "@utils/filter-hint.utils";
import { exactMatch, withUser } from "@utils/filter.utils";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";
import { FilterByLabelPipe, SortByLabelPipe } from "@components/shared/pipes/aria-label.pipe";
import { ScrollFocusableDirective } from "@components/shared/directives/scroll-focusable.directive";

// width: the col-width-* tier (see --column-width-* in styles.scss) each column's cell is fixed
// to, so the columns line up on the same scale other tables use and the table-state placeholder
// (see table-width() in table.scss) can be sized from the same numbers.
const columnsKeyMap = [
  { key: "select", label: "", width: "s" },
  { key: "serial", label: $localize`:@@common.serial:Serial`, width: "m" },
  { key: "type", label: $localize`:@@common.type:Type`, width: "s" },
  { key: "states", label: $localize`:@@common.status:Status`, width: "m" },
  { key: "description", label: $localize`:@@common.description:Description`, width: "xl" },
  { key: "user_name", label: $localize`:@@common.user:User`, width: "s" },
  { key: "user_realm", label: $localize`:@@common.realm:Realm`, width: "s" },
  { key: "realms", label: $localize`:@@common.containerRealms:Container Realms`, width: "m" }
];

// Shown only while the comparison is visible.
const comparisonColumnsKeyMap = [
  { key: "template", label: $localize`:@@container.template:Template`, width: "l" },
  { key: "differences", label: $localize`:@@container.differences:Differences`, width: "l" }
];

@Component({
  selector: "app-container-table",
  standalone: true,
  imports: [
    TableActionsTriggerComponent,
    ScrollFocusableDirective,
    FilterByLabelPipe,
    SortByLabelPipe,
    TruncationTooltipDirective,
    InfoHintComponent,
    MatSuffix,
    MatTooltip,
    RefocusAfterReloadDirective,
    FilterAutocompleteDirective,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    NgClass,
    CopyButtonComponent,
    CopyableComponent,
    FilterValueButtonComponent,
    MatCheckboxModule,
    ScrollToTopDirective,
    ClearableInputComponent,
    ContainerTableActionsComponent,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatTooltip,
    MatDividerModule,
    ScrollEdgesDirective,
    TableStateComponent,
    RouterLink,
    PaginatorPageSizeTooltipDirective,
    PaginatorCompactRangeDirective
  ],
  templateUrl: "./container-table.component.html",
  styleUrl: "./container-table.component.scss"
})
export class ContainerTableComponent implements OnDestroy {
  protected selectRowLabel(serial: string): string {
    return $localize`:@@container.selectContainerNamed:Select container ${serial}:SERIAL:`;
  }

  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);

  readonly columnsKeyMap = columnsKeyMap;
  readonly columnKeys = columnsKeyMap.map((column) => column.key);
  readonly unsortableColumnKeys = ["template", ...comparisonColumnsKeyMap.map((column) => column.key)];
  readonly comparisonByContainerSerial = signal<Record<string, ContainerTemplateComparisonRow>>({});
  readonly comparisonVisible = signal(false);
  readonly displayedColumns = computed(() =>
    this.comparisonVisible() ? [...columnsKeyMap, ...comparisonColumnsKeyMap] : columnsKeyMap
  );
  readonly displayedColumnKeys = computed(() => this.displayedColumns().map((column) => column.key));
  readonly apiFilterKeys = this.containerService.apiFilterKeys;
  readonly advancedApiFilterKeys = this.containerService.advancedApiFilterKeys;
  readonly toolbarFilterKeys = this.advancedApiFilterKeys.filter((keyword) => keyword !== "template");
  readonly filterKeywords = [...this.containerService.apiFilterKeys, ...this.containerService.advancedApiFilterKeys];
  readonly filterHint = inlineFilterHint();
  readonly filterMatchInfo = computed(() =>
    filterMatchTooltip(
      $localize`:@@common.container:Container`,
      [...this.containerService.apiFilterKeys, ...this.containerService.advancedApiFilterKeys],
      (key) => this.containerService.exactMatchKeys.has(key)
    )
  );
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
      // A reload in flight (filter/page/sort change) clears containerResource.value before the
      // new response arrives - keep showing the previous rows instead of flashing empty, now that
      // the table itself stays mounted through a reload (see TableState.lastKnownCount).
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

  readonly ROUTE_PATHS = ROUTE_PATHS;
  readonly tableState = new TableState({
    resource: this.containerResource,
    count: () => this.total(),
    filterActive: () => !this.containerService.activeFilter().isEmpty,
    allowed: () => this.authService.actionAllowed("container_list"),
    resetFilter: () => this.containerService.clearFilter()
  });
  readonly emptyHint = computed(() =>
    this.authService.actionAllowed("container_create")
      ? $localize`:@@container.createYourFirstContainerTo2:Create your first container to assign tokens to a user or a device.`
      : ""
  );

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

  showComparison(rows: ContainerTemplateComparisonRow[]): void {
    this.comparisonByContainerSerial.update((current) => ({
      ...current,
      ...Object.fromEntries(rows.map((row) => [row.containerSerial, row]))
    }));
    this.comparisonVisible.set(true);
  }

  private readonly containerTableActions = viewChild(ContainerTableActionsComponent);
  private lastListState: unknown[] = [];

  // While the comparison is visible, paging, a new page size, sorting or filtering compares the new rows again
  // as soon as the new list has loaded. A plain reload of the same list keeps the comparison untouched.
  private readonly recompareOnListChange = effect(() => {
    const state = [
      this.containerService.pageIndex(),
      this.containerService.pageSize(),
      this.containerService.sort(),
      this.containerService.activeFilter()
    ];
    const loading = this.containerService.containerResource.isLoading();
    this.containerService.containerResource.value();
    const changed = state.some((part, i) => part !== this.lastListState[i]);
    if (!changed || (this.comparisonVisible() && loading)) {
      return;
    }
    this.lastListState = state;
    if (this.comparisonVisible()) {
      untracked(() => {
        // The map is replaced, not merged, so rows of the old list disappear.
        this.comparisonByContainerSerial.set({});
        void this.containerTableActions()?.compareDisplayedContainers();
      });
    }
  });

  hideComparison(): void {
    this.comparisonVisible.set(false);
    this.comparisonByContainerSerial.set({});
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
      filterKeyword === "assigned"
        ? this.tableUtilsService.toggleBooleanInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
        : this.tableUtilsService.toggleKeywordInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
    );
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "assigned") {
      const value = this.containerService.activeFilter().booleanValueOfKey(keyword);
      if (value === undefined) {
        return "filter_alt";
      }
      return value ? "screen_rotation_alt" : "filter_alt_off";
    }
    const isSelected = this.isFilterSelected(keyword, this.containerService.activeFilter());
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  filterByUser(username: string, realm: string): void {
    this.containerService.updateFilter((current) => withUser(current, username, realm));
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

  onTemplateFilterSelected(
    selection: "all" | "with-template" | "without-template" | "specific",
    templateName?: string
  ): void {
    this.containerService.updateFilter((current) => {
      const filter = current.removeKey("template").removeKey("has_template");
      if (selection === "with-template") {
        return filter.addEntry("template", TEMPLATE_FILTER_ANY);
      }
      if (selection === "without-template") {
        return filter.addEntry("template", TEMPLATE_FILTER_NONE);
      }
      if (selection === "specific" && templateName) {
        return filter.addEntry("template", exactMatch(templateName));
      }
      return filter;
    });
  }
}
