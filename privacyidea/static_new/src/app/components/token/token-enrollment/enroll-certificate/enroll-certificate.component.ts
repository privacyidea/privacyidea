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
import { Component, computed, EventEmitter, inject, input, linkedSignal, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  CertificateApiPayloadMapper,
  CertificateEnrollmentData
} from "../../../../mappers/token-api-payload/certificate-token-api-payload.mapper";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenEnrollmentData } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { toSignal } from "@angular/core/rxjs-interop";
import { ClearButtonComponent } from "../../../shared/clear-button/clear-button.component";

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
    MatError,
    ClearButtonComponent,
    MatSuffix
  ],
  templateUrl: "./enroll-certificate.component.html",
  styleUrl: "./enroll-certificate.component.scss"
})
export class EnrollCertificateComponent implements OnInit {
  protected readonly enrollmentMapper: CertificateApiPayloadMapper = inject(CertificateApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: CertificateEnrollmentData;
      mapper: CertificateApiPayloadMapper;
    } | null
  >();
  disabled = input<boolean>(false);

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

  caConnectorOptions = computed(
    () =>
      this.systemService.caConnectorResource?.value()?.result?.value.map((config: any) => config.connectorname) || []
  );

  caConnectorValueSignal = toSignal(this.caConnectorControl.valueChanges, {
    initialValue: this.caConnectorControl.value
  });

  certTemplateOptions = linkedSignal({
    source: () => [this.systemService.caConnectors?.(), this.caConnectorValueSignal()],
    computation: ([caConnectors, selectedConnectorName]) => {
      const selectedConnector = Object.values(caConnectors ?? {}).find(
        (c) => c.connectorname === selectedConnectorName
      );
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

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): {
    data: CertificateEnrollmentData;
    mapper: CertificateApiPayloadMapper;
  } | null => {
    for (const [name, control] of Object.entries(this.certificateForm.controls)) {
      if (control.invalid) {
        control.markAsTouched();
        return null;
      }
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
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  clearTemplateSelection(): void {
    this.certTemplateControl.setValue("");
  }
}
