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
import { Component, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../route_paths";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";

@Component({
  selector: "app-attach-token-self-service",
  imports: [MatError, MatFormField, MatFormField, MatLabel, MatInput, FormsModule, MatButton, MatIcon],
  templateUrl: "./assign-token-self-service.component.html",
  styleUrl: "./assign-token-self-service.component.scss"
})
export class AssignTokenSelfServiceComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private router = inject(Router);
  tokenSerial = this.tokenService.tokenSerial;
  selectedToken = signal("");
  setPinValue = signal("");
  repeatPinValue = signal("");

  assignUserToToken() {
    this.tokenService
      .assignUser({
        tokenSerial: this.selectedToken(),
        username: "",
        realm: "",
        pin: this.setPinValue()
      })
      .subscribe({
        next: () => {
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + this.selectedToken());
          this.tokenSerial.set(this.selectedToken());
        }
      });
  }
}
