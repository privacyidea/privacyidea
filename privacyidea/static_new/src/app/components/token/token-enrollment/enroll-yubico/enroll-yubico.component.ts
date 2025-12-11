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
import { ErrorStateMatcher } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError } from "@angular/material/select";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { YubicoApiPayloadMapper } from "../../../../mappers/token-api-payload/yubico-token-api-payload.mapper";

export interface YubicoEnrollmentOptions extends TokenEnrollmentData {
  type: "yubico";
  yubicoIdentifier: string;
}

export class YubicoErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalidLength = control && control.value ? control.value.length !== 12 : true;
    return !!(control && invalidLength && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-yubico",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule, MatError],
  templateUrl: "./enroll-yubico.component.html",
  styleUrl: "./enroll-yubico.component.scss"
})
export class EnrollYubicoComponent implements OnInit {
  protected readonly enrollmentMapper: YubicoApiPayloadMapper = inject(YubicoApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  yubicoErrorStatematcher = new YubicoErrorStateMatcher();

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  yubikeyIdentifierControl = new FormControl<string>("", [
    Validators.required,
    Validators.minLength(12),
    Validators.maxLength(12)
  ]);

  yubicoForm = new FormGroup({
    yubikeyIdentifier: this.yubikeyIdentifierControl
  });

  yubicoIsConfigured = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(cfg?.["yubico.id"] && cfg?.["yubico.url"] && cfg?.["yubico.secret"]);
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      yubikeyIdentifier: this.yubikeyIdentifierControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    this.yubicoForm.updateValueAndValidity();
    if (this.yubicoForm.invalid) {
      this.yubicoForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: YubicoEnrollmentOptions = {
      ...basicOptions,
      type: "yubico",
      yubicoIdentifier: this.yubikeyIdentifierControl.value ?? ""
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
