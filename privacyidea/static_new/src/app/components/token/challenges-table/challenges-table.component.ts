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
import {
  Challenge,
  ChallengesService,
  ChallengesServiceInterface
} from "../../../services/token/challenges/challenges.service";
import { Component, ViewChild, WritableSignal, inject, linkedSignal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { MatPaginator, MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSort, MatSortModule, Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { KeywordFilterComponent } from "../../shared/keyword-filter/keyword-filter.component";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";

const columnKeysMap = [
  { key: "timestamp", label: "Timestamp" },
  { key: "serial", label: "Serial" },
  { key: "transaction_id", label: "Transaction ID" },
  { key: "expiration", label: "Expiration" },
  { key: "otp_received", label: "Received" }
];

@Component({
  selector: "app-challenges-table",
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    KeywordFilterComponent,
    NgClass,
    CopyButtonComponent,
    ScrollToTopDirective,
    ClearableInputComponent
  ],
  templateUrl: "./challenges-table.component.html",
  styleUrls: ["./challenges-table.component.scss"]
})
export class ChallengesTableComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly challengesService: ChallengesServiceInterface = inject(ChallengesService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  columnsKeyMap = columnKeysMap;
  displayedColumns = columnKeysMap.map((c) => c.key);
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  apiFilter = this.challengesService.apiFilter;
  advancedApiFilter = this.challengesService.advancedApiFilter;
  tokenSerial = this.tokenService.tokenSerial;
  pageSize = this.challengesService.pageSize;
  pageIndex = this.challengesService.pageIndex;
  sortby_sortdir = this.challengesService.sort;
  length = linkedSignal({
    source: this.challengesService.challengesResource.value,
    computation: (res, prev) => {
      if (res) {
        return res.result?.value?.count;
      }
      return prev?.value ?? 0;
    }
  });
  challengesDataSource: WritableSignal<MatTableDataSource<Challenge>> = linkedSignal({
    source: this.challengesService.challengesResource.value,
    computation: (challengesResource, previous) => {
      if (challengesResource) {
        return new MatTableDataSource(challengesResource.result?.value?.challenges);
      }
      return previous?.value ?? new MatTableDataSource<Challenge>([]);
    }
  });

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sortby_sortdir.set($event);
  }

  serialClicked(element: { data: { type: string }; serial: string }): void {
    if (element.data && element.data.type === "container") {
      this.contentService.containerSelected(element.serial);
    } else {
      this.contentService.tokenSelected(element.serial);
    }
  }
}
