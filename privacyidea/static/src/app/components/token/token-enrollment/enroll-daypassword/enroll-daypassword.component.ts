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
import { Component, computed, effect, forwardRef, inject, input, linkedSignal, signal, untracked } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  DaypasswordApiPayloadMapper,
  DaypasswordEnrollmentData
} from "@app/mappers/token-api-payload/daypassword-token-api-payload.mapper";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import {
  FieldPreset,
  loadedEnrollmentPolicies,
  numericPolicyValue,
  presetOrChoice,
  samePreset
} from "@components/token/token-enrollment/enrollment-policy-values";
import { DAYPASSWORD_HASHLIB, DAYPASSWORD_TIME_STEP } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { EnrollmentPolicyState, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

export interface DaypasswordEnrollmentOptions extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength: number;
  hashAlgorithm: string;
  timeStep: string;
  generateOnServer: boolean;
}

@Component({
  selector: "app-enroll-daypassword",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, MatOption, MatSelect, MatHint, MatError, MatCheckbox, FormField],
  templateUrl: "./enroll-daypassword.component.html",
  styleUrl: "./enroll-daypassword.component.scss",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollDaypasswordComponent) }]
})
export class EnrollDaypasswordComponent extends EnrollTokenBase<DaypasswordEnrollmentData> {
  protected readonly enrollmentMapper: DaypasswordApiPayloadMapper = inject(DaypasswordApiPayloadMapper);
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

  enrollmentData = input<DaypasswordEnrollmentData>();
  wizard = input<boolean>(false);
  disabled = input<boolean>(false);
  enrollmentPolicies = input<EnrollmentPolicyState>({ state: "unrestricted" });

  private readonly policies = computed(() => loadedEnrollmentPolicies(this.enrollmentPolicies()));
  private readonly policiesPending = computed(() => this.enrollmentPolicies().state === "pending");
  private readonly hashlibPolicy = computed(() => this.policies()?.defaults.hashlib || undefined);
  private readonly otpLengthPolicy = computed(() => numericPolicyValue(this.policies()?.defaults.otplen));
  private readonly timeStepPolicy = computed(() => this.policies()?.defaults.timeStep || undefined);

  forceServerGenerate = computed(() => !!this.policies()?.force_server_generate);

  defaultHashlib = computed(() => this.systemService.systemConfig()[DAYPASSWORD_HASHLIB] || "sha1");
  defaultTimeStep = computed(() => this.systemService.systemConfig()[DAYPASSWORD_TIME_STEP] || "24h");

  // Policy value first, then the enrollment data (rollover, template), then the default.
  generateOnServer = linkedSignal(
    () => this.forceServerGenerate() || (this.enrollmentData()?.generateOnServer ?? true)
  );
  otpKey = linkedSignal(() => this.enrollmentData()?.otpKey ?? "");
  private readonly otpLengthPreset = computed<FieldPreset<number>>(
    () => {
      const policy = this.otpLengthPolicy();
      return { value: policy ?? this.enrollmentData()?.otpLength ?? 6, locked: policy !== undefined };
    },
    { equal: samePreset }
  );
  private readonly hashAlgorithmPreset = computed<FieldPreset<string>>(
    () => {
      const policy = this.hashlibPolicy();
      const data = this.enrollmentData();
      return {
        value: policy ?? (data ? (data.hashAlgorithm ?? "sha256") : this.defaultHashlib()),
        locked: policy !== undefined
      };
    },
    { equal: samePreset }
  );
  private readonly timeStepPreset = computed<FieldPreset<string>>(
    () => {
      const policy = this.timeStepPolicy();
      const data = this.enrollmentData();
      return {
        value: policy ?? (data ? (data.timeStep ?? "24h") : this.defaultTimeStep()),
        locked: policy !== undefined
      };
    },
    { equal: samePreset }
  );
  // A value the user picked is kept when the preset changes later, even one that equals the preset.
  private readonly otpLengthChosen = signal(false);
  private readonly hashAlgorithmChosen = signal(false);
  private readonly timeStepChosen = signal(false);
  otpLength = linkedSignal<FieldPreset<number>, number>({
    source: this.otpLengthPreset,
    computation: (preset, previous) => presetOrChoice(preset, previous, untracked(this.otpLengthChosen))
  });
  hashAlgorithm = linkedSignal<FieldPreset<string>, string>({
    source: this.hashAlgorithmPreset,
    computation: (preset, previous) => presetOrChoice(preset, previous, untracked(this.hashAlgorithmChosen))
  });
  timeStep = linkedSignal<FieldPreset<string>, string>({
    source: this.timeStepPreset,
    computation: (preset, previous) => presetOrChoice(preset, previous, untracked(this.timeStepChosen))
  });

  override readonly fieldsInvalid = computed(() => !this.generateOnServer() && !this.otpKeyForm().valid());

  generateOnServerDisabled = computed(() => this.disabled() || this.policiesPending() || this.forceServerGenerate());

  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  generateOnServerForm = form(this.generateOnServer, (f) => {
    disabled(f, () => this.generateOnServerDisabled());
  });

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: ERR.minLength }] : []));
    disabled(f, () => this.disabled() || this.generateOnServer() || this.forceServerGenerate());
  });

  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.policiesPending() || this.otpLengthPolicy() !== undefined);
  });

  hashAlgorithmForm = form(this.hashAlgorithm, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.policiesPending() || this.hashlibPolicy() !== undefined);
  });

  timeStepForm = form(this.timeStep, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.policiesPending() || this.timeStepPolicy() !== undefined);
  });

  constructor() {
    super();

    // A pick in the field marks it dirty, which keeps its value over a later preset.
    effect(() => {
      if (this.otpLengthForm().dirty()) this.otpLengthChosen.set(true);
      if (this.hashAlgorithmForm().dirty()) this.hashAlgorithmChosen.set(true);
      if (this.timeStepForm().dirty()) this.timeStepChosen.set(true);
    });
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<DaypasswordEnrollmentData> | null {
    if (!this.generateOnServer() && !this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: "daypassword",
      otpLength: this.otpLength(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),
      generateOnServer: this.generateOnServer()
    };
    if (!this.generateOnServer()) {
      enrollmentData.otpKey = this.otpKey();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
