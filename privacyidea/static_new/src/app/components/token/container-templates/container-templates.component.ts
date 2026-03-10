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
import { SelectionModel } from "@angular/cdk/collections";
import { CommonModule } from "@angular/common";
import { Component, computed, effect, inject, signal } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatTableModule } from "@angular/material/table";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../services/container/container.service";
import { ContainerTemplatesTableActionsComponent } from "./container-templates-table-actions/container-templates-table-actions.component";
import { ContainerTemplatesFilterComponent } from "./container-templates-filter/container-templates-filter.component";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import { MatSortModule } from "@angular/material/sort";
import { MatButtonModule } from "@angular/material/button";
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
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    ContainerTemplatesFilterComponent,
    ContainerTemplatesTableActionsComponent,
    MatCheckbox,
    ViewTemplateTokensComponent
  ],
  templateUrl: "./container-templates.component.html",
  styleUrl: "./container-templates.component.scss"
})
export class ContainerTemplatesComponent {
  // Services
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  // Signals
  readonly filter = signal<FilterValueGeneric<ContainerTemplate>>(
    new FilterValueGeneric({ availableFilters: containerTemplateFilterOptions })
  );

  // Selection Model
  readonly selection = new SelectionModel<ContainerTemplate>(true, [], true, (a, b) => a.name === b.name);

  // Table Configuration
  readonly columns = {
    name: { label: "Name", filterable: true },
    container_type: { label: "Container Type", filterable: true },
    default: { label: "Default", filterable: true },
    tokens: { label: "Tokens", filterable: true }
  } as const;

  // Computed Properties
  readonly filteredContainerTemplates = computed(() => {
    const templates = this.containerTemplateService.templates();
    return this.filter().hasActiveFilters ? this.filter().filterItems(templates) : templates;
  });

  // Column Handling
  get displayedColumns(): string[] {
    return ["select", ...Object.keys(this.columns)];
  }

  readonly keepOrder = () => 0;

  // Selection Logic
  isAllSelected(): boolean {
    return this.selection.selected.length === this.filteredContainerTemplates().length;
  }

  toggleAllRows(): void {
    if (this.isAllSelected()) {
      this.selection.clear();
    } else {
      this.selection.select(...this.filteredContainerTemplates());
    }
  }

  // Filtering Logic
  onClickFilter(filterKey: string): void {
    this.filter.set(this.filter().toggleKey(filterKey));
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

  // Dialog Handling
  openEditDialog(template: ContainerTemplate): void {
    this.dialogService.openDialog({
      component: ContainerTemplateEditDialogComponent,
      data: template
    });
  }
}
