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
import {
  AfterViewInit,
  Component,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  Renderer2,
  signal,
  ViewChild
} from "@angular/core";
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
import { MatIconModule } from "@angular/material/icon";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { ActivatedRoute, Router } from "@angular/router";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MatSelectModule } from "@angular/material/select";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ScrollToTopDirective } from "../../../shared/directives/app-scroll-to-top.directive";

@Component({
  selector: "app-ca-connector-edit-dialog",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    ClearableInputComponent,
    ScrollToTopDirective
  ],
  templateUrl: "./new-ca-connector.component.html",
  styleUrl: "./new-ca-connector.component.scss"
})
export class NewCaConnectorComponent implements AfterViewInit, OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  protected readonly caConnectorService: CaConnectorServiceInterface = inject(CaConnectorService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly renderer: Renderer2 = inject(Renderer2);

  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;
  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;

  private observer!: IntersectionObserver;

  caConnectorForm!: FormGroup;
  isEditMode = false;
  availableCas = signal<string[]>([]);
  isLoadingCas = signal(false);
  private editConnectorName: string | null = null;

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const connectorName = params.get("name");
      if (connectorName) {
        this.isEditMode = true;
        this.editConnectorName = connectorName;
        const connector = this.caConnectorService.caConnectors().find((c) => c.connectorname === connectorName);
        if (connector) {
          this.initForm(connector);
        }
      } else {
        this.isEditMode = false;
        this.editConnectorName = null;
        this.initForm(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const connectors = this.caConnectorService.caConnectors();
      if (this.isEditMode && this.editConnectorName && this.caConnectorForm?.pristine) {
        const found = connectors.find((c) => c.connectorname === this.editConnectorName);
        if (found) {
          this.initForm(found);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return !this.caConnectorForm.pristine;
  }

  get canSave(): boolean {
    return this.caConnectorForm.valid;
  }

  private initForm(connector: CaConnector | null): void {
    const connectorData = connector?.data || {};

    this.caConnectorForm = this.formBuilder.group({
      connectorname: [connector?.connectorname || "", [Validators.required]],
      type: [connector?.type || "local", [Validators.required]],
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
      if (connector?.type === "microsoft") {
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
    this.pendingChangesService.clearAllRegistrations();
    this.observer?.disconnect();
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;

    const options: IntersectionObserverInit = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;
      const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
      if (shouldFloat) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
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

  async save(): Promise<boolean> {
    if (this.caConnectorForm.invalid) {
      return false;
    }
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

    try {
      await this.caConnectorService.postCaConnector(connector);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
      return true;
    } catch (error) {
      return false;
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe((result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (success) {
                this.pendingChangesService.clearAllRegistrations();
                this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
              }
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    }
  }
}
