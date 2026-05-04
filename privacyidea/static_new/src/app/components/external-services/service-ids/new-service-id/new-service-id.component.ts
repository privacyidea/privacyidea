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
import { Component, effect, inject, OnDestroy } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  ServiceId,
  ServiceIdService,
  ServiceIdServiceInterface
} from "../../../../services/service-id/service-id.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ROUTE_PATHS } from "../../../../route_paths";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-new-service-id",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    ClearableInputComponent
  ],
  templateUrl: "./new-service-id.component.html",
  styleUrl: "./new-service-id.component.scss"
})
export class NewServiceIdComponent implements OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  protected readonly serviceIdService: ServiceIdServiceInterface = inject(ServiceIdService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  serviceIdForm!: FormGroup;
  isEditMode = false;
  private editServiceName: string | null = null;

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const serviceName = params.get("name");
      if (serviceName) {
        this.isEditMode = true;
        this.editServiceName = serviceName;
        const serviceId = this.serviceIdService.serviceIds().find((s) => s.servicename === serviceName);
        this.initForm(serviceId ?? null);
      } else {
        this.isEditMode = false;
        this.editServiceName = null;
        this.initForm(null);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const serviceIds = this.serviceIdService.serviceIds();
      if (this.isEditMode && this.editServiceName && this.serviceIdForm?.pristine) {
        const serviceId = serviceIds.find((s) => s.servicename === this.editServiceName);
        if (serviceId) {
          this.initForm(serviceId);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return !this.serviceIdForm.pristine;
  }

  get canSave(): boolean {
    return this.serviceIdForm.valid;
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  private initForm(data: ServiceId | null): void {
    this.serviceIdForm = this.formBuilder.group({
      servicename: [data?.servicename || "", [Validators.required, Validators.pattern(/^[a-zA-Z0-9._-]*$/)]],
      description: [data?.description || ""]
    });

    if (this.isEditMode) {
      this.serviceIdForm.get("servicename")?.disable();
    }
  }

  async save(): Promise<boolean> {
    if (this.serviceIdForm.invalid) {
      return false;
    }
    const serviceId: ServiceId = {
      ...this.serviceIdForm.getRawValue()
    };

    try {
      await this.serviceIdService.postServiceId(serviceId);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
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
