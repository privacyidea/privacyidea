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
import { Component, EventEmitter, inject, Output } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError } from "@angular/material/select";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { SshkeyApiPayloadMapper } from "../../../../mappers/token-api-payload/sshkey-token-api-payload.mapper";

export interface SshkeyEnrollmentOptions extends TokenEnrollmentData {
  type: "sshkey";
  sshPublicKey: string;
}

@Component({
  selector: "app-enroll-sshkey",
  imports: [FormsModule, MatFormField, MatInput, MatLabel, MatError, ReactiveFormsModule],
  templateUrl: "./enroll-sshkey.component.html"
})
export class EnrollSshkeyComponent {
  protected readonly enrollmentMapper: SshkeyApiPayloadMapper = inject(SshkeyApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  sshPublicKeyFormControl = new FormControl<string>("", [Validators.required, EnrollSshkeyComponent.sshKeyValidator]);

  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();

  static sshKeyValidator(control: AbstractControl): { [key: string]: boolean } | null {
    const sshKeyPattern =
      /^ssh-(rsa|dss|ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) [A-Za-z0-9+/=]+( .+)?$/;
    if (control.value && !sshKeyPattern.test(control.value)) {
      return { invalidSshKey: true };
    }
    return null;
  }

  ngOnInit() {
    this.additionalFormFieldsChange.emit({
      sshPublicKey: this.sshPublicKeyFormControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.sshPublicKeyFormControl.invalid) {
      this.sshPublicKeyFormControl.markAsTouched();
      return of(null);
    }

    const sshPublicKey = this.sshPublicKeyFormControl?.value?.trim() ?? "";
    const parts = sshPublicKey.split(" ");
    const sshKeyDescriptionPart = parts.length >= 3 ? parts[2] : "";
    const fullDescription = basicOptions.description
      ? `${basicOptions.description}\n\n${sshKeyDescriptionPart}`.trim()
      : sshKeyDescriptionPart;

    const enrollmentData: SshkeyEnrollmentOptions = {
      ...basicOptions,
      type: "sshkey",
      sshPublicKey: sshPublicKey,
      description: fullDescription
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
