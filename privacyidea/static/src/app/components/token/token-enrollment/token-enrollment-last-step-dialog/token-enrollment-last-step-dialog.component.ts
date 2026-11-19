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

import { Component, computed, inject, signal, Signal } from "@angular/core";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { MessageConfirmationDialogComponent } from "@components/shared/dialog/message-confirmation-dialog/message-confirmation-dialog.component";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenEnrollmentDialogData, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { map, Observable, of } from "rxjs";

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  imports: [DialogWrapperComponent, TokenEnrollmentDataComponent, TokenEnrolledTextComponent]
})
export class TokenEnrollmentLastStepDialogComponent extends AbstractDialogComponent<TokenEnrollmentDialogData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly serial = this.data.response?.detail?.serial ?? "";
  protected readonly containerSerial = (this.data.response?.detail?.["container_serial"] ?? "") as string;
  protected readonly rollover = this.data.rollover ?? false;

  // Set while closing would lose data that exists nowhere else.
  private readonly closeConfirmation = signal("");
  // The links in the header ask the same way as Close.
  protected readonly confirmLeave = () => this.confirmClose();

  title: Signal<string> = computed(() =>
    this.rollover
      ? $localize`:@@token.tokenSuccessfullyRolled:Token Successfully Rolled Over`
      : $localize`:@@token.tokenSuccessfully:Token Successfully Enrolled`
  );

  constructor() {
    super();
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
    this.dialogRef.disableClose = true;
    this.dialogRef.backdropClick().subscribe(() => this.attemptClose());
    this.dialogRef.keydownEvents().subscribe((event) => {
      if (event.key === "Escape") {
        this.attemptClose();
      }
    });
  }

  protected attemptClose(): void {
    this.confirmClose().subscribe((confirmed) => {
      if (confirmed) {
        this.dialogRef.close();
      }
    });
  }

  private confirmClose(): Observable<boolean> {
    const message = this.closeConfirmation();
    if (!message) {
      return of(true);
    }
    return this.dialogService
      .openDialog({
        component: MessageConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.passphraseNotSaved:Passphrase Not Saved`,
          message,
          confirmAction: { label: $localize`:@@common.close:Close`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .pipe(map((confirmed) => !!confirmed));
  }

  onCloseConfirmationChange(message: string): void {
    this.closeConfirmation.set(message);
  }

  onEnrollmentResponseChange(response: EnrollmentResponse): void {
    this.data.onEnrollmentResponseChange?.(response);
  }

  onSwitchRoute() {
    this.dialogRef.close();
  }
}
