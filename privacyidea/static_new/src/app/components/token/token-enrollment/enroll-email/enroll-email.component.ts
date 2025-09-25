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
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { EmailApiPayloadMapper } from "../../../../mappers/token-api-payload/email-token-api-payload.mapper";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

export interface EmailEnrollmentOptions extends TokenEnrollmentData {
  type: "email";
  emailAddress?: string;
  readEmailDynamically: boolean;
}

@Component({
  selector: "app-enroll-email",
  standalone: true,
  imports: [MatCheckbox, MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule, MatError],
  templateUrl: "./enroll-email.component.html",
  styleUrl: "./enroll-email.component.scss"
})
export class EnrollEmailComponent implements OnInit {
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: EmailApiPayloadMapper = inject(EmailApiPayloadMapper);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  emailAddressControl = new FormControl<string>("");
  readEmailDynamicallyControl = new FormControl<boolean>(false);
  emailForm = new FormGroup({
    emailAddress: this.emailAddressControl,
    readEmailDynamically: this.readEmailDynamicallyControl
  });

  defaultSMTPisSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.["email.identifier"];
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      emailAddress: this.emailAddressControl,
      readEmailDynamically: this.readEmailDynamicallyControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.readEmailDynamicallyControl.valueChanges.subscribe((readEmailDynamic) => {
      if (!readEmailDynamic) {
        this.emailAddressControl.setValidators([Validators.email, Validators.required]);
      } else {
        this.emailAddressControl.clearValidators();
      }
      this.emailAddressControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (!this.readEmailDynamicallyControl.value && this.emailAddressControl.invalid) {
      this.emailForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: EmailEnrollmentOptions = {
      ...basicOptions,
      type: "email",
      readEmailDynamically: !!this.readEmailDynamicallyControl.value
    };
    if (!enrollmentData.readEmailDynamically) {
      enrollmentData.emailAddress = this.emailAddressControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
