import { Component, computed, effect, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import { SmsGatewayService, SmsGatewayServiceInterface } from "../../../../services/sms-gateway/sms-gateway.service";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { SmsApiPayloadMapper } from "../../../../mappers/token-api-payload/sms-token-api-payload.mapper";

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
  protected readonly enrollmentMapper: SmsApiPayloadMapper =
    inject(SmsApiPayloadMapper);
  protected readonly smsGatewayService: SmsGatewayServiceInterface =
    inject(SmsGatewayService);
  protected readonly systemService: SystemServiceInterface =
    inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  smsGatewayControl = new FormControl<string>("", [Validators.required]);
  phoneNumberControl = new FormControl<string>("");
  readNumberDynamicallyControl = new FormControl<boolean>(false, [
    Validators.required
  ]);

  smsForm = new FormGroup({
    smsGateway: this.smsGatewayControl,
    phoneNumber: this.phoneNumberControl,
    readNumberDynamically: this.readNumberDynamicallyControl
  });
  smsGatewayOptions = computed(() => {
    const raw =
      this.smsGatewayService.smsGatewayResource.value()?.result?.value;
    return raw && Array.isArray(raw) ? raw.map((gw) => gw.name) : [];
  });

  defaultSMSGatewayIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.["sms.identifier"];
  });

  constructor() {
    effect(() => {
      const id =
        this.systemService.systemConfigResource.value()?.result?.value?.[
          "sms.identifier"
          ];
      if (id && this.smsGatewayControl.pristine) {
        this.smsGatewayControl.setValue(id);
      }
    });
  }

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      smsGateway: this.smsGatewayControl,
      phoneNumber: this.phoneNumberControl,
      readNumberDynamically: this.readNumberDynamicallyControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.readNumberDynamicallyControl.valueChanges.subscribe((dynamic) => {
      if (!dynamic) {
        this.phoneNumberControl.setValidators([Validators.required]);
      } else {
        this.phoneNumberControl.clearValidators();
      }
      this.phoneNumberControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if (this.smsGatewayControl.invalid ||
      (!this.readNumberDynamicallyControl.value && this.phoneNumberControl.invalid)) {
      this.smsForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: SmsEnrollmentOptions = {
      ...basicOptions,
      type: "sms",
      smsGateway: this.smsGatewayControl.value ?? "",
      readNumberDynamically: !!this.readNumberDynamicallyControl.value
    };

    if (!enrollmentData.readNumberDynamically) {
      enrollmentData.phoneNumber = this.phoneNumberControl.value ?? "";
    }

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
