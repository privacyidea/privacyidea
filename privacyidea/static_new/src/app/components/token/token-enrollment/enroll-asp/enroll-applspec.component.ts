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
import { Component, computed, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import { ServiceIdService, ServiceIdServiceInterface } from "../../../../services/service-id/service-id.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ApplspecApiPayloadMapper } from "../../../../mappers/token-api-payload/applspec-token-api-payload.mapper";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

export interface ApplspecEnrollmentOptions extends TokenEnrollmentData {
  type: "applspec";
  serviceId: string;
  generateOnServer: boolean;
  otpKey?: string;
}

export class ApplspecErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value === "" : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-applspec",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatCheckbox,
    FormsModule,
    MatOption,
    MatSelect,
    MatError
  ],
  templateUrl: "./enroll-applspec.component.html",
  styleUrl: "./enroll-applspec.component.scss"
})
export class EnrollApplspecComponent implements OnInit {
  protected readonly enrollmentMapper: ApplspecApiPayloadMapper = inject(
    ApplspecApiPayloadMapper
  );
  protected readonly serviceIdService: ServiceIdServiceInterface =
    inject(ServiceIdService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  serviceIdControl = new FormControl<string>("", [Validators.required]);
  generateOnServerControl = new FormControl<boolean>(true, [
    Validators.required
  ]);

  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });

  applspecForm = new FormGroup({
    serviceId: this.serviceIdControl,
    generateOnServer: this.generateOnServerControl,
    otpKey: this.otpKeyFormControl
  });
  serviceIdOptions = computed(
    () => this.serviceIdService.serviceIds().map((s) => s.name) || []
  );
  applspecErrorStateMatcher = new ApplspecErrorStateMatcher();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      serviceId: this.serviceIdControl,
      generateOnServer: this.generateOnServerControl,
      otpKey: this.otpKeyFormControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    if (this.authService.checkForceServerGenerateOTPKey("applspec")) {
      this.generateOnServerControl.disable({ emitEvent: false });
    } else {
      this.generateOnServerControl.valueChanges.subscribe((generate) => {
        if (!generate) {
          this.otpKeyFormControl.enable({ emitEvent: false });
          this.otpKeyFormControl.setValidators([Validators.required]);
        } else {
          this.otpKeyFormControl.disable({ emitEvent: false });
          this.otpKeyFormControl.clearValidators();
        }
        this.otpKeyFormControl.updateValueAndValidity();
      });
    }
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if ((!this.generateOnServerControl.value && this.otpKeyFormControl.invalid) ||
      this.generateOnServerControl.invalid ||
      this.serviceIdControl.invalid) {
      this.applspecForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: ApplspecEnrollmentOptions = {
      ...basicOptions,
      type: "applspec",
      serviceId: this.serviceIdControl.value ?? "",
      generateOnServer: !!this.generateOnServerControl.value
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
