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
import { Component, computed, inject, input } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { DetailFieldComponent } from "@components/shared/details-shared/detail-field/detail-field.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { formatTokenTimestamp } from "../token-details.component";

@Component({
  selector: "app-token-details-status",
  standalone: true,
  imports: [DetailsCardComponent, DetailFieldComponent, NgClass, MatIcon, MatIconButton],
  templateUrl: "./token-details-status.component.html",
  styleUrl: "./token-details-status.component.scss"
})
export class TokenDetailsStatusComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly tokenDetails = input.required<TokenDetails>();
  readonly isAnyEditingOrRevoked = input(false);
  readonly selfService = input(false);

  protected readonly tokenIsActive = this.tokenService.tokenIsActive;
  protected readonly tokenIsRevoked = this.tokenService.tokenIsRevoked;
  protected readonly maxfail = computed(() => this.tokenDetails().maxfail);
  protected readonly createdDisplay = computed(
    () => formatTokenTimestamp(this.tokenDetails().info?.["creation_date"]) ?? ""
  );
  protected readonly lastAuthDisplay = computed(
    () => formatTokenTimestamp(this.tokenDetails().info?.["last_auth"]) ?? ""
  );

  protected str(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
  }

  protected toggleActive(): void {
    this.tokenService
      .toggleActive(this.tokenService.tokenSerial(), this.tokenService.tokenIsActive())
      .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
  }

  protected resetFailCount(): void {
    this.tokenService
      .resetFailCount(this.tokenService.tokenSerial())
      .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
  }
}
