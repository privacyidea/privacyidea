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
import { Component, inject, input } from "@angular/core";
import { DetailFieldComponent } from "@components/shared/details-shared/detail-field/detail-field.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { PolicyAction } from "@services/auth/policy-actions";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { tokenDetailsRightsMap } from "../token-details.constants";

@Component({
  selector: "app-token-details-counters",
  standalone: true,
  imports: [DetailsCardComponent, DetailFieldComponent],
  templateUrl: "./token-details-counters.component.html",
  styleUrl: "./token-details-counters.component.scss"
})
export class TokenDetailsCountersComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly tokenDetails = input.required<TokenDetails>();
  readonly isAnyEditingOrRevoked = input(false);

  protected readonly saveMaxfail = (value: string): void => this.saveTokenDetail("maxfail", value);
  protected readonly saveCountWindow = (value: string): void => this.saveTokenDetail("count_window", value);
  protected readonly saveSyncWindow = (value: string): void => this.saveTokenDetail("sync_window", value);

  protected str(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
  }

  protected isEditableElement(key: string): boolean {
    const rightEntry = tokenDetailsRightsMap.find((entry) => entry.key === key);
    return !!(rightEntry && this.authService.actionAllowed(rightEntry.right as PolicyAction));
  }

  private saveTokenDetail(key: string, value: unknown): void {
    this.tokenService.saveTokenDetail(this.tokenService.tokenSerial(), key, value).subscribe({
      next: () => this.tokenService.tokenDetailResource.reload()
    });
  }
}
