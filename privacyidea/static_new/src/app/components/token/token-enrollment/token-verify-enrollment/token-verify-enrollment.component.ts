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
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail, TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { TokenEnrollmentDataComponent } from "../token-enrollment-data/token-enrollment-data.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatButton } from "@angular/material/button";
import { MatFormField, MatHint } from "@angular/material/form-field";

@Component({
  selector: "app-token-verify-enrollment",
  imports: [
    DialogWrapperComponent,
    TokenEnrollmentDataComponent,
    FormsModule,
    MatButton,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    ReactiveFormsModule
  ],
  templateUrl: "./token-verify-enrollment.component.html",
  styleUrl: "./token-verify-enrollment.component.scss"
})
export class TokenVerifyEnrollmentComponent extends AbstractDialogComponent<EnrollmentResponse> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly enrollDetails = this.data.detail ?? {};
  protected readonly tokenType = this.data.type ?? "hotp";
  protected readonly verifyMessage = this.enrollDetails.verify?.message ?? "";

  verifyOTPControl = new FormControl("", { nonNullable: true });

  constructor() {
    super();
    console.log("Enrollment details:", this.enrollDetails);
  }

  verifyOTP() {
    const verifyData: TokenEnrollmentData = {
      serial: this.enrollDetails.serial,
      type: this.tokenService.selectedTokenType().key,
      verify: this.verifyOTPControl.value
    };
    this.tokenService.verifyToken(verifyData).subscribe({
      next: (response) => {
        if (response?.result?.status && response?.detail?.rollout_state === "enrolled") {
          this.dialogRef.close(response);
        }
      }
    });
  }
}
