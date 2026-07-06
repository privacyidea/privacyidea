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

import { Component, computed, inject, Signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { NO_QR_CODE_TOKEN_TYPES } from "@components/token/token-enrollment/token-enrollment.constants";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TokenEnrollmentDialogData, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss",
  standalone: true,
  imports: [
    DialogWrapperComponent,
    MatIconModule,
    MatButtonModule,
    TokenEnrollmentDataComponent,
    TokenEnrolledTextComponent
  ]
})
export class TokenEnrollmentLastStepDialogComponent extends AbstractDialogComponent<TokenEnrollmentDialogData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly Object = Object;
  protected readonly serial = this.data.response?.detail?.serial ?? "";
  protected readonly containerSerial = (this.data.response?.detail?.["container_serial"] ?? "") as string;
  protected readonly qrCode =
    this.data.response?.detail.googleurl?.img ??
    this.data.response?.detail.motpurl?.img ??
    this.data.response?.detail.otpkey?.img ??
    this.data.response?.detail.tiqrenroll?.img ??
    "";
  protected readonly url =
    this.data.response?.detail?.googleurl?.value ??
    this.data.response?.detail?.motpurl?.value ??
    this.data.response?.detail?.otpkey?.value ??
    this.data.response?.detail?.tiqrenroll?.value ??
    "";
  protected readonly rollover = this.data.rollover ?? false;

  title: Signal<string> = computed(() =>
    this.rollover ? $localize`Token Successfully Rolled Over` : $localize`Token Successfully Enrolled`
  );

  constructor() {
    super();
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }

  showQRCode(): boolean {
    return !NO_QR_CODE_TOKEN_TYPES.includes(this.data.tokenType);
  }


  onSwitchRoute() {
    this.dialogRef.close();
  }
}
