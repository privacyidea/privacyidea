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
import { Component, forwardRef, inject, input, signal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  SshkeyApiPayloadMapper,
  SshkeyEnrollmentData
} from "@app/mappers/token-api-payload/sshkey-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";

const SSH_KEY_PATTERN =
  /^ssh-(rsa|dss|ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) [A-Za-z0-9+/=]+( .+)?$/;

export interface SshkeyEnrollmentOptions extends TokenEnrollmentData {
  type: "sshkey";
  sshPublicKey: string;
}

@Component({
  selector: "app-enroll-sshkey",
  imports: [FormField, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: "./enroll-sshkey.component.html",
  styleUrl: "./enroll-sshkey.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollSshkeyComponent) }
  ]
})
export class EnrollSshkeyComponent extends EnrollTokenBase<SshkeyEnrollmentData> {
  disabled = input<boolean>(false);
  protected readonly enrollmentMapper: SshkeyApiPayloadMapper = inject(SshkeyApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  sshPublicKey = signal<string>("");
  sshPublicKeyForm = form(this.sshPublicKey, (f) => {
    required(f);
    validate(f, (ctx) => {
      const value = ctx.value();
      if (value && !SSH_KEY_PATTERN.test(value)) {
        return [{ kind: "invalidSshKey" }];
      }
      return [];
    });
    disabled(f, () => this.disabled());
  });

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<SshkeyEnrollmentData> | null {
    if (!this.sshPublicKeyForm().valid()) {
      this.sshPublicKeyForm().markAsTouched();
      return null;
    }

    const sshPublicKey = this.sshPublicKey().trim();
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
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
