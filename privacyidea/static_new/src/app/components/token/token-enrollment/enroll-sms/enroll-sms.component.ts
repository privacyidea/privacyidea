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
import { Component, computed, effect, EventEmitter, inject, input, Input, OnInit, Output, signal } from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  SmsApiPayloadMapper,
  SmsEnrollmentData
} from "../../../../mappers/token-api-payload/sms-token-api-payload.mapper";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "../../../../services/sms-gateway/sms-gateway.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

export interface SmsEnrollmentOptions extends TokenEnrollmentData {
  type: "sms";
  smsGateway: string;
  phoneNumber?: string;
  readNumberDynamically: boolean;
}

const phoneNumberValidator: ValidatorFn = (control: AbstractControl) => {
  const value = control.value;
  const parent = control.parent;

  if (parent) {
    const isDynamic = parent.get("readNumberDynamically")?.value;
    if (isDynamic) {
      return null;
    }
  }

  if (!value) {
    return { required: true };
  }

  const phoneRegex = /^\+?[1-9]\d{1,14}$/;
  return phoneRegex.test(value) ? null : { invalidPhoneNumber: true };
};

@Component({
  selector: "app-enroll-sms",
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatSelect,
    MatOption,
    MatHint,
    MatError
  ],
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
  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: SmsEnrollmentData;
      mapper: TokenApiPayloadMapper<SmsEnrollmentData>;
    } | null
  >();

  smsGatewayControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  phoneNumberControl = new FormControl<string>("", [phoneNumberValidator]);
  readNumberDynamicallyControl = new FormControl<boolean>(false, {
    nonNullable: true,
    validators: [Validators.required]
  });

  smsForm = new FormGroup({
    smsGateway: this.smsGatewayControl,
    phoneNumber: this.phoneNumberControl,
    readNumberDynamically: this.readNumberDynamicallyControl
  });

  smsGatewayOptions = computed(() => {
    // Find the first right that starts with "sms_gateways="
    const right = this.authService.rights().find((r) => r.startsWith("sms_gateways="));
    const defaultId = this.systemService.systemConfigResource.value()?.result?.value?.["sms.identifier"];
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

    if (defaultId && !gateways.includes(defaultId)) {
      gateways.push(defaultId);
    }

    return gateways;
  });

  defaultSMSGatewayIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.["sms.identifier"];
  });

  disabled = input<boolean>(false);

  constructor() {
    effect(() => (this.disabled() ? this.smsForm.disable({ emitEvent: false }) : this._enableFormControls()));
    effect(() => {
      const id = this.systemService.systemConfigResource.value()?.result?.value?.["sms.identifier"];
      if (id && this.smsGatewayControl.pristine) {
        this.smsGatewayControl.setValue(id);
      }
    });
    effect(() => {
      if (this.enrollmentData()) {
        this._setInitialFormValues();
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      smsGateway: this.smsGatewayControl,
      phoneNumber: this.phoneNumberControl,
      readNumberDynamically: this.readNumberDynamicallyControl
    });
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this.readNumberDynamicallyControl.valueChanges.subscribe(() => {
      this.phoneNumberControl.updateValueAndValidity();
    });
    this._applyPolicies();
  }

  private _setInitialFormValues() {
    const data = this.enrollmentData();
    if (data) {
      this.smsGatewayControl.setValue(this.enrollmentData()?.smsGateway ?? "", { emitEvent: false });
      this.readNumberDynamicallyControl.setValue(this.enrollmentData()?.readNumberDynamically ?? false, {
        emitEvent: false
      });
      this.phoneNumberControl.setValue(this.enrollmentData()?.phoneNumber ?? "", { emitEvent: false });

      this._updatePhoneNumberControlState(this.readNumberDynamicallyControl.value);
    }
  }

  private _applyPolicies() {
    this.readNumberDynamicallyControl.valueChanges.subscribe((dynamic) => {
      this._updatePhoneNumberControlState(dynamic);
    });
    this._updatePhoneNumberControlState(this.readNumberDynamicallyControl.value);
  }

  private _updatePhoneNumberControlState(dynamic: boolean) {
    if (!dynamic) {
      this.phoneNumberControl.enable({ emitEvent: false });
      this.phoneNumberControl.setValidators([Validators.required]);
    } else {
      this.phoneNumberControl.disable({ emitEvent: false });
      this.phoneNumberControl.clearValidators();
    }
    this.phoneNumberControl.updateValueAndValidity();
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: SmsEnrollmentData;
    mapper: TokenApiPayloadMapper<SmsEnrollmentData>;
  } | null => {
    const enrollmentData: SmsEnrollmentOptions = {
      ...basicOptions,
      type: "sms",
      smsGateway: this.smsGatewayControl.value ?? "",
      readNumberDynamically: !!this.readNumberDynamicallyControl.value
    };

    if (!enrollmentData.readNumberDynamically) {
      enrollmentData.phoneNumber = this.phoneNumberControl.value ?? "";
    }

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  private _enableFormControls(): void {
    this.smsForm.enable({ emitEvent: false });
    this._updatePhoneNumberControlState(this.readNumberDynamicallyControl.value);
  }

  goToSmsConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: 'sms' });
  }

  onSmsConfigKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.goToSmsConfig();
    }
  }
}
