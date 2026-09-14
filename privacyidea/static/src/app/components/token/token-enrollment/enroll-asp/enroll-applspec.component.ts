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
import { Component, computed, forwardRef, inject, input, OnInit, signal } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  ApplspecApiPayloadMapper,
  ApplspecEnrollmentData
} from "@app/mappers/token-api-payload/applspec-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ServiceIdService, ServiceIdServiceInterface } from "@services/service-id/service-id.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface ApplspecEnrollmentOptions extends TokenEnrollmentData {
  type: "applspec";
  serviceId: string;
  generateOnServer: boolean;
  otpKey?: string;
}

@Component({
  selector: "app-enroll-applspec",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatOption,
    MatSelect,
    MatError,
    FormField
  ],
  templateUrl: "./enroll-applspec.component.html",
  styleUrl: "./enroll-applspec.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollApplspecComponent) }
  ]
})
export class EnrollApplspecComponent extends EnrollTokenBase<ApplspecEnrollmentData> implements OnInit {
  protected readonly enrollmentMapper: ApplspecApiPayloadMapper = inject(ApplspecApiPayloadMapper);
  protected readonly serviceIdService: ServiceIdServiceInterface = inject(ServiceIdService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  enrollmentData = input<ApplspecEnrollmentData>();
  wizard = input<boolean>(false);
  disabled = input<boolean>(false);

  serviceId = signal<string>("");
  generateOnServer = signal<boolean>(true);
  otpKey = signal<string>("");

  serviceIdForm = form(this.serviceId, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });
  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.generateOnServer() || this.authService.checkForceServerGenerateOTPKey("applspec"));
  });

  serviceIdOptions = computed(() => this.serviceIdService.serviceIds().map((s) => s.servicename) || []);

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.serviceId.set(this.enrollmentData()!.serviceId ?? "");
      this.generateOnServer.set(this.enrollmentData()!.generateOnServer ?? true);
      if (!this.enrollmentData()!.generateOnServer) {
        this.otpKey.set(this.enrollmentData()!.otpKey ?? "");
      }
    }
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<ApplspecEnrollmentData> | null {
    if (!this.serviceIdForm().valid()) {
      this.serviceIdForm().markAsTouched();
      return null;
    }
    if (!this.generateOnServer() && !this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }

    const enrollmentData: ApplspecEnrollmentOptions = {
      ...basicOptions,
      type: "applspec",
      serviceId: this.serviceId(),
      generateOnServer: this.generateOnServer()
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKey();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
