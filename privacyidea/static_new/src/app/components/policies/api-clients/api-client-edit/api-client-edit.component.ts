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
import { Component, computed, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";

import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ApiClientIssuedKeyBannerComponent } from "@components/policies/api-clients/api-client-issued-key-banner/api-client-issued-key-banner.component";
import { ApiClientRememberedDevicesComponent } from "@components/policies/api-clients/api-client-remembered-devices/api-client-remembered-devices.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import {
  ApiClient,
  ApiClientService,
  ApiClientServiceInterface,
  ApiClientStatus
} from "@services/api-client/api-client.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { IntegrationsService, IntegrationsServiceInterface } from "@services/integrations/integrations.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";

interface ApiClientFormModel {
  display_name: string;
  client_type: string;
  status: ApiClientStatus;
}

const EMPTY_API_CLIENT_FORM: ApiClientFormModel = {
  display_name: "",
  client_type: "",
  status: "active"
};

@Component({
  selector: "app-api-client-edit",
  standalone: true,
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    ClearableInputComponent,
    ApiClientRememberedDevicesComponent,
    ApiClientIssuedKeyBannerComponent
  ],
  templateUrl: "./api-client-edit.component.html",
  styleUrl: "./api-client-edit.component.scss"
})
export class ApiClientEditComponent implements OnDestroy {
  protected readonly apiClientService: ApiClientServiceInterface = inject(ApiClientService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly integrationsService: IntegrationsServiceInterface = inject(IntegrationsService);
  protected readonly clientTypeOptions = computed(() => this.integrationsService.apiClientIntegrations());
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  isEditMode = signal(false);
  editClientId = signal<string | null>(null);

  apiClientModel = signal<ApiClientFormModel>({ ...EMPTY_API_CLIENT_FORM });

  apiClientForm = form(this.apiClientModel, (f) => {
    required(f.display_name);
    required(f.client_type);
    disabled(f.client_type, () => this.isEditMode());
  });

  constructor() {
    this.apiClientService.dismissIssuedKey();

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const id = params.get("id");
      if (id) {
        this.isEditMode.set(true);
        this.editClientId.set(id);
        const client = this.apiClientService.apiClients().find((c) => c.id === id);
        this.loadData(client ?? null);
      } else {
        this.isEditMode.set(false);
        this.editClientId.set(null);
        this.loadData(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const apiClients = this.apiClientService.apiClients();
      const id = this.editClientId();
      if (this.isEditMode() && id && untracked(() => !this.apiClientForm().dirty())) {
        const client = apiClients.find((c) => c.id === id);
        if (client) {
          this.loadData(client);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.apiClientForm().dirty();
  }

  cancelLabel(): string {
    return this.hasChanges ? $localize`Cancel` : $localize`Back`;
  }

  get canSave(): boolean {
    return this.apiClientForm().valid();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  private loadData(data: ApiClient | null): void {
    this.apiClientModel.set({
      display_name: data?.display_name || "",
      client_type: data?.client_type || "",
      status: data?.status || "active"
    });
    this.apiClientForm().reset();
  }

  async save(): Promise<boolean> {
    if (!this.apiClientForm().valid()) {
      return false;
    }
    const { display_name, client_type, status } = this.apiClientModel();

    try {
      const id = this.editClientId();
      if (this.isEditMode() && id) {
        await this.apiClientService.updateClient(id, { display_name, status });
      } else {
        await this.apiClientService.createClient(display_name, client_type);
      }
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS);
      return true;
    } catch {
      return false;
    }
  }

  rotateKey(): void {
    const id = this.editClientId();
    if (!id) return;
    const displayName = this.apiClientModel().display_name;
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Rotate API Key`,
          items: [displayName],
          itemType: "api-client",
          confirmAction: {
            label: $localize`Rotate key`,
            value: true,
            type: "destruct"
          }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.rotateClient(id, displayName).catch(() => undefined);
        }
      });
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
            this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (!success) return;
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS);
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS);
    }
  }
}
