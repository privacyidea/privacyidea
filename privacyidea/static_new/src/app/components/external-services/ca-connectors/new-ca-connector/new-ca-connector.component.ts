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
  untracked,
  ViewChild
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { MatSelectModule } from "@angular/material/select";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import {
  CaConnector,
  CaConnectorService,
  CaConnectorServiceInterface
} from "@services/ca-connector/ca-connector.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";

interface CaConnectorFormModel {
  connectorname: string;
  type: string;
  // Local CA fields
  cacert: string;
  cakey: string;
  "openssl.cnf": string;
  templates: string;
  WorkingDir: string;
  CSRDir: string;
  CertificateDir: string;
  CRL: string;
  CRL_Validity_Period: string;
  CRL_Overlap_Period: string;
  // Microsoft CA fields
  hostname: string;
  port: string;
  http_proxy: boolean;
  use_ssl: boolean;
  ssl_ca_cert: string;
  ssl_client_cert: string;
  ssl_client_key: string;
  ssl_client_key_password: string;
  ca: string;
}

const EMPTY_CA_CONNECTOR_FORM: CaConnectorFormModel = {
  connectorname: "",
  type: "local",
  cacert: "",
  cakey: "",
  "openssl.cnf": "",
  templates: "",
  WorkingDir: "",
  CSRDir: "",
  CertificateDir: "",
  CRL: "",
  CRL_Validity_Period: "",
  CRL_Overlap_Period: "",
  hostname: "",
  port: "",
  http_proxy: false,
  use_ssl: false,
  ssl_ca_cert: "",
  ssl_client_cert: "",
  ssl_client_key: "",
  ssl_client_key_password: "",
  ca: ""
};

@Component({
  selector: "app-ca-connector-edit-dialog",
  standalone: true,
  imports: [
    FormField,
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

  isEditMode = signal(false);
  availableCas = signal<string[]>([]);
  isLoadingCas = signal(false);
  private editConnectorName: string | null = null;

  caConnectorModel = signal<CaConnectorFormModel>({ ...EMPTY_CA_CONNECTOR_FORM });

  caConnectorForm = form(this.caConnectorModel, (f) => {
    required(f.connectorname);
    pattern(f.connectorname, /^[a-zA-Z0-9._-]*$/);
    required(f.type);
    // Local CA required fields (conditional)
    required(f.cacert, { when: () => this.caConnectorModel().type === "local" });
    required(f.cakey, { when: () => this.caConnectorModel().type === "local" });
    required(f["openssl.cnf"], { when: () => this.caConnectorModel().type === "local" });
    // Microsoft CA required fields (conditional)
    required(f.hostname, { when: () => this.caConnectorModel().type === "microsoft" });
    required(f.port, { when: () => this.caConnectorModel().type === "microsoft" });
    required(f.ca, { when: () => this.caConnectorModel().type === "microsoft" && this.availableCas().length > 0 });
    disabled(f.connectorname, () => this.isEditMode());
    disabled(f.type, () => this.isEditMode());
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const connectorName = params.get("name");
      if (connectorName) {
        this.isEditMode.set(true);
        this.editConnectorName = connectorName;
        const connector = this.caConnectorService.caConnectors().find((c) => c.connectorname === connectorName);
        if (connector) {
          this.loadData(connector);
          if (connector.type === "microsoft") {
            this.loadAvailableCas();
          }
        }
      } else {
        this.isEditMode.set(false);
        this.editConnectorName = null;
        this.loadData(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const connectors = this.caConnectorService.caConnectors();
      if (this.isEditMode() && this.editConnectorName && untracked(() => !this.caConnectorForm().dirty())) {
        const found = connectors.find((c) => c.connectorname === this.editConnectorName);
        if (found) {
          this.loadData(found);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.caConnectorForm().dirty();
  }

  get canSave(): boolean {
    return this.caConnectorForm().valid();
  }

  private loadData(connector: CaConnector | null): void {
    const connectorData = connector?.data || {};
    this.caConnectorModel.set({
      connectorname: connector?.connectorname || "",
      type: connector?.type || "local",
      cacert: connectorData["cacert"] || "",
      cakey: connectorData["cakey"] || "",
      "openssl.cnf": connectorData["openssl.cnf"] || "",
      templates: connectorData["templates"] || "",
      WorkingDir: connectorData["WorkingDir"] || "",
      CSRDir: connectorData["CSRDir"] || "",
      CertificateDir: connectorData["CertificateDir"] || "",
      CRL: connectorData["CRL"] || "",
      CRL_Validity_Period: connectorData["CRL_Validity_Period"] || "",
      CRL_Overlap_Period: connectorData["CRL_Overlap_Period"] || "",
      hostname: connectorData["hostname"] || "",
      port: connectorData["port"] || "",
      http_proxy: connectorData["http_proxy"] || false,
      use_ssl: connectorData["use_ssl"] || false,
      ssl_ca_cert: connectorData["ssl_ca_cert"] || "",
      ssl_client_cert: connectorData["ssl_client_cert"] || "",
      ssl_client_key: connectorData["ssl_client_key"] || "",
      ssl_client_key_password: connectorData["ssl_client_key_password"] || "",
      ca: connectorData["ca"] || ""
    });
    this.caConnectorForm().reset();
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
    const model = this.caConnectorModel();
    const params = {
      hostname: model.hostname,
      port: model.port,
      use_ssl: model.use_ssl,
      ssl_ca_cert: model.ssl_ca_cert,
      ssl_client_cert: model.ssl_client_cert,
      ssl_client_key: model.ssl_client_key,
      ssl_client_key_password: model.ssl_client_key_password,
      http_proxy: model.http_proxy
    };

    if (params.hostname && params.port) {
      this.isLoadingCas.set(true);
      this.caConnectorService
        .getCaSpecificOptions("microsoft", params)
        .then((res) => {
          this.availableCas.set(res.available_cas || []);
          this.isLoadingCas.set(false);
        })
        .catch(() => {
          this.isLoadingCas.set(false);
        });
    }
  }

  async save(): Promise<boolean> {
    if (!this.caConnectorForm().valid()) {
      return false;
    }
    const model = this.caConnectorModel();
    const type = model.type;
    const connectorname = model.connectorname;

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
      ] as const;
      localFields.forEach((field) => {
        const value = model[field];
        if (value !== undefined && value !== "") {
          data[field] = value;
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
      ] as const;
      microsoftFields.forEach((field) => {
        const value = model[field];
        if (value !== undefined && value !== "") {
          data[field] = value;
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
    } catch {
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
