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
import { Component, EventEmitter, inject, linkedSignal, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import {
  CaConnectorService,
  CaConnectorServiceInterface
} from "../../../../services/ca-connector/ca-connector.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { CertificateApiPayloadMapper } from "../../../../mappers/token-api-payload/certificate-token-api-payload.mapper";

export interface CertificateEnrollmentOptions extends TokenEnrollmentData {
  type: "certificate";
  caConnector: string;
  certTemplate: string;
  pem?: string;
}

export class CaConnectorErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value === "" : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-certificate",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatButtonToggleGroup,
    MatButtonToggle,
    FormsModule,
    MatOption,
    MatSelect,
    MatError
  ],
  templateUrl: "./enroll-certificate.component.html",
  styleUrl: "./enroll-certificate.component.scss"
})
export class EnrollCertificateComponent implements OnInit {
  protected readonly enrollmentMapper: CertificateApiPayloadMapper = inject(CertificateApiPayloadMapper);
  protected readonly caConnectorService: CaConnectorServiceInterface = inject(CaConnectorService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  caConnectorControl = new FormControl<string>("", [Validators.required]);
  certTemplateControl = new FormControl<string>("");
  pemControl = new FormControl<string>("");
  intentionToggleControl = new FormControl<"generate" | "uploadRequest" | "uploadCert">("generate", [
    Validators.required
  ]);

  certificateForm = new FormGroup({
    caConnector: this.caConnectorControl,
    certTemplate: this.certTemplateControl,
    pem: this.pemControl,
    intentionToggle: this.intentionToggleControl
  });

  caConnectorOptions = linkedSignal({
    source: this.caConnectorService.caConnectors,
    computation: (caConnectors) =>
      typeof caConnectors === "object"
        ? Object.values(caConnectors).map((caConnector) => caConnector.connectorname)
        : []
  });

  certTemplateOptions = linkedSignal({
    source: this.caConnectorService.caConnectors,
    computation: (caConnectors) => {
      const selectedConnectorName = this.caConnectorControl.value;
      const selectedConnector = Object.values(caConnectors).find((c) => c.connectorname === selectedConnectorName);
      return selectedConnector && selectedConnector.templates ? Object.keys(selectedConnector.templates) : [];
    }
  });

  caConnectorErrorStateMatcher = new CaConnectorErrorStateMatcher();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      caConnector: this.caConnectorControl,
      certTemplate: this.certTemplateControl,
      pem: this.pemControl,
      intentionToggle: this.intentionToggleControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.intentionToggleControl.valueChanges.subscribe((intention) => {
      if (intention === "uploadRequest" || intention === "uploadCert") {
        this.pemControl.setValidators([Validators.required]);
        this.caConnectorControl.clearValidators();
        this.certTemplateControl.clearValidators();
      } else {
        this.pemControl.clearValidators();
        this.caConnectorControl.setValidators([Validators.required]);
        this.certTemplateControl.setValidators([Validators.required]);
      }
      this.pemControl.updateValueAndValidity();
      this.caConnectorControl.updateValueAndValidity();
      this.certTemplateControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.certificateForm.invalid) {
      this.certificateForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: CertificateEnrollmentOptions = {
      ...basicOptions,
      type: "certificate",
      caConnector: this.caConnectorControl.value ?? "",
      certTemplate: this.certTemplateControl.value ?? ""
    };
    if (this.intentionToggleControl.value === "uploadRequest" || this.intentionToggleControl.value === "uploadCert") {
      enrollmentData.pem = this.pemControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
