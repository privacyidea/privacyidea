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
import { MatFormField, MatLabel } from "@angular/material/select";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogAction } from "@models/dialog";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

// Asks for an OTP value to verify that the authenticator was set up, see the verify_enrollment policy.
@Component({
  selector: "app-token-verify-enrollment",
  imports: [MatFormField, MatInput, MatLabel, TokenEnrollmentDataComponent, FormField],
  templateUrl: "./token-verify-enrollment.component.html"
})
export class TokenVerifyEnrollmentComponent extends EnrollmentStep {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  readonly title = signal($localize`:@@token.verifyTokenEnrollment:Verify Token Enrollment`).asReadonly();
  readonly headerState = "verify";

  protected readonly responseDetails = this.data.response?.detail;
  protected readonly verifyMessage = this.responseDetails?.verify?.message ?? "";
  protected readonly enrollParameters = this.data.enrollParameters ?? {};
  protected readonly enrollData: TokenEnrollmentData | null = this.enrollParameters?.data;
  protected readonly tokenType: string = this.enrollData?.type ?? this.data.tokenType;
  protected readonly wizard = this.data.wizard ?? false;

  verifyOTP_value = signal<string>("");
  verifyOTPForm = form(this.verifyOTP_value, (f) => {
    required(f);
  });
  invalidInputSignal = computed(() => !this.verifyOTPForm().valid());

  override readonly actions = computed<DialogAction<string>[]>(() => [
    {
      label: $localize`:@@token.verify:Verify`,
      type: "confirm",
      value: "verify",
      disabled: this.invalidInputSignal()
    }
  ]);

  override onAction(value: string): void {
    if (value === "verify") {
      this.verifyOTP();
    }
  }

  verifyOTP() {
    const tokenSerial = this.responseDetails?.serial;
    if (!tokenSerial) {
      return;
    }
    this.tokenService.verifyToken(tokenSerial, this.verifyOTP_value()).subscribe({
      next: (response) => {
        if (response?.result?.status && response?.detail?.rollout_state === "enrolled") {
          this.flow.finishStep(response as unknown as EnrollmentResponse);
        }
      }
    });
  }

  onEnrollmentResponseChange(response: EnrollmentResponse): void {
    this.data.onEnrollmentResponseChange?.(response);
  }
}
