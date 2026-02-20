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
import { Component, inject } from "@angular/core";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";

import { OtpValuesComponent } from "./otp-values/otp-values.component";
import { RegistrationCodeComponent } from "./registration-code/registration-code.component";
import { TiqrEnrollUrlComponent } from "./tiqr-enroll-url/tiqr-enroll-url.component";
import { OtpKeyComponent } from "./otp-key/otp-key.component";
import { ContentServiceInterface, ContentService } from "../../../../services/content/content.service";
import { TokenServiceInterface, TokenService } from "../../../../services/token/token.service";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "../token-enrollment.constants";
import { MatIconModule } from "@angular/material/icon";
import { QrCodeTextComponent } from "./qr-code-text/qr-code-text.component";
import { TokenEnrollmentLastStepDialogData } from "./token-enrollment-last-step-dialog.self-service.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { MatButtonModule } from "@angular/material/button";

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss",
  standalone: true,
  imports: [
    DialogWrapperComponent,
    OtpValuesComponent,
    RegistrationCodeComponent,
    TiqrEnrollUrlComponent,
    OtpKeyComponent,
    MatIconModule,
    QrCodeTextComponent,
    MatButtonModule
  ]
})
export class TokenEnrollmentLastStepDialogComponent extends AbstractDialogComponent<TokenEnrollmentLastStepDialogData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly Object = Object;
  protected readonly serial = this.data.response.detail?.serial ?? "";
  protected readonly containerSerial = this.data.response.detail?.["container_serial"] ?? "";
  protected readonly qrCode =
    this.data.response.detail.googleurl?.img ??
    this.data.response.detail.motpurl?.img ??
    this.data.response.detail.otpkey?.img ??
    this.data.response.detail.tiqrenroll?.img ??
    "";
  protected readonly url =
    this.data.response.detail?.googleurl?.value ??
    this.data.response.detail?.motpurl?.value ??
    this.data.response.detail?.otpkey?.value ??
    this.data.response.detail?.tiqrenroll?.value ??
    "";
  showQRCode(): boolean {
    return !NO_QR_CODE_TOKEN_TYPES.includes(this.data.tokentype?.key);
  }
  showRegenerateButton(): boolean {
    return !NO_REGENERATE_TOKEN_TYPES.includes(this.data.tokentype?.key);
  }
  regenerateButtonText(): string {
    return REGENERATE_AS_VALUES_TOKEN_TYPES.includes(this.data.tokentype?.key) ? "Values" : "QR Code";
  }
  constructor() {
    super();
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }
  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }
  regenerateQRCode() {
    this.data.serial.set(this.data.response.detail?.serial ?? null);
    this.data.enrollToken();
    this.data.serial.set(null);
    this.dialogRef.close();
  }
  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }
}
