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
import { Component, computed, effect, EventEmitter, inject, input, Input, OnInit, Output, signal } from "@angular/core";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  RadiusApiPayloadMapper,
  RadiusEnrollmentData
} from "@app/mappers/token-api-payload/radius-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { RADIUS_SERVER } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";

export interface RadiusEnrollmentOptions extends TokenEnrollmentData {
  type: "radius";
  radiusServerConfiguration: string;
  radiusUser: string;
  checkPinLocally: boolean;
}

@Component({
  selector: "app-enroll-radius",
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatHint,
    MatError,
    FormField
  ],
  templateUrl: "./enroll-radius.component.html",
  styleUrl: "./enroll-radius.component.scss"
})
export class EnrollRadiusComponent implements OnInit {
  protected readonly enrollmentMapper: RadiusApiPayloadMapper = inject(RadiusApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  enrollmentData = input<RadiusEnrollmentData>();
  @Input() wizard = false;
  @Output() additionalFormFieldsChange = new EventEmitter<Record<string, unknown>>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: RadiusEnrollmentData;
      mapper: TokenApiPayloadMapper<RadiusEnrollmentData>;
    } | null
  >();
  disabled = input<boolean>(false);

  radiusUser = signal<string>("");
  radiusServerConfiguration = signal<string>("");
  checkPinLocally = signal<boolean>(false);

  radiusServerConfigurationForm = form(this.radiusServerConfiguration, (f) => {
    required(f);
    disabled(f, () => this.disabled());
  });
  radiusUserForm = form(this.radiusUser, (f) => {
    disabled(f, () => this.disabled());
  });

  radiusServerConfigurationOptions = computed(() => this.systemService.radiusServers());

  defaultRadiusServerIsSet = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return false;
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.[RADIUS_SERVER];
  });

  private radiusServerConfigInitialized = false;

  constructor() {
    effect(() => {
      if (!this.systemService.systemConfigResource.hasValue()) return;
      const id = this.systemService.systemConfigResource.value()?.result?.value?.[RADIUS_SERVER];
      if (id && !this.radiusServerConfigInitialized) {
        this.radiusServerConfiguration.set(id);
        this.radiusServerConfigInitialized = true;
      }
    });
  }

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.radiusUser.set(this.enrollmentData()?.radiusUser ?? "");
      this.radiusServerConfiguration.set(this.enrollmentData()?.radiusServerConfiguration ?? "");
      this.radiusServerConfigInitialized = true;
    }
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: RadiusEnrollmentData;
    mapper: TokenApiPayloadMapper<RadiusEnrollmentData>;
  } | null => {
    if (!this.radiusServerConfigurationForm().valid()) {
      this.radiusServerConfigurationForm().markAsTouched();
      return null;
    }

    const enrollmentData: RadiusEnrollmentOptions = {
      ...basicOptions,
      type: "radius",
      radiusUser: this.radiusUser(),
      radiusServerConfiguration: this.radiusServerConfiguration(),
      checkPinLocally: this.checkPinLocally()
    };

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  goToRadiusConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: "radius" });
  }

  onRadiusConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToRadiusConfig();
    }
  }
}
