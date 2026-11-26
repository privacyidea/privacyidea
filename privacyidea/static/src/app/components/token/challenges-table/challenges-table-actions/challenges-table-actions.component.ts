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

import { Component, computed, inject, viewChild } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { MatMenu, MatMenuModule } from "@angular/material/menu";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { ChallengesService, ChallengesServiceInterface } from "@services/token/challenges/challenges.service";
import { TableAction, TableActionsComponent } from "../../../shared/table-actions/table-actions.component";
import { TableActionsHost } from "../../../shared/table-actions/table-actions-host";

@Component({
  selector: "app-challenges-table-actions",
  standalone: true,
  imports: [MatIconModule, MatMenuModule, TableActionsComponent],
  templateUrl: "./challenges-table-actions.component.html"
})
export class ChallengesTableActionsComponent extends TableActionsHost {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly challengesService: ChallengesServiceInterface = inject(ChallengesService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  readonly advancedApiFilterKeys = this.challengesService.advancedApiFilterKeys;
  private readonly advancedFilterMenu = viewChild.required<MatMenu>("advancedFilterMenu");

  protected readonly actions = computed<TableAction[]>(() => [
    {
      id: "delete-expired",
      label: $localize`:@@token.deleteExpired:Delete Expired`,
      tone: "delete-primary",
      width: "l",
      icon: "delete_sweep",
      pinned: true,
      run: () => this.onDeleteExpiredChallenges()
    },
    {
      id: "more-filter",
      label: $localize`:@@common.moreFilter:More Filter`,
      tooltip: $localize`:@@common.moreFilter:More Filter`,
      tone: "primary",
      width: "l",
      fontIcon: "ms--filter-list",
      pinned: true,
      visible: this.advancedApiFilterKeys.length > 0,
      submenu: this.advancedFilterMenu()
    }
  ]);

  onDeleteExpiredChallenges(): void {
    this.challengesService.deleteExpiredChallenges().subscribe({
      next: () => {
        this.challengesService.challengesResource.reload();
      },
      error: (err) => {
        const message =
          err?.error?.result?.error?.message ??
          $localize`:@@token.failedDeleteExpired:Failed to delete expired challenges.`;
        this.notificationService.error(message);
      }
    });
  }

  toggleFilter(filterKeyword: string): void {
    this.challengesService.updateFilter((current) =>
      this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: current
      })
    );
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
  }

  getFilterIconName(keyword: string): string {
    const isSelected = this.challengesService.activeFilter().hasKey(keyword);
    return isSelected ? "filter_alt_off" : "filter_alt";
  }
}
