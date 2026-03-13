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

import { CommonModule, KeyValuePipe } from "@angular/common";
import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox, MatCheckboxChange } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../services/container/container.service";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import { ContainerTemplatesFilterComponent } from "./container-templates-filter/container-templates-filter.component";
import { ContainerTemplatesTableActionsComponent } from "./container-templates-table-actions/container-templates-table-actions.component";
import { ContainerTemplateEditDialogComponent } from "./dialogs/container-template-edit-dialog/container-template-edit-dialog.component";
import { ViewTemplateTokensComponent } from "./view-template-tokens/view-template-tokens.component";

const containerTemplateFilterOptions: FilterOption<ContainerTemplate>[] = [
  new FilterOption<ContainerTemplate>({
    key: "name",
    label: $localize`Name`,
    matches: (item, filter) => {
      const filterValue = filter.getFilterOfKey("name");
      return !filterValue || item.name.toLowerCase().includes(filterValue.toLowerCase());
    }
  }),
  new FilterOption<ContainerTemplate>({
    key: "container_type",
    label: $localize`Container Type`,
    matches: (item, filter) => {
      const filterValue = filter.getFilterOfKey("container_type");
      return !filterValue || item.container_type.toLowerCase().includes(filterValue.toLowerCase());
    }
  }),
  new FilterOption<ContainerTemplate>({
    key: "default",
    label: $localize`Default`,
    matches: (item, filter) => {
      const filterValue = filter.getFilterOfKey("default");
      return !filterValue || (filterValue === "true" ? item.default === true : item.default === false);
    }
  }),
  new FilterOption<ContainerTemplate>({
    key: "tokens",
    label: $localize`Tokens`,
    matches: (item, filter) => {
      const filterString = filter.getFilterOfKey("tokens");
      if (!filterString) return true;
      if (!item.template_options.tokens) return false;
      return item.template_options.tokens.some((token) =>
        Object.values(token).some((val) => val?.toString().toLowerCase().includes(filterString.toLowerCase()))
      );
    }
  })
];

@Component({
  selector: "app-container-templates",
  standalone: true,
  imports: [
    CommonModule,
    KeyValuePipe,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    ContainerTemplatesFilterComponent,
    ContainerTemplatesTableActionsComponent,
    MatCheckbox,
    ViewTemplateTokensComponent,
    MatPaginatorModule
  ],
  templateUrl: "./container-templates.component.html",
  styleUrl: "./container-templates.component.scss"
})
export class ContainerTemplatesComponent {
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly columns = {
    name: { label: $localize`Name`, filterable: true, sortable: true },
    container_type: { label: $localize`Container Type`, filterable: true, sortable: true },
    default: { label: $localize`Default`, filterable: true, sortable: true },
    tokens: { label: $localize`Tokens`, filterable: true, sortable: false }
  } as const;

  readonly columnKeys = computed(() => ["select", ...Object.keys(this.columns)]);

  readonly filter = signal<FilterValueGeneric<ContainerTemplate>>(
    new FilterValueGeneric({ availableFilters: containerTemplateFilterOptions })
  );
  readonly pageIndex = signal(0);
  readonly pageSize = signal(10);
  readonly pageSizeOptions = signal([5, 10, 25, 100]);
  readonly activeSort = signal<Sort>({ active: "", direction: "" });

