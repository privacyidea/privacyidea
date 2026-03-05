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
import { Component, computed, effect, inject, input, model, signal } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../services/container/container.service";
import { ContainerTemplatesTableActionsComponent } from "./container-templates-table-actions/container-templates-table-actions.component";
import { ContainerTemplatesFilterComponent } from "./container-templates-filter/container-templates-filter.component";
import { ViewTemplateOptionsComponent } from "./view-template-options/view-template-options.component";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import { ContainerTemplateEditComponent } from "./dialogs/container-template-edit/container-template-edit.component";

const containerTemplateFilterOptions: FilterOption<ContainerTemplate>[] = [
  new FilterOption<ContainerTemplate>({
    key: "name",
    label: $localize`Name`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("scope");
      return !val || item.name.toLowerCase().includes(val.toLowerCase());
    }
  }),
  new FilterOption<ContainerTemplate>({
    key: "container_type",
    label: $localize`Container Type`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("type");
      return !val || item.container_type.toLowerCase().includes(val.toLowerCase());
    }
  }),
  new FilterOption<ContainerTemplate>({
    key: "default",
    label: $localize`Default`,
    matches: (item, filter) => {
      const val = filter.getValueOfKey("default");
      return !val || (val === "true" ? item.default === true : item.default === false);
    }
  })
];

@Component({
  selector: "app-container-templates",
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    MatTableModule,
    ContainerTemplatesFilterComponent,
    ContainerTemplatesTableActionsComponent,
    MatCheckbox,
    ViewTemplateOptionsComponent
  ],
  templateUrl: "./container-templates.component.html",
  styleUrl: "./container-templates.component.scss"
})
export class ContainerTemplatesComponent {
  readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly containerTemplates = computed(() => {
    const templates = this.containerTemplateService.templates();
    const filter = this.filter();
    return templates;
  });
  readonly filter = signal<FilterValueGeneric<ContainerTemplate>>(
    new FilterValueGeneric({ availableFilters: containerTemplateFilterOptions })
  );

  readonly selectedContainerTemplates = signal<ContainerTemplate[]>([]);

  readonly dataSource = computed(() => {
    const templates = this.containerTemplates();
    console.log("Templates in dataSource computation:", templates);
    return new MatTableDataSource(templates);
  });
  readonly selection = new SelectionModel<ContainerTemplate>(true, []);

  readonly columns = {
    name: { label: "Name", sortable: true, filterable: true },
    container_type: { label: "Container Type", sortable: false, filterable: true },
    default: { label: "Default", sortable: false, filterable: true },
    options: { label: "Options", sortable: false, filterable: true }
  } as const;

  readonly keepOrder = () => 0;

  constructor() {
    effect(() => {
      this.selectedContainerTemplates.set(this.selection.selected);
    });
  }

  get displayedColumns(): string[] {
    return ["select", ...Object.keys(this.columns)];
  }

  isAllSelected(): boolean {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource().data.length;
    return numSelected === numRows;
  }

  toggleAllRows(): void {
    if (this.isAllSelected()) {
      this.selection.clear();
      return;
    }
    this.selection.select(...this.dataSource().data);
  }

  onClickFilter(filterKey: string): void {
    const newFilter = this.filter().toggleKey(filterKey);
    this.filter.set(newFilter);
  }

  openEditDialog(template: ContainerTemplate): void {
    this.dialogService.openDialog({
      component: ContainerTemplateEditComponent
    });
  }
}
