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
import { Component, computed, effect, inject, input, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SmsApiPayloadMapper, SmsEnrollmentData } from "@app/mappers/token-api-payload/sms-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { SMS_GATEWAY } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface SmsEnrollmentOptions extends TokenEnrollmentData {
  type: "sms";
  smsGateway: string;
  phoneNumber?: string;
  readNumberDynamically: boolean;
}

@Component({
  selector: "app-enroll-sms",
  standalone: true,
  imports: [MatCheckbox, MatFormField, MatInput, MatLabel, MatSelect, MatOption, MatHint, MatError, FormField],
  templateUrl: "./enroll-sms.component.html",
  styleUrl: "./enroll-sms.component.scss"
})
export class EnrollSmsComponent implements OnInit {
  protected readonly enrollmentMapper: SmsApiPayloadMapper = inject(SmsApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);

  enrollmentData = input<SmsEnrollmentData>();
  @Input() wizard = false;
  @Output() additionalFormFieldsChange = new EventEmitter<Record<string, unknown>>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: SmsEnrollmentData;
      mapper: TokenApiPayloadMapper<SmsEnrollmentData>;
    } | null
  >();

  disabled = input<boolean>(false);

  smsGateway = signal<string>("");
  phoneNumber = signal<string>("");
  readNumberDynamically = signal<boolean>(false);

  smsGatewayForm = form(this.smsGateway, (f) => {
    required(f);
    disabled(f, () => this.disabled());
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

  smsGatewayOptions = computed(() => {
    // Find the first right that starts with "sms_gateways="
    const right = this.authService.rights().find((r) => r.startsWith("sms_gateways="));
    const defaultId = this.systemService.systemConfigResource.hasValue()
      ? this.systemService.systemConfigResource.value()?.result?.value?.["sms.identifier"]
      : undefined;
    let gateways: string[] = [];

    if (right) {
      const gatewaysStr = right.split("=")[1];
      if (gatewaysStr) {
        gateways = gatewaysStr
          .split(" ")
          .map((gw) => gw.trim())
          .filter((gw) => gw.length > 0);
      }
    } else {
      gateways = this.smsGatewayService.smsGateways().map((gw) => gw.name);
    }

    if (defaultId && !gateways.includes(String(defaultId))) {
      gateways.push(String(defaultId));
    }

    return gateways;
  });

  defaultSMSGatewayIsSet = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return false;
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.[SMS_GATEWAY];
  });

  private smsGatewayInitialized = false;

  constructor() {
    effect(() => {
      if (!this.systemService.systemConfigResource.hasValue()) return;
      const id = this.systemService.systemConfigResource.value()?.result?.value?.[SMS_GATEWAY];
      if (id && !this.smsGatewayInitialized) {
        this.smsGateway.set(String(id));
        this.smsGatewayInitialized = true;
      }
    });
  }

  ngOnInit(): void {
    const data = this.enrollmentData();
    if (data) {
      this.smsGateway.set(data.smsGateway ?? "");
      this.readNumberDynamically.set(data.readNumberDynamically ?? false);
      this.phoneNumber.set(data.phoneNumber ?? "");
      this.smsGatewayInitialized = true;
    }
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: SmsEnrollmentData;
    mapper: TokenApiPayloadMapper<SmsEnrollmentData>;
  } | null => {
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
  };

  goToSmsConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: "sms" });
  }

  onSmsConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToSmsConfig();
    }
  }
}
