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
import { CommonModule } from "@angular/common";
import { Component, inject, input, model, AfterViewInit, effect, computed } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { SelectionModel } from "@angular/cdk/collections";
import { ViewTemplateOptionsComponent } from "../view-template-options/view-template-options.component";

@Component({
  selector: "app-container-templates-table",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatCheckboxModule,
    ViewTemplateOptionsComponent
  ],
  templateUrl: "./container-templates-table.component.html",
  styleUrl: "./container-templates-table.component.scss"
})
export class ContainerTemplatesTableComponent {
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly selectedContainerTemplates = model.required<ContainerTemplate[]>();
  readonly filter = model.required<string>();
  readonly containerTemplates = input.required<ContainerTemplate[]>();

  dataSource = computed(() => new MatTableDataSource(this.containerTemplates()));
  selection = new SelectionModel<ContainerTemplate>(true, []);

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

  get displayedColumns() {
    return ["select", ...Object.keys(this.columns)];
  }

  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource().data.length;
    return numSelected === numRows;
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.selection.clear();
      return;
    }
    this.selection.select(...this.dataSource().data);
  }

  onClickFilter(filter: string): void {
    const currentFilter = this.filter();
    if (currentFilter.includes(`${filter}:`)) {
      this.filter.set(currentFilter.replace(`${filter}:`, "").trim());
    } else {
      this.filter.set(currentFilter ? `${currentFilter} ${filter}:` : `${filter}:`);
    }
  }
}
