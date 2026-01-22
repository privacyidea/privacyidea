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

import { Component, computed, effect, inject, OnDestroy, OnInit, signal, untracked } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  SmsGateway,
  SmsGatewayService,
  SmsGatewayServiceInterface,
  SmsProvider
} from "../../../../services/sms-gateway/sms-gateway.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { toSignal } from "@angular/core/rxjs-interop";

@Component({
  selector: "app-sms-edit-dialog",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatOptionModule
  ],
  templateUrl: "./new-sms-gateway.component.html",
  styleUrl: "./new-sms-gateway.component.scss"
})
export class NewSmsGatewayComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewSmsGatewayComponent>);
  protected readonly data = inject<SmsGateway | null>(MAT_DIALOG_DATA);
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly pendingChangesService = inject(PendingChangesService);

  smsForm: FormGroup = this.fb.group({
    name: [this.data?.name || "", [Validators.required]],
    providermodule: [this.data?.providermodule || "", [Validators.required]],
    description: [this.data?.description || ""]
  });
  parametersForm: FormGroup = this.fb.group({});
  isEditMode = false;

  customOptions: Record<string, string> = {};
  customHeaders: Record<string, string> = {};

  newOptionKey = "";
  newOptionValue = "";
  newHeaderKey = "";
  newHeaderValue = "";

  providers = computed(() => this.smsGatewayService.smsProvidersResource.value()?.result?.value);
  selectedProvider = signal<SmsProvider | undefined>(undefined);
  providermoduleSignal = toSignal(this.smsForm.get("providermodule")!.valueChanges, { initialValue: this.data?.providermodule || "" });

  constructor() {
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.onCancel();
      });
      this.dialogRef.keydownEvents().subscribe(event => {
        if (event.key === "Escape") {
          this.onCancel();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS)) {
        this.dialogRef?.close(true);
      }
    });

    effect(() => {
      const providers = this.providers();
      const module = this.providermoduleSignal();
      if (providers && module) {
        untracked(() => this.onProviderChange(module));
      }
    });
  }

  get hasChanges(): boolean {
    return !this.smsForm.pristine || !this.parametersForm?.pristine || Object.keys(this.customOptions).length > 0 || Object.keys(this.customHeaders).length > 0;
  }

  get customOptionKeys() {
    return Object.keys(this.customOptions);
  }

  get customHeaderKeys() {
    return Object.keys(this.customHeaders);
  }

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    if (this.isEditMode) {
      this.smsForm.get("name")?.disable();
    }
  }

  onProviderChange(module: string): void {
    const providers = this.providers();
    if (!providers) return;

    const provider = providers[module];
    this.selectedProvider.set(provider);

    const group: any = {};
    if (provider && provider.parameters) {
      Object.entries(provider.parameters).forEach(([name, param]) => {
        const validators = [];
        if (param.required) {
          validators.push(Validators.required);
        }

        let initialValue = "";
        if (this.isEditMode && this.data?.options) {
          initialValue = this.data.options[name] || "";
        }

        group[name] = [initialValue, validators];
      });
    }
    this.parametersForm = this.fb.group(group);

    if (this.isEditMode && this.data) {
      this.customOptions = {};
      const paramKeys = provider ? Object.keys(provider.parameters) : [];
      Object.entries(this.data.options || {}).forEach(([key, value]) => {
        if (!paramKeys.includes(key)) {
          this.customOptions[key] = value;
        }
      });
      this.customHeaders = { ...(this.data.headers || {}) };
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.unregisterHasChanges();
  }

  save(): void {
    if (this.smsForm.valid && this.parametersForm.valid) {
      const formValue = this.smsForm.getRawValue();
      const paramValue = this.parametersForm.getRawValue();

      const payload: any = {
        name: formValue.name,
        description: formValue.description,
        module: formValue.providermodule
      };

      if (this.isEditMode) {
        payload.id = this.data?.id;
      }

      Object.entries(paramValue).forEach(([key, value]) => {
        payload[`option.${key}`] = value;
      });

      Object.entries(this.customOptions).forEach(([key, value]) => {
        payload[`option.${key}`] = value;
      });

      Object.entries(this.customHeaders).forEach(([key, value]) => {
        payload[`header.${key}`] = value;
      });

      this.smsGatewayService.postSmsGateway(payload).then(() => {
        this.dialogRef.close(true);
      });
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialog.open(ConfirmationDialogComponent, {
        data: {
          title: $localize`Discard changes`,
          action: "discard",
          type: "sms-gateway"
        }
      }).afterClosed().subscribe(result => {
        if (result) {
          this.closeActual();
        }
      });
    } else {
      this.closeActual();
    }
  }

  addOption(): void {
    if (this.newOptionKey) {
      this.customOptions[this.newOptionKey] = this.newOptionValue;
      this.newOptionKey = "";
      this.newOptionValue = "";
    }
  }

  deleteOption(key: string): void {
    delete this.customOptions[key];
  }

  addHeader(): void {
    if (this.newHeaderKey) {
      this.customHeaders[this.newHeaderKey] = this.newHeaderValue;
      this.newHeaderKey = "";
      this.newHeaderValue = "";
    }
  }

  deleteHeader(key: string): void {
    delete this.customHeaders[key];
  }

  private closeActual(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    }
  }
}
