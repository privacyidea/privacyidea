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
import { Component, computed, EventEmitter, inject, input, OnInit, Output, signal } from "@angular/core";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  ApplspecApiPayloadMapper,
  ApplspecEnrollmentData
} from "@app/mappers/token-api-payload/applspec-token-api-payload.mapper";
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
  imports: [MatFormField, MatInput, MatLabel, MatCheckbox, MatOption, MatSelect, MatError, FormField],
  templateUrl: "./enroll-applspec.component.html",
  styleUrl: "./enroll-applspec.component.scss"
})
export class EnrollApplspecComponent implements OnInit {
  protected readonly enrollmentMapper = inject(ApplspecApiPayloadMapper);
  protected readonly serviceIdService: ServiceIdServiceInterface = inject(ServiceIdService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  enrollmentData = input<ApplspecEnrollmentData>();
  wizard = input(false);
  @Output() additionalFormFieldsChange = new EventEmitter<Record<string, unknown>>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: ApplspecEnrollmentData;
      mapper: ApplspecApiPayloadMapper;
    } | null
  >();
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
    disabled(
      f,
      () => this.disabled() || this.generateOnServer() || this.authService.checkForceServerGenerateOTPKey("applspec")
    );
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
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: ApplspecEnrollmentData;
    mapper: ApplspecApiPayloadMapper;
  } | null => {
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
  };
}
