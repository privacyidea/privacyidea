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
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import { Observable, of } from "rxjs";
import { FourEyesApiPayloadMapper } from "../../../../mappers/token-api-payload/4eyes-token-api-payload.mapper";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { RealmService, RealmServiceInterface } from "../../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

export interface FourEyesEnrollmentOptions extends TokenEnrollmentData {
  type: "4eyes";
  separator: string;
  requiredTokenOfRealms: { realm: string; tokens: number }[];
  userRealm?: string;
}

export class RequiredRealmsErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.length === 0 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-foureyes",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule, MatOption, MatSelect, MatError],
  templateUrl: "./enroll-foureyes.component.html",
  styleUrl: "./enroll-foureyes.component.scss"
})
export class EnrollFoureyesComponent implements OnInit {
  protected readonly enrollmentMapper: FourEyesApiPayloadMapper = inject(FourEyesApiPayloadMapper);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  separatorControl = new FormControl<string>("|", [Validators.required]);
  requiredTokensOfRealmsControl = new FormControl<string[]>([], [Validators.required, Validators.minLength(1)]);

  foureyesForm = new FormGroup({
    separator: this.separatorControl,
    requiredTokensOfRealms: this.requiredTokensOfRealmsControl
  });

  realmOptions = this.realmService.realmOptions;
  tokensByRealm: Map<string, number> = new Map();
  requiredRealmsErrorStateMatcher = new RequiredRealmsErrorStateMatcher();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      separator: this.separatorControl,
      requiredTokensOfRealms: this.requiredTokensOfRealmsControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  getTokenCount(realm: string): number {
    return this.tokensByRealm.get(realm) ?? 1;
  }

  setTokenCount(realm: string, tokens: number): void {
    if (tokens <= 0) this.tokensByRealm.delete(realm);
    else this.tokensByRealm.set(realm, tokens);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.separatorControl.invalid || this.requiredTokensOfRealmsControl.invalid) {
      this.foureyesForm.markAllAsTouched();
      return of(null);
    }
    const selected = this.requiredTokensOfRealmsControl.value ?? [];
    const requiredTokenOfRealms = selected.map((realm) => ({
      realm,
      tokens: this.getTokenCount(realm)
    }));
    const enrollmentData: FourEyesEnrollmentOptions = {
      ...basicOptions,
      type: "4eyes",
      separator: this.separatorControl.value ?? ":",
      requiredTokenOfRealms
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
