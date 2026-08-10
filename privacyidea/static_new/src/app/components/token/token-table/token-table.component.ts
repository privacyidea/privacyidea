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
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatDividerModule } from "@angular/material/divider";
import { MatMenuModule } from "@angular/material/menu";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";

import { NgClass } from "@angular/common";
import { MatIconButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { MultiSelectFilterComponent } from "@components/shared/multi-select-filter/multi-select-filter.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { filterColumnHint, inlineFilterHint } from "@utils/filter-hint.utils";
import { withDefaultRealm } from "@utils/filter.utils";
import { StringUtils } from "@utils/string.utils";
import { TokenTableActionsComponent } from "./token-table-actions/token-table-actions.component";

const columnKeysMap = [
  { key: "select", label: "" },
  { key: "serial", label: $localize`Serial` },
  { key: "tokentype", label: $localize`Type` },
  { key: "active", label: $localize`Active` },
  { key: "description", label: $localize`Description` },
  { key: "failcount", label: $localize`Fail Counter` },
  { key: "rollout_state", label: $localize`Rollout State` },
  { key: "username", label: $localize`User` },
  { key: "user_realm", label: $localize`User Realm` },
  { key: "realms", label: $localize`Token Realm` },
  { key: "container_serial", label: $localize`Container` }
];

@Component({
  selector: "app-token-table",
  standalone: true,
  imports: [
    FilterAutocompleteDirective,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    MatCheckboxModule,
    MatIconModule,
    ScrollToTopDirective,
    ClearableInputComponent,
    CopyableComponent,
    MultiSelectFilterComponent,
    TokenTableActionsComponent,
    MatIconButton,
    MatMenuModule,
    MatDividerModule,
    MatTooltipModule,
    ScrollEdgesDirective
  ],
  templateUrl: "./token-table.component.html",
  styleUrl: "./token-table.component.scss"
})
export class TokenTableComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);

  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = columnKeysMap.map((column) => column.key);
  readonly apiFilterKeyMap = this.tokenService.apiFilterKeyMap;
  readonly advancedApiFilterKeys = this.tokenService.advancedApiFilterKeys;
  readonly filterKeywords = [...this.tokenService.apiFilterKeys, ...this.tokenService.advancedApiFilterKeys].filter(
    (keyword) => !keyword.includes(" ")
  );
  readonly filterHint = inlineFilterHint();
  readonly tokenTypeFilterOptions = computed(() => this.tokenService.tokenTypeOptions().map((type) => type.key));
  private basePageSizeOptions = [...this.tableUtilsService.pageSizeOptions()];
  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;
  tokenSelection = this.tokenService.tokenSelection;
  tokenResource = this.tokenService.tokenResource;
  activeFilter = this.tokenService.activeFilter;
  pageSize = this.tokenService.pageSize;
  pageIndex = this.tokenService.pageIndex;
  sort = this.tokenService.sort;

  constructor() {
    effect(() => {
      if (!this.contentService.onTokens()) {
        return;
      }
      const preset = this.tokenService.presetFilter();
      if (preset) {
        this.tokenService.presetFilter.set(null);
        this.tokenService.setFilter(preset);
      }
    });
  }
  protected readonly filterInputValue = linkedSignal({
    source: () => this.tokenService.activeFilter().filterString,
    computation: (v) => v
  });
  protected readonly showFilterHint = computed(() => {
    const current = this.filterInputValue().trim().toLowerCase();
    const applied = this.tokenService.activeFilter().filterString.trim().toLowerCase();

    if (current !== applied) {
      const hasUser = /(^|\s)user:/.test(current);
      const hasRealm = /(^|\s)realm:/.test(current);
      return hasUser || hasRealm;
    }
    return false;
  });
  emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        const emptyRow: Record<string, string> = {};
        columnKeysMap.forEach((column) => {
          emptyRow[column.key] = "";
        });
        return emptyRow as unknown as TokenDetails;
      })
  });
  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: () => ({ value: this.tokenService.tokenResourceValue(), error: this.tokenResource.error() }),
    computation: (src, previous) => {
      if (src.error) {
        return new MatTableDataSource<TokenDetails>([]);
      }
      if (src.value) {
        return new MatTableDataSource(src.value.tokens);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
  totalLength: WritableSignal<number> = linkedSignal({
    source: () => ({ value: this.tokenService.tokenResourceValue(), error: this.tokenResource.error() }),
    computation: (src, previous) => {
      if (src.error) {
        return 0;
      }
      if (src.value) {
        return src.value.count;
      }
      return previous?.value ?? 0;
    }
  });
  pageSizeOptions = computed(() => {
    if (!this.basePageSizeOptions.includes(this.pageSize())) {
      this.basePageSizeOptions.push(this.pageSize());
      this.basePageSizeOptions.sort((a, b) => a - b);
    }
    return this.basePageSizeOptions;
  });

  isAllSelected() {
    return this.tokenSelection().length === this.tokenDataSource().data.length;
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.tokenSelection.set([]);
    } else {
      this.tokenSelection.set([...this.tokenDataSource().data]);
    }
  }

  toggleRow(tokenDetails: TokenDetails): void {
    const current = this.tokenSelection();
    if (current.includes(tokenDetails)) {
      this.tokenSelection.set(current.filter((r) => r !== tokenDetails));
    } else {
      this.tokenSelection.set([...current, tokenDetails]);
    }
  }

  toggleActive(tokenDetails: TokenDetails): void {
    if (
      !tokenDetails.revoked &&
      !tokenDetails.locked &&
      ((tokenDetails.active && this.authService.actionAllowed("disable")) ||
        (!tokenDetails.active && this.authService.actionAllowed("enable")))
    ) {
      this.tokenService.toggleActive(tokenDetails.serial, tokenDetails.active).subscribe({
        next: () => {
          this.tokenResource.reload();
        }
      });
    }
  }

  resetFailCount(tokenDetails: TokenDetails): void {
    if (!tokenDetails.revoked && !tokenDetails.locked && this.authService.actionAllowed("reset")) {
      this.tokenService.resetFailCount(tokenDetails.serial).subscribe({
        next: () => {
          this.tokenResource.reload();
        }
      });
    }
  }

  onSortEvent($event: Sort) {
    if (!$event.direction) {
      this.sort.set({ active: "serial", direction: "asc" });
    } else {
      this.sort.set({ active: $event.active, direction: $event.direction });
    }
  }

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.tokenService.eventPageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onFilterInput($event: Event) {
    const input = $event.target as HTMLInputElement;
    this.filterInputValue.set(input.value);
    const value = input.value.toLowerCase();
    const hasUser = /(^|\s)user:/.test(value);
    const hasRealm = /(^|\s)realm:/.test(value);
    if (!hasUser && !hasRealm) {
      this.tokenService.handleFilterInput($event);
    }
  }

  toggleFilter(filterKeyword: string): void {
    this.tokenService.updateFilter((current) => {
      let newValue =
        filterKeyword === "active"
          ? this.tableUtilsService.toggleBooleanInFilter({
              keyword: filterKeyword,
              currentValue: current
            })
          : this.tableUtilsService.toggleKeywordInFilter({
              keyword: filterKeyword,
              currentValue: current
            });

      if (filterKeyword === "user") {
        newValue = withDefaultRealm(newValue, this.realmService.defaultRealm());
      }

      return newValue;
    });
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  filterColumnTooltip(label: string, keyword: string): string {
    return filterColumnHint(label, {
      exactMatch: this.tokenService.exactMatchKeys.has(keyword),
      isBoolean: this.tokenService.booleanKeys.has(keyword),
      caseNote: this.tokenService.caseNotes[keyword]
    });
  }


  getFilterIconName(keyword: string): string {
    if (keyword === "active" || keyword === "assigned") {
      const value = this.tokenService.activeFilter().booleanValueOfKey(keyword);
      if (value === undefined) {
        return "filter_alt";
      }
      return value ? "screen_rotation_alt" : "filter_alt_off";
    } else {
      const isSelected = this.isFilterSelected(keyword, this.tokenService.activeFilter());
      return isSelected ? "filter_alt_off" : "filter_alt";
    }
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    const inputElement = this.filterInput?.nativeElement;
    if (inputElement) {
      inputElement.focus();
      if (filterKeyword === "user" && this.tokenService.activeFilter().hasKey("user")) {
        setTimeout(() => {
          const filterString = inputElement.value;
          const userIndex = filterString.indexOf("user:");
          if (userIndex !== -1) {
            const focusIndex = userIndex + "user: ".length;
            inputElement.setSelectionRange(focusIndex, focusIndex);
          }
        });
      }
    }
  }

  selectedFilterValues(keyword: string): string[] {
    return StringUtils.splitFilterList(this.tokenService.filterDraft().getValueOfKey(keyword));
  }

  setFilterValues(keyword: string, values: string[]): void {
    this.tokenService.updateFilter((current) =>
      values.length ? current.addEntry(keyword, values.join(",")) : current.removeKey(keyword)
    );
  }

  onItemSelected(keyword: string, value: string): void {
    this.tokenService.updateFilter((current) =>
      value ? current.addEntry(keyword, value) : current.removeKey(keyword)
    );
    this.filterInput?.nativeElement.focus();
  }
}