  readonly emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from(
        { length: pageSize },
        () =>
          ({
            name: "",
            container_type: "",
            default: false,
            template_options: { tokens: [] }
          }) as ContainerTemplate
      )
  });

  readonly filteredContainerTemplates = computed(() => {
    const templates = this.containerTemplateService.templates();
    if (templates.length === 0) return this.emptyResource();
    return this.filter().hasActiveFilters ? this.filter().filterItems(templates) : templates;
  });

  readonly sortedContainerTemplates = computed(() => {
    const data = [...this.filteredContainerTemplates()];
    const sort = this.activeSort();

    if (!sort.active || sort.direction === "" || this.containerTemplateService.templates().length === 0) {
      return data;
    }

    return data.sort((a, b) => {
      const isAsc = sort.direction === "asc";
      const valueA = a[sort.active as keyof ContainerTemplate];
      const valueB = b[sort.active as keyof ContainerTemplate];

      if (valueA === valueB) {
        return 0;
      }

      const modifier = isAsc ? 1 : -1;

      if (typeof valueA === "string" && typeof valueB === "string") {
        return valueA.localeCompare(valueB) * modifier;
      }

      return (valueA < valueB ? -1 : 1) * modifier;
    });
  });

  readonly totalLength = computed(() => {
    const templates = this.containerTemplateService.templates();
    return templates.length > 0 ? this.filteredContainerTemplates().length : 0;
  });

  readonly pagedContainerTemplates = computed(() => {
    const data = this.sortedContainerTemplates();
    const templates = this.containerTemplateService.templates();
    if (templates.length === 0) return data;

    const startIndex = this.pageIndex() * this.pageSize();
    return data.slice(startIndex, startIndex + this.pageSize());
  });

  readonly selectedTemplateNames = linkedSignal<ContainerTemplate[], Set<string>>({
    source: () => this.pagedContainerTemplates(),
    computation: (paged, previous) => {
      const selected = new Set(previous?.value ?? []);
      if (this.containerTemplateService.templates().length === 0) {
        return new Set();
      }
      const currentPagedNames = new Set(paged.map((t) => t.name));
      for (const name of selected) {
        if (!currentPagedNames.has(name)) {
          selected.delete(name);
        }
      }
      return selected;
    }
  });

  readonly selectedTemplates = computed(() => {
    const templates = this.containerTemplateService.templates();
    if (templates.length === 0) return [];
    const selectedNames = this.selectedTemplateNames();
    return templates.filter((t) => selectedNames.has(t.name));
  });

  readonly isAllSelected = computed(() => {
    const displayedRows = this.pagedContainerTemplates().filter((r) => !!r.name);
    if (displayedRows.length === 0) return false;
    return displayedRows.every((row) => this.selectedTemplateNames().has(row.name));
  });

  readonly isPartiallySelected = computed(() => {
    const selectedCount = this.selectedTemplateNames().size;
    const displayedCount = this.pagedContainerTemplates().filter((r) => !!r.name).length;
    return selectedCount > 0 && selectedCount < displayedCount;
  });

  readonly keepOrder = () => 0;

  onSortChange(sort: Sort): void {
    this.activeSort.set(sort);
  }

  toggleAllRows(): void {
    const displayedRows = this.pagedContainerTemplates().filter((r) => !!r.name);
    if (this.isAllSelected()) {
      this.selectedTemplateNames.set(new Set());
    } else {
      this.selectedTemplateNames.set(new Set(displayedRows.map((r) => r.name)));
    }
  }

  updateSelection(event: MatCheckboxChange, template: ContainerTemplate): void {
    if (!template.name) return;
    const selected = new Set(this.selectedTemplateNames());
    event.checked ? selected.add(template.name) : selected.delete(template.name);
    this.selectedTemplateNames.set(selected);
  }

  onPageEvent(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onFilterChange(newFilter: FilterValueGeneric<ContainerTemplate>): void {
    this.filter.set(newFilter);
    this.pageIndex.set(0);
  }

  onClickFilter(filterKey: string): void {
    this.onFilterChange(this.filter().toggleKey(filterKey));
  }

  getFilterIconName(columnKey: string): string {
    const actionType =
      containerTemplateFilterOptions.find((o) => o.key === columnKey)?.getActionType?.(this.filter()) ?? "none";
    switch (actionType) {
      case "add":
        return "filter_alt";
      case "remove":
        return "filter_alt_off";
      case "change":
        return "screen_rotation_alt";
      default:
        return "filter_alt";
    }
  }

  openEditDialog(template: ContainerTemplate): void {
    if (!template.name) return;
    this.dialogService.openDialog({
      component: ContainerTemplateEditDialogComponent,
      data: template
    });
  }
}
