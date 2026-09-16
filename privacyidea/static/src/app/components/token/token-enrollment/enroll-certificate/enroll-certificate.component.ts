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
import { Component, computed, forwardRef, inject, input, linkedSignal, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  CertificateApiPayloadMapper,
  CertificateEnrollmentData,
  CertificateIntention
} from "@app/mappers/token-api-payload/certificate-token-api-payload.mapper";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { SelectorButtonsComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/selector-buttons/selector-buttons.component";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { CaConnector } from "@services/ca-connector/ca-connector.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface CertificateEnrollmentOptions extends TokenEnrollmentData {
  type: "certificate";
  intention: CertificateIntention;
  caConnector?: string;
  certTemplate?: string;
  pem?: string;
}

@Component({
  selector: "app-enroll-certificate",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatError,
    MatHint,
    ClearButtonComponent,
    SelectorButtonsComponent,
    MatSuffix,
    FormField
  ],
  templateUrl: "./enroll-certificate.component.html",
  styleUrl: "./enroll-certificate.component.scss",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollCertificateComponent) }]
})
export class EnrollCertificateComponent extends EnrollTokenBase<CertificateEnrollmentData> implements OnInit {
  protected readonly enrollmentMapper: CertificateApiPayloadMapper = inject(CertificateApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  enrollmentData = input<CertificateEnrollmentData>();
  disabled = input<boolean>(false);

  intention = signal<CertificateIntention>("generate");
  readonly intentionValues: CertificateIntention[] = ["generate", "uploadRequest", "uploadCert"];
  protected readonly intentionLabels = computed(() => [
    $localize`:@@token.generateRequest:Generate Request`,
    $localize`:@@token.uploadRequest:Upload Request`,
    $localize`:@@token.uploadCertificate:Upload Certificate`
  ]);
  caConnector = signal<string>("");
  certTemplate = signal<string>("");
  pem = signal<string>("");

  pemForm = form(this.pem, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.intention() === "generate");
  });

  caConnectorOptions = computed(
    () =>
      (this.systemService.caConnectorResource?.hasValue()
        ? this.systemService.caConnectorResource
            ?.value()
            ?.result?.value?.map((config: CaConnector) => config.connectorname)
        : []) || []
  );

  certTemplateOptions = linkedSignal({
    source: () => [this.systemService.caConnectors?.(), this.caConnector()] as const,
    computation: ([caConnectors, selectedConnectorName]) => {
      const selectedConnector = Object.values(caConnectors ?? {}).find(
        (c) => c.connectorname === selectedConnectorName
      );
      return selectedConnector && selectedConnector.templates ? Object.keys(selectedConnector.templates) : [];
    }
  });

  caConnectorTouched = signal<boolean>(false);

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.caConnector.set(this.enrollmentData()?.caConnector ?? "");
      this.certTemplate.set(this.enrollmentData()?.certTemplate ?? "");
    }
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<CertificateEnrollmentData> | null {
    const intention = this.intention();
    const needsPem = intention !== "generate";

    if (needsPem && !this.pemForm().valid()) {
      this.pemForm().markAsTouched();
      return null;
    }

    const needsCaConnector = intention !== "uploadCert";
    if (needsCaConnector && !this.caConnector()) {
      this.caConnectorTouched.set(true);
      return null;
    }

    const enrollmentData: CertificateEnrollmentOptions = {
      ...basicOptions,
      type: "certificate",
      intention: intention
    };
    if (needsCaConnector) {
      enrollmentData.caConnector = this.caConnector();
      enrollmentData.certTemplate = this.certTemplate();
    }
    if (needsPem) {
      enrollmentData.pem = this.pem();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  onIntentionSelected(value: string | undefined): void {
    if (value === "generate" || value === "uploadRequest" || value === "uploadCert") {
      this.intention.set(value);
    }
  }

  clearTemplateSelection(): void {
    this.certTemplate.set("");
  }
}
