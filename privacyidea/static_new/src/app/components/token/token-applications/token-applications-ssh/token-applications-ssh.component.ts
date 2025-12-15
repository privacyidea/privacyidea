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
import { NgClass } from "@angular/common";
import { Component, computed, ElementRef, inject, ViewChild } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFormField, MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatCell, MatCellDef, MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTabsModule } from "@angular/material/tabs";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication
} from "../../../../services/machine/machine.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatMenuModule } from "@angular/material/menu";
import { FilterValue } from "../../../../core/models/filter_value";

@Component({
  selector: "app-token-applications-ssh",
  standalone: true,
  imports: [
    MatTabsModule,
    MatCell,
    MatCellDef,
    MatFormField,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    NgClass,
    CopyButtonComponent,
    FormsModule,
    ClearableInputComponent,
    MatIconModule,
    MatButtonModule,
    MatMenuModule
  ],
  templateUrl: "./token-applications-ssh.component.html",
  styleUrls: ["./token-applications-ssh.component.scss"]
})
export class TokenApplicationsSshComponent {
  protected readonly machineService: MachineServiceInterface = inject(MachineService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "serial",
    "service_id",
    "user",
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = this.columnsKeyMap.map((column) => column.key);
  sort = this.machineService.sort;

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data) {
      return new MatTableDataSource<TokenApplication>(data);
    }
    return this.tableUtilsService.emptyDataSource(this.machineService.pageSize(), [...this.columnsKeyMap]);
  });

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }

  @ViewChild('filterInput', { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  toggleFilter(filterKeyword: string): void {
    let newValue;
    if (filterKeyword === "machineid & resolver") {
      const current = this.machineService.machineFilter();
      const hasMachineId = current.hasKey("machineid");
      const hasResolver = current.hasKey("resolver");

      if (hasMachineId && hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (!hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: newValue });
      } else if (hasMachineId && !hasResolver) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "resolver", currentValue: current });
      } else {
        newValue = this.tableUtilsService.toggleKeywordInFilter({ keyword: "machineid", currentValue: current });
      }
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.machineService.machineFilter()
      });
    }
    this.machineService.machineFilter.set(newValue);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "machineid & resolver") {
      const current = this.machineService.machineFilter();
      const selected = current.hasKey("machineid") && current.hasKey("resolver");
      return selected ? "filter_alt_off" : "filter_alt";
    }
    const isSelected = this.isFilterSelected(keyword, this.machineService.machineFilter());
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }
}
