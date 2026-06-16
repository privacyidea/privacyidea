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
import { Component, inject, input } from "@angular/core";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-status-field",
  standalone: true,
  imports: [NgClass],
  templateUrl: "./token-status-field.component.html",
  styleUrl: "./token-status-field.component.scss"
})
export class TokenStatusFieldComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  readonly disabled = input(false);
  readonly maxfail = input(0);

  protected toggle(): void {
    this.tokenService
      .toggleActive(this.tokenService.tokenSerial(), this.tokenService.tokenIsActive())
      .subscribe({ next: () => this.tokenService.tokenDetailResource.reload() });
  }
}
