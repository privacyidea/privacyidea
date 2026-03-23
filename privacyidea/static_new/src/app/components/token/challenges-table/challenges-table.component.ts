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
import { Component, inject, linkedSignal, WritableSignal, ViewChild, ElementRef } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule, MatPaginator, PageEvent } from "@angular/material/paginator";
import { MatTableModule, MatTableDataSource } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterValue } from "src/app/core/models/filter_value/filter_value";
import { ContentServiceInterface, ContentService } from "src/app/services/content/content.service";
import { NotificationServiceInterface, NotificationService } from "src/app/services/notification/notification.service";
import { TableUtilsServiceInterface, TableUtilsService } from "src/app/services/table-utils/table-utils.service";
import {
  ChallengesServiceInterface,
  ChallengesService,
  Challenge
} from "src/app/services/token/challenges/challenges.service";
import { TokenServiceInterface, TokenService } from "src/app/services/token/token.service";

import { ChallengesTableActionsComponent } from "./challenges-table-actions/challenges-table-actions.component";

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
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    NgClass,
    CopyButtonComponent,
    ScrollToTopDirective,
    ClearableInputComponent,
    ChallengesTableActionsComponent
  ],
  templateUrl: "./challenges-table.component.html",
  styleUrls: ["./challenges-table.component.scss"]
})
export class ChallengesTableComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly challengesService: ChallengesServiceInterface = inject(ChallengesService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  columnsKeyMap = columnKeysMap;
  displayedColumns = columnKeysMap.map((c) => c.key);
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  apiFilter = this.challengesService.apiFilter;
  advancedApiFilter = this.challengesService.advancedApiFilter;
  tokenSerial = this.tokenService.tokenSerial;
  pageSize = this.challengesService.pageSize;
  pageIndex = this.challengesService.pageIndex;
  sort = this.challengesService.sort;
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

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  toggleFilter(filterKeyword: string): void {
    const newValue = this.tableUtilsService.toggleKeywordInFilter({
      keyword: filterKeyword,
      currentValue: this.challengesService.challengesFilter()
    });
    this.challengesService.challengesFilter.set(newValue);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    const isSelected = this.isFilterSelected(keyword, this.challengesService.challengesFilter());
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  serialClicked(element: { data: { type: string }; serial: string }): void {
    if (element.data && element.data.type === "container") {
      this.contentService.containerSelected(element.serial);
    } else {
      this.contentService.tokenSelected(element.serial);
    }
  }
}
