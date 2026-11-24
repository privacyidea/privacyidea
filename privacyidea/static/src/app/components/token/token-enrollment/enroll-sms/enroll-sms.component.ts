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
import { Component, computed, forwardRef, inject, input, linkedSignal, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SmsApiPayloadMapper, SmsEnrollmentData } from "@app/mappers/token-api-payload/sms-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { loadedEnrollmentPolicies } from "@components/token/token-enrollment/enrollment-policy-values";
import { SMS_GATEWAY } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { EnrollmentPolicyState, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

export interface SmsEnrollmentOptions extends TokenEnrollmentData {
  type: "sms";
  smsGateway: string;
  phoneNumber?: string;
  readNumberDynamically: boolean;
}

@Component({
  selector: "app-enroll-sms",
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    MatSelect,
    MatOption,
    MatHint,
    MatError,
    FormField
  ],
  templateUrl: "./enroll-sms.component.html",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollSmsComponent) }
  ]
})
export class EnrollSmsComponent extends EnrollTokenBase<SmsEnrollmentData> implements OnInit {
  protected readonly enrollmentMapper: SmsApiPayloadMapper = inject(SmsApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);

  enrollmentData = input<SmsEnrollmentData>();
  wizard = input<boolean>(false);

  disabled = input<boolean>(false);
  enrollmentPolicies = input<EnrollmentPolicyState>({ state: "unrestricted" });

  private readonly policyGateways = computed(
    () => loadedEnrollmentPolicies(this.enrollmentPolicies())?.sms_gateways ?? []
  );
  private readonly defaultGatewayId = computed<string | undefined>(() =>
    this.systemService.systemConfigResource.hasValue()
      ? this.systemService.systemConfigResource.value()?.result?.value?.[SMS_GATEWAY]
      : undefined
  );

  // The enrollment data (rollover, template) first, then the system default gateway if the policies allow it.
  smsGateway = linkedSignal<string>(() => {
    const data = this.enrollmentData();
    if (data) return data.smsGateway ?? "";
    const defaultId = this.defaultGatewayId();
    const allowed = this.policyGateways();
    return defaultId && (allowed.length === 0 || allowed.includes(defaultId)) ? defaultId : "";
  });
  phoneNumber = signal<string>("");
  readNumberDynamically = signal<boolean>(false);

  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  readNumberDynamicallyForm = form(this.readNumberDynamically);
  smsGatewayForm = form(this.smsGateway, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.enrollmentPolicies().state === "pending");
  });

  phoneNumberForm = form(this.phoneNumber, (f) => {
    required(f);
    validate(f, (ctx) => {
      const value = ctx.value();
      const phoneRegex = /^\+?[1-9]\d{1,14}$/;
      if (value && !phoneRegex.test(value)) return [{ kind: "invalidPhoneNumber" }];
      return [];
    });
    disabled(f, () => this.disabled() || this.readNumberDynamically());
  });

  // A gateway list from the enrollment policies is offered as it is, otherwise all gateways plus the default.
  smsGatewayOptions = computed(() => {
    const allowed = this.policyGateways();
    if (allowed.length > 0) return [...allowed];

    const gateways = this.smsGatewayService.smsGateways().map((gw) => gw.name);
    const defaultId = this.defaultGatewayId();
    if (defaultId && !gateways.includes(defaultId)) {
      gateways.push(defaultId);
    }
    return gateways;
  });

  defaultSMSGatewayIsSet = computed(() => !!this.defaultGatewayId());

  ngOnInit(): void {
    const data = this.enrollmentData();
    if (data) {
      this.readNumberDynamically.set(data.readNumberDynamically ?? false);
      this.phoneNumber.set(data.phoneNumber ?? "");
    }
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<SmsEnrollmentData> | null {
    if (!this.smsGatewayForm().valid()) {
      this.smsGatewayForm().markAsTouched();
      return null;
    }
    if (!this.readNumberDynamically() && !this.phoneNumberForm().valid()) {
      this.phoneNumberForm().markAsTouched();
      return null;
    }
    const enrollmentData: SmsEnrollmentOptions = {
      ...basicOptions,
      type: "sms",
      smsGateway: this.smsGateway(),
      readNumberDynamically: this.readNumberDynamically()
    };
    if (!this.readNumberDynamically()) {
      enrollmentData.phoneNumber = this.phoneNumber();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  goToSmsConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: "sms" });
  }

  onSmsConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToSmsConfig();
    }
  }
}
