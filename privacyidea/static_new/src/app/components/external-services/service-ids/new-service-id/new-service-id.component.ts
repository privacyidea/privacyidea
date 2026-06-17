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
import { Component, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ServiceId, ServiceIdService, ServiceIdServiceInterface } from "@services/service-id/service-id.service";

import { MatIconModule } from "@angular/material/icon";

import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";

interface ServiceIdFormModel {
  servicename: string;
  description: string;
}

const EMPTY_SERVICE_ID_FORM: ServiceIdFormModel = {
  servicename: "",
  description: ""
};

@Component({
  selector: "app-new-service-id",
  standalone: true,
  imports: [FormField, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule, ClearableInputComponent],
  templateUrl: "./new-service-id.component.html",
  styleUrl: "./new-service-id.component.scss"
})
export class NewServiceIdComponent implements OnDestroy {
  protected readonly serviceIdService: ServiceIdServiceInterface = inject(ServiceIdService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  isEditMode = signal(false);
  private editServiceName: string | null = null;

  serviceIdModel = signal<ServiceIdFormModel>({ ...EMPTY_SERVICE_ID_FORM });

  serviceIdForm = form(this.serviceIdModel, (f) => {
    required(f.servicename);
    pattern(f.servicename, /^[a-zA-Z0-9._-]*$/);
    disabled(f.servicename, () => this.isEditMode());
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const serviceName = params.get("name");
      if (serviceName) {
        this.isEditMode.set(true);
        this.editServiceName = serviceName;
        const serviceId = this.serviceIdService.serviceIds().find((s) => s.servicename === serviceName);
        this.loadData(serviceId ?? null);
      } else {
        this.isEditMode.set(false);
        this.editServiceName = null;
        this.loadData(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const serviceIds = this.serviceIdService.serviceIds();
      if (this.isEditMode() && this.editServiceName && untracked(() => !this.serviceIdForm().dirty())) {
        const serviceId = serviceIds.find((s) => s.servicename === this.editServiceName);
        if (serviceId) {
          this.loadData(serviceId);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.serviceIdForm().dirty();
  }

  get canSave(): boolean {
    return this.serviceIdForm().valid();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  private loadData(data: ServiceId | null): void {
    this.serviceIdModel.set({
      servicename: data?.servicename || "",
      description: data?.description || ""
    });
    this.serviceIdForm().reset();
  }

  async save(): Promise<boolean> {
    if (!this.serviceIdForm().valid()) {
      return false;
    }
    const { servicename, description } = this.serviceIdModel();
    const serviceId: ServiceId = { servicename, description };

    try {
      await this.serviceIdService.postServiceId(serviceId);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
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
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (!success) return;
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
    }
  }
}
