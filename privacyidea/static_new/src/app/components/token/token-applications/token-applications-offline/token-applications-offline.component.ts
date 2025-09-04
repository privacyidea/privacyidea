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
import { Component, computed, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
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
import { KeywordFilterComponent } from "../../../shared/keyword-filter/keyword-filter.component";

const _offlineColumnsKeyMap = [
  { key: "serial", label: "Serial" },
  { key: "count", label: "Count" },
  { key: "rounds", label: "Rounds" }
];

@Component({
  selector: "app-token-applications-offline",
  standalone: true,
  imports: [
    MatTabsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    KeywordFilterComponent,
    MatFormField,
    MatInput,
    MatLabel,
    NgClass,
    CopyButtonComponent,
    FormsModule,
    ClearableInputComponent
  ],
  templateUrl: "./token-applications-offline.component.html",
  styleUrls: ["./token-applications-offline.component.scss"]
})
export class TokenApplicationsOfflineComponent {
  protected readonly machineService: MachineServiceInterface = inject(MachineService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  columnsKeyMap = _offlineColumnsKeyMap;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = _offlineColumnsKeyMap.map((column) => column.key);

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data) {
      return new MatTableDataSource<TokenApplication>(data);
    }
    return this.tableUtilsService.emptyDataSource(this.machineService.pageSize(), _offlineColumnsKeyMap);
  });

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }
}
