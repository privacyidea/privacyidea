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
import { Component, effect, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  CaConnector,
  CaConnectorService,
  CaConnectorServiceInterface
} from "../../../../services/ca-connector/ca-connector.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MatSelectModule } from "@angular/material/select";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";

@Component({
  selector: "app-ca-connector-edit-dialog",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule
  ],
  templateUrl: "./new-ca-connector.component.html",
  styleUrl: "./new-ca-connector.component.scss"
})
export class NewCaConnectorComponent implements OnInit, OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewCaConnectorComponent>);
  protected readonly data = inject<CaConnector | null>(MAT_DIALOG_DATA);
  protected readonly caConnectorService: CaConnectorServiceInterface = inject(CaConnectorService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly pendingChangesService = inject(PendingChangesService);

  caConnectorForm!: FormGroup;
  isEditMode = false;
  availableCas = signal<string[]>([]);
  isLoadingCas = signal(false);

  constructor() {
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.onCancel();
      });
      this.dialogRef.keydownEvents().subscribe((event) => {
        if (event.key === "Escape") {
          this.onCancel();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS)) {
        this.dialogRef?.close(true);
      }
    });
  }

  get hasChanges(): boolean {
    return !this.caConnectorForm.pristine;
  }

  get canSave(): boolean {
    return this.caConnectorForm.valid;
  }

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    const connectorData = this.data?.data || {};

    this.caConnectorForm = this.formBuilder.group({
      connectorname: [this.data?.connectorname || "", [Validators.required]],
      type: [this.data?.type || "local", [Validators.required]],
      // Local CA fields
      cacert: [connectorData["cacert"] || ""],
      cakey: [connectorData["cakey"] || ""],
      "openssl.cnf": [connectorData["openssl.cnf"] || ""],
      templates: [connectorData["templates"] || ""],
      WorkingDir: [connectorData["WorkingDir"] || ""],
      CSRDir: [connectorData["CSRDir"] || ""],
      CertificateDir: [connectorData["CertificateDir"] || ""],
      CRL: [connectorData["CRL"] || ""],
      CRL_Validity_Period: [connectorData["CRL_Validity_Period"] || ""],
      CRL_Overlap_Period: [connectorData["CRL_Overlap_Period"] || ""],
      // Microsoft CA fields
      hostname: [connectorData["hostname"] || ""],
      port: [connectorData["port"] || ""],
      http_proxy: [connectorData["http_proxy"] || false],
      use_ssl: [connectorData["use_ssl"] || false],
      ssl_ca_cert: [connectorData["ssl_ca_cert"] || ""],
      ssl_client_cert: [connectorData["ssl_client_cert"] || ""],
      ssl_client_key: [connectorData["ssl_client_key"] || ""],
      ssl_client_key_password: [connectorData["ssl_client_key_password"] || ""],
      ca: [connectorData["ca"] || ""]
    });

    if (this.isEditMode) {
      this.caConnectorForm.get("connectorname")?.disable();
      this.caConnectorForm.get("type")?.disable();
      if (this.data?.type === "microsoft") {
        this.loadAvailableCas();
      }
    }

    this.updateValidators(this.caConnectorForm.get("type")?.value);

    this.caConnectorForm.get("type")?.valueChanges.subscribe((type) => {
      this.updateValidators(type);
    });
  }

  updateValidators(type: string): void {
    const localFields = ["cacert", "cakey", "openssl.cnf"];
    const microsoftFields = ["hostname", "port"];

    if (type === "local") {
      localFields.forEach((localField) => this.caConnectorForm.get(localField)?.setValidators([Validators.required]));
      microsoftFields.forEach((microsoftField) => this.caConnectorForm.get(microsoftField)?.clearValidators());
      this.caConnectorForm.get("ca")?.clearValidators();
    } else {
      microsoftFields.forEach((microsoftField) =>
        this.caConnectorForm.get(microsoftField)?.setValidators([Validators.required])
      );
      localFields.forEach((localField) => this.caConnectorForm.get(localField)?.clearValidators());
      if (this.availableCas().length > 0) {
        this.caConnectorForm.get("ca")?.setValidators([Validators.required]);
      } else {
        this.caConnectorForm.get("ca")?.clearValidators();
      }
    }

    localFields
      .concat(microsoftFields)
      .concat(["ca"])
      .forEach((f) => this.caConnectorForm.get(f)?.updateValueAndValidity());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.unregisterHasChanges();
  }

  loadAvailableCas(): void {
    const params = {
      hostname: this.caConnectorForm.get("hostname")?.value,
      port: this.caConnectorForm.get("port")?.value,
      use_ssl: this.caConnectorForm.get("use_ssl")?.value,
      ssl_ca_cert: this.caConnectorForm.get("ssl_ca_cert")?.value,
      ssl_client_cert: this.caConnectorForm.get("ssl_client_cert")?.value,
      ssl_client_key: this.caConnectorForm.get("ssl_client_key")?.value,
      ssl_client_key_password: this.caConnectorForm.get("ssl_client_key_password")?.value,
      http_proxy: this.caConnectorForm.get("http_proxy")?.value
    };

    if (params.hostname && params.port) {
      this.isLoadingCas.set(true);
      this.caConnectorService
        .getCaSpecificOptions("microsoft", params)
        .then((res) => {
          this.availableCas.set(res.available_cas || []);
          this.isLoadingCas.set(false);
          this.updateValidators(this.caConnectorForm.get("type")?.value);
        })
        .catch(() => {
          this.isLoadingCas.set(false);
        });
    }
  }

  save(): Promise<void> | void {
    if (this.caConnectorForm.valid) {
      const formValue = this.caConnectorForm.getRawValue();
      const type = formValue.type;
      const connectorname = formValue.connectorname;

      const data: Record<string, any> = { type };

      if (type === "local") {
        const localFields = [
          "cacert",
          "cakey",
          "openssl.cnf",
          "templates",
          "WorkingDir",
          "CSRDir",
          "CertificateDir",
          "CRL",
          "CRL_Validity_Period",
          "CRL_Overlap_Period"
        ];
        localFields.forEach((f) => {
          if (formValue[f] !== undefined && formValue[f] !== "") {
            data[f] = formValue[f];
          }
        });
      } else if (type === "microsoft") {
        const microsoftFields = [
          "hostname",
          "port",
          "http_proxy",
          "use_ssl",
          "ssl_ca_cert",
          "ssl_client_cert",
          "ssl_client_key",
          "ssl_client_key_password",
          "ca"
        ];
        microsoftFields.forEach((f) => {
          if (formValue[f] !== undefined && formValue[f] !== "") {
            data[f] = formValue[f];
          }
        });
      }

      const connector: CaConnector = {
        connectorname,
        type,
        data
      };

      return this.caConnectorService.postCaConnector(connector).then(() => {
        this.dialogRef.close(true);
      });
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            title: $localize`Discard changes`,
            message: $localize`You have unsaved changes. Do you want to save them before exiting?`,
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe((result) => {
          if (result === "discard") {
            this.pendingChangesService.unregisterHasChanges();
            this.closeActual();
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then(() => {
              this.pendingChangesService.unregisterHasChanges();
              this.closeActual();
            });
          }
        });
    } else {
      this.closeActual();
    }
  }

  private closeActual(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    }
  }
}
