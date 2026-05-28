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
import { Component, computed, inject, input, OnInit, signal, output } from '@angular/core';
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  EmailApiPayloadMapper,
  EmailEnrollmentData
} from "@app/mappers/token-api-payload/email-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface EmailEnrollmentOptions extends TokenEnrollmentData {
  type: "email";
  emailAddress?: string;
  readEmailDynamically: boolean;
}

@Component({
  selector: "app-enroll-email",
  standalone: true,
  imports: [MatCheckbox, MatFormField, MatInput, MatLabel, MatError, FormField],
  templateUrl: "./enroll-email.component.html",
  styleUrl: "./enroll-email.component.scss"
})
export class EnrollEmailComponent implements OnInit {
  protected readonly enrollmentMapper: EmailApiPayloadMapper = inject(EmailApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private router = inject(Router);

  enrollmentData = input<EmailEnrollmentData>();

  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: EmailEnrollmentData;
      mapper: TokenApiPayloadMapper<EmailEnrollmentData>;
    } | null>();

  disabled = input<boolean>(false);

  readEmailDynamically = signal<boolean>(false);
  emailAddress = signal<string>("");

  emailAddressForm = form(this.emailAddress, (f) => {
    required(f);
    validate(f, (ctx) => {
      const value = ctx.value();
      if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return [{ kind: "invalidEmail" }];
      return [];
    });
    disabled(f, () => this.disabled() || this.readEmailDynamically());
  });

  defaultSmtpIsSet = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return false;
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.["email.identifier"];
  });

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.emailAddress.set(this.enrollmentData()?.emailAddress ?? "");
      this.readEmailDynamically.set(this.enrollmentData()?.readEmailDynamically ?? false);
    }
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: EmailEnrollmentData;
    mapper: TokenApiPayloadMapper<EmailEnrollmentData>;
  } | null => {
    if (!this.readEmailDynamically() && !this.emailAddressForm().valid()) {
      this.emailAddressForm().markAsTouched();
      return null;
    }
    const enrollmentData: EmailEnrollmentOptions = {
      ...basicOptions,
      type: "email",
      readEmailDynamically: this.readEmailDynamically()
    };
    if (!enrollmentData.readEmailDynamically) {
      enrollmentData.emailAddress = this.emailAddress();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  goToEmailConfig() {
    this.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { queryParams: { expanded: "email" } });
    return false;
  }

  onEmailConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToEmailConfig();
    }
  }
}
