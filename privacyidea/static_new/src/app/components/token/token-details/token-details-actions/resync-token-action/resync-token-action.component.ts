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
import { Component, inject, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { ResyncOTPTokenDialog } from "@components/token/resync-otp-token-dialog/resync-otp-token-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-resync-token-action",
  imports: [MatIcon, MatButtonModule, MatFormField, MatInput, MatLabel],
  templateUrl: "./resync-token-action.component.html",
  styleUrl: "./resync-token-action.component.scss"
})
export class ResyncTokenActionComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  fristOTPValue = signal("");
  secondOTPValue = signal("");

  async resyncOTPToken() {
    const response = await this.tokenService.resyncOTPToken(
      this.tokenService.tokenSerial(),
      this.fristOTPValue(),
      this.secondOTPValue()
    );

    console.log("Token resynced successfully response:", response);
    this.dialogService.openDialog({
      component: ResyncOTPTokenDialog,
      data: response.result?.value || false
    });

    this.tokenService.tokenDetailResource.reload();
  }
}
