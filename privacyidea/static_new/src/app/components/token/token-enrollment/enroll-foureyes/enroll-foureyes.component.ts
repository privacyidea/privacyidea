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
import { Component, effect, forwardRef, inject, input, signal } from "@angular/core";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import {
  FourEyesApiPayloadMapper,
  FourEyesEnrollmentData
} from "@app/mappers/token-api-payload/4eyes-token-api-payload.mapper";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface FourEyesEnrollmentOptions extends TokenEnrollmentData {
  type: "4eyes";
  separator: string;
  requiredTokenOfRealms: { realm: string; tokens: number }[];
  userRealm?: string;
}

@Component({
  selector: "app-enroll-foureyes",
  standalone: true,
  imports: [FormField, MatFormField, MatInput, MatLabel, MatOption, MatSelect, MatError],
  templateUrl: "./enroll-foureyes.component.html",
  styleUrl: "./enroll-foureyes.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollFoureyesComponent) }
  ]
})
export class EnrollFoureyesComponent extends EnrollTokenBase<FourEyesEnrollmentData> {
  protected readonly enrollmentMapper: FourEyesApiPayloadMapper = inject(FourEyesApiPayloadMapper);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  enrollmentData = input<FourEyesEnrollmentData>();
  disabled = input<boolean>(false);

  separator = signal<string>("|");
  requiredTokensOfRealms = signal<string[]>([]);
  tokensByRealm: Map<string, number> = new Map();

  separatorForm = form(this.separator, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });

  realmOptions = this.realmService.realmOptions;

  constructor() {
    super();

    effect(() => {
      if (this.enrollmentData()) {
        this.separator.set(this.enrollmentData()?.separator ?? "|");
        if (this.enrollmentData()?.requiredTokenOfRealms) {
          this.requiredTokensOfRealms.set(this.enrollmentData()!.requiredTokenOfRealms.map((r) => r.realm));
          for (const rd of this.enrollmentData()!.requiredTokenOfRealms) {
            this.tokensByRealm.set(rd.realm, rd.tokens);
          }
        }
      }
    });
  }

  getTokenCount(realm: string): number {
    return this.tokensByRealm.get(realm) ?? 1;
  }

  setTokenCount(realm: string, tokens: number): void {
    if (tokens <= 0) {
      this.tokensByRealm.delete(realm);
    } else {
      this.tokensByRealm.set(realm, tokens);
    }
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<FourEyesEnrollmentData> | null {
    if (!this.separatorForm().valid()) {
      this.separatorForm().markAsTouched();
      return null;
    }
    if (this.requiredTokensOfRealms().length === 0) {
      return null;
    }

    const requiredTokenOfRealms = this.requiredTokensOfRealms().map((realm) => ({
      realm,
      tokens: this.getTokenCount(realm)
    }));

    const enrollmentData: FourEyesEnrollmentOptions = {
      ...basicOptions,
      type: "4eyes",
      separator: this.separator(),
      requiredTokenOfRealms
    };

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
