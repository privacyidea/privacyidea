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
import { Component, computed, inject, input, output } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";
import { TableRow, TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface ActiveToggleToken extends TableRow {
  serial: string;
  active: boolean;
  revoked?: boolean;
  locked?: boolean;
}

@Component({
  selector: "app-token-active-toggle",
  standalone: true,
  imports: [NgClass, MatTooltip],
  templateUrl: "./token-active-toggle.component.html",
  styleUrl: "./token-active-toggle.component.scss"
})
export class TokenActiveToggleComponent {
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);

  readonly token = input.required<ActiveToggleToken>();
  readonly toggled = output<void>();

  protected readonly canToggle = computed(() => this.tableUtilsService.canToggleActive(this.token()));
  protected readonly highlightClass = computed(() => this.tableUtilsService.getClassForColumn("active", this.token()));
  protected readonly displayText = computed(() => this.tableUtilsService.getDisplayText("active", this.token()));
  protected readonly actionHint = computed(() => this.tableUtilsService.getTooltipForColumn("active", this.token()));

  protected toggle(): void {
    const token = this.token();
    this.tokenService.toggleActive(token.serial, token.active).subscribe({ next: () => this.toggled.emit() });
  }
}
