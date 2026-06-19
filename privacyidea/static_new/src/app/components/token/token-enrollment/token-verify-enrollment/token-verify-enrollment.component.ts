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

import { Component, computed, inject, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatHint, MatLabel } from "@angular/material/select";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenEnrolledTextComponent } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TokenEnrollmentDialogData, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-verify-enrollment",
  imports: [
    DialogWrapperComponent,
    TokenEnrollmentDataComponent,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    TokenEnrolledTextComponent,
    FormField
  ],
  templateUrl: "./token-verify-enrollment.component.html",
  styleUrl: "./token-verify-enrollment.component.scss"
})
export class TokenVerifyEnrollmentComponent extends AbstractDialogComponent<TokenEnrollmentDialogData, EnrollmentResponse> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  protected readonly responseDetails = this.data.response?.detail;
  protected readonly tokenType = this.data.response?.type ?? "hotp";
  protected readonly verifyMessage = this.responseDetails?.verify?.message ?? "";
  protected readonly enrollParameters = this.data.enrollParameters ?? {};
  protected readonly enrollData: TokenEnrollmentData | null = this.enrollParameters?.data;

  verifyOTP_value = signal<string>("");
  verifyOTPForm = form(this.verifyOTP_value, (f) => {
    required(f);
  });
  invalidInputSignal = computed(() => !this.verifyOTPForm().valid());

  readonly dialogActions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`Verify`,
      type: "confirm",
      value: "verify",
      disabled: this.invalidInputSignal()
    }
  ]);

  onDialogAction(value: string): void {
    if (value === "verify") {
      this.verifyOTP();
    }
  }

  verifyOTP() {
    const verifyData: TokenEnrollmentData = {
      serial: this.responseDetails?.serial,
      type: this.tokenService.selectedTokenType().key,
      verify: this.verifyOTP_value()
    };
    this.tokenService.verifyToken(verifyData).subscribe({
      next: (response) => {
        if (response?.result?.status && response?.detail?.rollout_state === "enrolled") {
          this.dialogRef.close(response as unknown as EnrollmentResponse);
        }
      }
    });
  }

  onSwitchRoute() {
    this.dialogRef.close();
  }
}
