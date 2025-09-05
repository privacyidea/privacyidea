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
import { Component, computed, inject, WritableSignal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";
import { TokenType } from "../../../../services/token/token.service";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "../token-enrollment.constants";

export type TokenEnrollmentLastStepDialogData = {
  tokentype: TokenType;
  response: EnrollmentResponse;
  serial: WritableSignal<string | null>;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton
  ],
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss"
})

export class TokenEnrollmentLastStepDialogComponent {
  protected readonly dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent> = inject(MatDialogRef);
  public readonly data: TokenEnrollmentLastStepDialogData = inject(MAT_DIALOG_DATA);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  protected readonly Object = Object;

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

  printOtps(): void {
    const printContents = document.getElementById("otp-values")?.innerHTML;
    if (printContents) {
      const printWindow = window.open("", "_blank", "width=800,height=600");
      if (printWindow) {
        printWindow.document.open();
        printWindow.document.write(`
          <html lang="en">
              <style>
                .otp-values {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 8px;
                }
                .otp-value {
                  min-width: 6rem;
                  border: 1px solid #e2e2e2;
                  padding: 6px;
                  border-radius: 6px;
                }
              </style>
              ${printContents}
          </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        printWindow.close();
      }
    }
  }
}
