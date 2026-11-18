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
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { TokenEnrollmentDialogData, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  imports: [DialogWrapperComponent, TokenEnrollmentDataComponent, TokenEnrolledTextComponent]
})
export class TokenEnrollmentLastStepDialogComponent extends AbstractDialogComponent<TokenEnrollmentDialogData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly serial = this.data.response?.detail?.serial ?? "";
  protected readonly containerSerial = (this.data.response?.detail?.["container_serial"] ?? "") as string;
  protected readonly rollover = this.data.rollover ?? false;

  /**
   * Names the enrollment data that is shown only once and still has to be saved. Leaving the page
   * loses it, so the links and the actions that navigate away wait for it. Closing keeps it: the
   * reopen button shows this dialog again.
   */
  protected readonly closeBlockedReason = signal("");

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
  }

  onCloseBlockedReasonChange(reason: string): void {
    this.closeBlockedReason.set(reason);
  }

  onEnrollmentResponseChange(response: EnrollmentResponse): void {
    this.data.onEnrollmentResponseChange?.(response);
  }

  onSwitchRoute() {
    // Following a link closes the dialog and leaves the page, which would lose the enrollment data
    // that is shown only once.
    if (this.closeBlockedReason()) {
      return;
    }
    this.dialogRef.close();
  }
}
