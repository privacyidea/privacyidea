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
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { TiqrApiPayloadMapper } from "../../../../mappers/token-api-payload/tiqr-token-api-payload.mapper";

export interface TiqrEnrollmentOptions extends TokenEnrollmentData {
  type: "tiqr";
}

@Component({
  selector: "app-enroll-tiqr",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-tiqr.component.html",
  styleUrl: "./enroll-tiqr.component.scss"
})
export class EnrollTiqrComponent implements OnInit {
  protected readonly enrollmentMapper: TiqrApiPayloadMapper = inject(TiqrApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  defaultTiQRIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(cfg?.["tiqr.infoUrl"] && cfg?.["tiqr.logoUrl"] && cfg?.["tiqr.regServer"]);
  });

  tiqrForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    const enrollmentData: TiqrEnrollmentOptions = {
      ...basicOptions,
      type: "tiqr"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
