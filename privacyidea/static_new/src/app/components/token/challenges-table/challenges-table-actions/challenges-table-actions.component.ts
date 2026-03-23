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

import { Component, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { ChallengesService, ChallengesServiceInterface } from "../../../../services/token/challenges/challenges.service";
import { NotificationService, NotificationServiceInterface } from "../../../../services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";

@Component({
  selector: "app-challenges-table-actions",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatMenuModule],
  templateUrl: "./challenges-table-actions.component.html",
  styleUrls: ["./challenges-table-actions.component.scss"]
})
export class ChallengesTableActionsComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly challengesService: ChallengesServiceInterface = inject(ChallengesService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  readonly advancedApiFilter = this.challengesService.advancedApiFilter;

  onDeleteExpiredChallenges(): void {
    this.challengesService.deleteExpiredChallenges().subscribe({
      next: () => {
        this.challengesService.challengesResource.reload();
      },
      error: (err) => {
        const message = err?.error?.result?.error?.message ?? "Failed to delete expired challenges.";
        this.notificationService.openSnackBar(message);
      }
    });
  }

  toggleFilter(filterKeyword: string): void {
    const newValue = this.tableUtilsService.toggleKeywordInFilter({
      keyword: filterKeyword,
      currentValue: this.challengesService.challengesFilter()
    });
    this.challengesService.challengesFilter.set(newValue);
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
  }

  getFilterIconName(keyword: string): string {
    const isSelected = this.challengesService.challengesFilter().hasKey(keyword);
    return isSelected ? "filter_alt_off" : "filter_alt";
  }
}
