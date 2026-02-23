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
import { DatePipe } from "@angular/common";
import { Component, effect, inject, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatCard, MatCardContent } from "@angular/material/card";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { LostTokenData, TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import { AbstractDialogComponent } from "../../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";

@Component({
  selector: "app-lost-token",
  standalone: true,
  imports: [MatCard, MatCardContent, DatePipe, DialogWrapperComponent, MatIconModule, MatButton, MatIcon],
  templateUrl: "./lost-token.component.html",
  styleUrl: "./lost-token.component.scss"
})
export class LostTokenComponent extends AbstractDialogComponent<
  {
    isLost: WritableSignal<boolean>;
    tokenSerial: WritableSignal<string>;
  },
  void
> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  lostTokenData?: LostTokenData;

  constructor() {
    super();
    effect(() => {
      this.dialogRef.disableClose = this.data.isLost();
    });
  }

  lostToken(): void {
    this.tokenService.lostToken(this.data.tokenSerial()).subscribe({
      next: (response) => {
        this.data.isLost.set(true);
        this.lostTokenData = response?.result?.value;
        this.notificationService.openSnackBar("Token marked as lost: " + this.data.tokenSerial());
      }
    });
  }

  tokenSelected(tokenSerial?: string) {
    if (!tokenSerial) {
      this.notificationService.openSnackBar("No token selected, please select a token.");
      return;
    }
    this.dialogRef.close();
    this.data.tokenSerial.set(tokenSerial);
  }
}
