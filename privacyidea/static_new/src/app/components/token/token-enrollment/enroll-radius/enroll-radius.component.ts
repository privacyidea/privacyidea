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
import { Component, computed, effect, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import {
  RadiusServerService,
  RadiusServerServiceInterface
} from "../../../../services/radius-server/radius-server.service";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { RadiusApiPayloadMapper } from "../../../../mappers/token-api-payload/radius-token-api-payload.mapper";

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
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError
  ],
  templateUrl: "./enroll-radius.component.html",
  styleUrl: "./enroll-radius.component.scss"
})
export class EnrollRadiusComponent implements OnInit {
  protected readonly enrollmentMapper: RadiusApiPayloadMapper = inject(RadiusApiPayloadMapper);
  protected readonly radiusServerService: RadiusServerServiceInterface = inject(RadiusServerService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  radiusUserControl = new FormControl<string>("");
  radiusServerConfigurationControl = new FormControl<string>("", [Validators.required]);
  checkPinLocallyControl = new FormControl<boolean>(false, [Validators.required]);

  radiusForm = new FormGroup({
    radiusUser: this.radiusUserControl,
    radiusServerConfiguration: this.radiusServerConfigurationControl,
    checkPinLocally: this.checkPinLocallyControl
  });

  radiusServerConfigurationOptions = computed(
    () => this.radiusServerService.radiusServerConfigurations()?.map((config) => config.name) ?? []
  );

  defaultRadiusServerIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.["radius.identifier"];
  });

  constructor() {
    effect(() => {
      const id = this.systemService.systemConfigResource.value()?.result?.value?.["radius.identifier"];
      if (id && this.radiusServerConfigurationControl.pristine) {
        this.radiusServerConfigurationControl.setValue(id);
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      radiusUser: this.radiusUserControl,
      radiusServerConfiguration: this.radiusServerConfigurationControl,
      checkPinLocally: this.checkPinLocallyControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (
      this.radiusUserControl.invalid ||
      this.radiusServerConfigurationControl.invalid ||
      this.checkPinLocallyControl.invalid
    ) {
      this.radiusForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: RadiusEnrollmentOptions = {
      ...basicOptions,
      type: "radius",
      radiusUser: this.radiusUserControl.value ?? "",
      radiusServerConfiguration: this.radiusServerConfigurationControl.value ?? "",
      checkPinLocally: !!this.checkPinLocallyControl.value
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
