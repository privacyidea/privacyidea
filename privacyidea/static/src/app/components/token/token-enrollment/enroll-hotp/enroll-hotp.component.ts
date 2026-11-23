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
import { Component, computed, forwardRef, inject, input, linkedSignal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { HotpApiPayloadMapper, HotpEnrollmentData } from "@app/mappers/token-api-payload/hotp-token-api-payload.mapper";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import {
  loadedEnrollmentPolicies,
  numericPolicyValue,
  twoStepMode
} from "@components/token/token-enrollment/enrollment-policy-values";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { EnrollmentPolicyState, TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface HotpEnrollmentOptions extends TokenEnrollmentData {
  type: "hotp";
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string;
  hashAlgorithm: string;
  twoStepInit?: boolean;
}

@Component({
  selector: "app-enroll-hotp",
  imports: [MatCheckbox, MatSelect, MatOption, MatLabel, MatFormField, MatInput, MatHint, MatError, FormField],
  templateUrl: "./enroll-hotp.component.html",
  standalone: true,
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollHotpComponent) }]
})
export class EnrollHotpComponent extends EnrollTokenBase<HotpEnrollmentData> {
  protected readonly enrollmentMapper: HotpApiPayloadMapper = inject(HotpApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    { value: "sha1", viewValue: "SHA1" },
    { value: "sha256", viewValue: "SHA256" },
    { value: "sha512", viewValue: "SHA512" }
  ];

  enrollmentData = input<HotpEnrollmentData | null>();
  wizard = input<boolean>(false);
  disabled = input<boolean>(false);
  enrollmentPolicies = input<EnrollmentPolicyState>({ state: "unrestricted" });

  private readonly policies = computed(() => loadedEnrollmentPolicies(this.enrollmentPolicies()));
  private readonly policiesPending = computed(() => this.enrollmentPolicies().state === "pending");
  private readonly hashlibPolicy = computed(() => this.policies()?.defaults.hashlib || undefined);
  private readonly otpLengthPolicy = computed(() => numericPolicyValue(this.policies()?.defaults.otplen));

  twoStep = computed(() => twoStepMode(this.policies()));
  forceServerGenerate = computed(() => !!this.policies()?.force_server_generate);

  // Policy value first, then the enrollment data (rollover, template), then the default.
  twoStepEnabled = linkedSignal(() => this.twoStep() === "force" || !!this.enrollmentData()?.twoStepInit);
  generateOnServer = linkedSignal(
    () => this.forceServerGenerate() || this.twoStepEnabled() || (this.enrollmentData()?.generateOnServer ?? true)
  );
  otpKey = linkedSignal(() => this.enrollmentData()?.otpKey ?? "");
  otpLength = linkedSignal(() => this.otpLengthPolicy() ?? this.enrollmentData()?.otpLength ?? 6);
  hashAlgorithm = linkedSignal(() => this.hashlibPolicy() ?? this.enrollmentData()?.hashAlgorithm ?? "sha1");

  twoStepDisabled = computed(() => this.disabled() || this.policiesPending() || this.twoStep() === "force");
  override readonly fieldsInvalid = computed(() => !this.generateOnServer() && !this.otpKeyForm().valid());

  generateOnServerDisabled = computed(
    () =>
      this.disabled() ||
      this.policiesPending() ||
      this.twoStep() === "force" ||
      (this.twoStep() === "allow" && this.twoStepEnabled()) ||
      this.forceServerGenerate()
  );

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: "minlength" }] : []));
    disabled(f, () => this.disabled() || this.generateOnServer() || this.twoStepEnabled());
  });

  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.policiesPending() || this.otpLengthPolicy() !== undefined);
  });

  hashAlgorithmForm = form(this.hashAlgorithm, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.policiesPending() || this.hashlibPolicy() !== undefined);
  });

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<HotpEnrollmentData> | null {
    const enrollmentData: HotpEnrollmentOptions = {
      ...basicOptions,
      type: "hotp",
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      hashAlgorithm: this.hashAlgorithm(),
      twoStepInit: this.twoStepEnabled()
    };

    if (!this.generateOnServer()) {
      if (!this.otpKeyForm().valid()) {
        this.otpKeyForm().markAsTouched();
        return null;
      }
      enrollmentData.otpKey = this.otpKey().trim();
    }

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
