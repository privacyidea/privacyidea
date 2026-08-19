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
import { Component, computed, effect, inject, WritableSignal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatCard, MatCardContent } from "@angular/material/card";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { LocalDateTimePipe } from "@components/shared/pipes/local-date-time.pipe";
import { DialogAction } from "@models/dialog";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { LostTokenData, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-lost-token",
  standalone: true,
  imports: [MatCard, MatCardContent, LocalDateTimePipe, DialogWrapperComponent, MatIconModule, MatButton, MatIcon],
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
  protected readonly dialogTitle = computed(() => $localize`Token ${this.data.tokenSerial()}:serial: is lost?`);
  protected closeAction: DialogAction<void> = {
    label: $localize`Close`,
    type: "cancel",
    value: undefined,
    primary: this.data.isLost()
  };

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
        this.notificationService.success($localize`Token marked as lost: ` + this.data.tokenSerial());
      }
    });
  }

  tokenSelected(tokenSerial?: string) {
    if (!tokenSerial) {
      this.notificationService.warning($localize`No token selected, please select a token.`);
      return;
    }
    this.dialogRef.close();
    this.data.tokenSerial.set(tokenSerial);
  }

  onCloseAction(): void {
    this.data.isLost.set(false);
    this.lostTokenData = undefined;
    this.dialogRef.close();
  }
}
