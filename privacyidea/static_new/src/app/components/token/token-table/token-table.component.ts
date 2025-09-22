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
import { Component, WritableSignal, inject, linkedSignal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSortModule, Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../services/token/token.service";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { FormsModule } from "@angular/forms";
import { KeywordFilterComponent } from "../../shared/keyword-filter/keyword-filter.component";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";

const columnKeysMap = [
  { key: "select", label: "" },
  { key: "serial", label: "Serial" },
  { key: "tokentype", label: "Type" },
  { key: "active", label: "Active" },
  { key: "description", label: "Description" },
  { key: "failcount", label: "Fail Counter" },
  { key: "rollout_state", label: "Rollout State" },
  { key: "username", label: "User" },
  { key: "user_realm", label: "User Realm" },
  { key: "realms", label: "Token Realm" },
  { key: "container_serial", label: "Container" }
];

@Component({
  selector: "app-token-table",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    KeywordFilterComponent,
    MatCheckboxModule,
    FormsModule,
    MatIconModule,
    ScrollToTopDirective,
    ClearableInputComponent,
    CopyButtonComponent
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

  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = columnKeysMap.map((column) => column.key);
  readonly apiFilter = this.tokenService.apiFilter;
  readonly advancedApiFilter = this.tokenService.advancedApiFilter;
  tokenSelection = this.tokenService.tokenSelection;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;

  tokenResource = this.tokenService.tokenResource;
  tokenFilter = this.tokenService.tokenFilter;
  pageSize = this.tokenService.pageSize;
  pageIndex = this.tokenService.pageIndex;
  sort = this.tokenService.sort;

  emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        columnKeysMap.forEach((column) => {
          emptyRow[column.key] = "";
        });
        return emptyRow;
      })
  });

  tokenDataSource: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource && tokenResource.result?.value) {
        return new MatTableDataSource(tokenResource.result?.value.tokens);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.tokenResource.value,
    computation: (tokenResource, previous) => {
      if (tokenResource && tokenResource.result?.value) {
        return tokenResource.result?.value.count;
      }
      return previous?.value ?? 0;
    }
  });

  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

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

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.tokenService.eventPageSize = event.pageSize;
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    if ($event.direction === "") {
      this.sort.set({ active: "serial", direction: "asc" });
      return;
    }
    this.sort.set($event);
  }
}
