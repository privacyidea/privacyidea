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
import { MatHint } from "@angular/material/form-field";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TokenEnrollmentDialogData, TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-token-complete-enrollment",
  imports: [DialogWrapperComponent, MatFormField, MatHint, MatInput, MatLabel, TokenEnrollmentDataComponent, FormField],
  templateUrl: "./token-complete-enrollment.component.html",
  styleUrl: "./token-complete-enrollment.component.scss"
})
export class TokenCompleteEnrollmentComponent extends AbstractDialogComponent<TokenEnrollmentDialogData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  protected readonly enrollDetails = this.data.response?.detail;
  protected readonly tokenType = this.data.response?.type ?? "hotp";
  protected readonly enrollParameters = this.data.enrollParameters ?? {};
  protected readonly twoStepEnrollment = computed(() => {
    return (
      this.enrollDetails?.["2step_output"] ||
      this.enrollDetails?.["2step_difficulty"] ||
      this.enrollDetails?.["2step_salt"]
    );
  });

  clientPart = signal<string>("");
  clientPartForm = form(this.clientPart, (f) => {
    required(f);
  });
  invalidInputSignal = computed(() => !this.clientPartForm().valid());

  readonly dialogActions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`Enroll`,
      type: "confirm",
      value: "enroll",
      disabled: this.invalidInputSignal()
    }
  ]);

  onDialogAction(value: string) {
    if (value === "enroll") {
      this.enrollToken();
    }
  }

  enrollToken() {
    this.enrollParameters.data.serial = this.enrollDetails?.serial;
    if (this.clientPart()) {
      this.enrollParameters.data["otpKey"] = this.clientPart();
      this.enrollParameters.data["otpKeyFormat"] = "base32check";
      this.enrollParameters.data["generateOnServer"] = false;
      if (this.enrollParameters.data["twoStepInit"]) {
        delete this.enrollParameters.data["twoStepInit"];
      }
    }
    this.tokenService.enrollToken(this.enrollParameters).subscribe({
      next: (response) => {
        if (response?.result?.status && response?.detail?.rollout_state !== "client_wait") {
          this.dialogRef.close(response);
        }
      }
    });
  }
}
