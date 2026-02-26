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
import { Component, EventEmitter, inject, Input, OnInit, Output } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  PaperApiPayloadMapper,
  PaperEnrollmentData
} from "../../../../mappers/token-api-payload/paper-token-api-payload.mapper";

export interface PaperEnrollmentOptions extends TokenEnrollmentData {
  type: "paper";
}

@Component({
  selector: "app-enroll-paper",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-paper.component.html",
  styleUrl: "./enroll-paper.component.scss"
})
export class EnrollPaperComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: PaperApiPayloadMapper = inject(PaperApiPayloadMapper);

  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: PaperEnrollmentData;
      mapper: TokenApiPayloadMapper<PaperEnrollmentData>;
    } | null
  >();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: PaperEnrollmentData;
    mapper: TokenApiPayloadMapper<PaperEnrollmentData>;
  } | null => {
    const enrollmentData: PaperEnrollmentOptions = {
      ...basicOptions,
      type: "paper"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
