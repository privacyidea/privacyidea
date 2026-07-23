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

import { NgClass } from "@angular/common";
import { Component, computed, ElementRef, inject, ViewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatFormField, MatLabel } from "@angular/material/select";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTabsModule } from "@angular/material/tabs";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatHint } from "@angular/material/form-field";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { TokenApplicationsActionsComponent } from "@components/token/token-applications/token-applications-actions/token-applications-actions.component";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { MachineService, MachineServiceInterface, TokenApplication } from "@services/machine/machine.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { filterColumnHint, filterInputHint, filterKeywordHint } from "@utils/filter-hint.utils";

@Component({
  selector: "app-token-applications-offline",
  standalone: true,
  imports: [
    MatTabsModule,
    MatTableModule,
    MatPaginatorModule,
    MatFormField,
    MatInput,
    MatLabel,
    NgClass,
    CopyableComponent,
    ClearableInputComponent,
    MatIconModule,
    MatButtonModule,
    TokenApplicationsActionsComponent,
    MatTooltipModule,
    MatHint
  ],
  templateUrl: "./token-applications-offline.component.html",
  styleUrls: ["./token-applications-offline.component.scss"]
})
export class TokenApplicationsOfflineComponent {
  protected readonly machineService: MachineServiceInterface = inject(MachineService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly columnsKeyMap = this.tableUtilsService.pickColumns("serial", "count", "rounds");
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = this.columnsKeyMap.map((column) => column.key);
  sort = this.machineService.sort;
  readonly filterHint = filterInputHint({ mayBeCaseSensitive: true });
  readonly filterKeywordHintText = filterKeywordHint(this.machineService.offlineApiFilter);

  dataSource = computed(() => {
    const data = this.machineService.tokenApplications();
    if (data) {
      return new MatTableDataSource<TokenApplication>(data);
    }
    return this.tableUtilsService.emptyDataSource(this.machineService.pageSize(), [...this.columnsKeyMap]);
  });
  @ViewChild("filterInput", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }

  filterColumnTooltip(label: string, keyword: string): string {
    return filterColumnHint(label, { exactMatch: keyword !== "serial", isBoolean: false });
  }

  getFilterIconName(keyword: string): string {
    return this.machineService.getFilterIconName(keyword);
  }

  onKeywordClick(filterKeyword: string): void {
    this.machineService.toggleFilter(filterKeyword);
    this.machineService.focusActiveInput();
  }
}
