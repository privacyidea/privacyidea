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

import { CommonModule } from "@angular/common";
import { Component, OnDestroy, computed, effect, inject, input, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormField, disabled, form, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatOptionModule } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  SmsGateway,
  SmsGatewayPayload,
  SmsGatewayService,
  SmsGatewayServiceInterface,
  SmsProvider,
  SmsProviderParameter
} from "@services/sms-gateway/sms-gateway.service";

interface KeyValueRow {
  key: string;
  value: string;
  secret: boolean;
}

interface SmsFormModel {
  name: string;
  providermodule: string;
  description: string;
}

const EMPTY_SMS_FORM: SmsFormModel = {
  name: "",
  providermodule: "",
  description: ""
};

@Component({
  selector: "app-sms-edit-dialog",
  standalone: true,
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatOptionModule,
    MatTableModule,
    MatCheckboxModule,
    ClearableInputComponent,
    CommonModule,
    StickyHeaderDirective
  ],
  templateUrl: "./new-sms-gateway.component.html",
  styleUrl: "./new-sms-gateway.component.scss"
})
export class NewSmsGatewayComponent implements OnDestroy {
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  protected data: SmsGateway | null = null;
  private gatewayName: string | null = null;

  isEditMode = signal(false);

  smsModel = signal<SmsFormModel>({ ...EMPTY_SMS_FORM });
  private initialSmsModel = signal<SmsFormModel>({ ...EMPTY_SMS_FORM });
  private initialParametersModel = signal<Record<string, string>>({});
  private initialCustomOptions: Record<string, string> = {};
  private initialCustomHeaders: Record<string, string> = {};

  smsForm = form(this.smsModel, (f) => {
    required(f.name);
    pattern(f.name, /^[a-zA-Z0-9._-]*$/);
    required(f.providermodule);
    disabled(f.name, () => this.isEditMode());
  });

  /** Parameters for the selected provider: signal<Record<string, string>> */
  parametersModel = signal<Record<string, string>>({});
  /** Tracks which parameter keys are required */
  private requiredParams = signal<Set<string>>(new Set());
  /** Whether all required params are filled */
  parametersValid = computed(() => {
    const model = this.parametersModel();
    for (const key of this.requiredParams()) {
      if (!model[key]) return false;
    }
    return true;
  });
  /** Whether the parameters have been touched/dirtied */
  parametersDirty = signal(false);

  updateParameter(key: string, value: string): void {
    this.parametersModel.update((m) => ({ ...m, [key]: value }));
    this.parametersDirty.set(true);
  }

  clearParameter(key: string): void {
    this.parametersModel.update((m) => ({ ...m, [key]: "" }));
    this.parametersDirty.set(true);
  }

  customOptions: Record<string, string> = {};
  customHeaders: Record<string, string> = {};
  optionSecrets: Record<string, boolean> = {};
  headerSecrets: Record<string, boolean> = {};
  private initialOptionSecrets: Record<string, boolean> = {};
  private initialHeaderSecrets: Record<string, boolean> = {};

  newOptionKey = signal("");
  newOptionValue = signal("");
  newOptionSecret = signal(false);
  newHeaderKey = signal("");
  newHeaderValue = signal("");
  newHeaderSecret = signal(false);

  optionDisplayedColumns: string[] = ["key", "value", "secret", "actions"];
  optionFooterColumns: string[] = ["footerKey", "footerValue", "footerSecret", "footerActions"];

  headerDisplayedColumns: string[] = ["key", "value", "secret", "actions"];
  headerFooterColumns: string[] = ["footerKey", "footerValue", "footerSecret", "footerActions"];

  providers = computed<Record<string, SmsProvider>>(() => {
    if (!this.smsGatewayService.smsProvidersResource.hasValue()) return {};
    return this.smsGatewayService.smsProvidersResource.value()?.result?.value ?? {};
  });

  selectedProvider = signal<SmsProvider | undefined>(undefined);

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      this.gatewayName = params.get("name");
      this.isEditMode.set(!!this.gatewayName);

      // Load data for editing existing gateway
      if (this.isEditMode() && this.gatewayName) {
        const gateways = this.smsGatewayService.smsGateways();
        const gatewayData = gateways.find((g) => g.name === this.gatewayName);
        if (gatewayData) {
          this.data = gatewayData;
        }
      }
      this.initForm();
    });

    effect(() => {
      const providers = this.providers();
      const module = this.smsModel().providermodule;
      if (providers && module) {
        untracked(() => this.onProviderChange(module));
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const gateways = this.smsGatewayService.smsGateways();
      if (this.isEditMode() && this.gatewayName && untracked(() => !this.smsForm().dirty())) {
        const found = gateways.find((g) => g.name === this.gatewayName);
        if (found) {
          this.data = found;
          this.initForm();
        }
      }
    });
  }

  private initForm(): void {
    const initialModel = {
      name: this.data?.name || "",
      providermodule: this.data?.providermodule || "",
      description: this.data?.description || ""
    };
    this.smsModel.set(initialModel);
    this.initialSmsModel.set({ ...initialModel });
    this.initialParametersModel.set({});
    this.initialCustomOptions = {};
    this.initialCustomHeaders = {};
    this.initialOptionSecrets = {};
    this.initialHeaderSecrets = {};
    this.newOptionKey.set("");
    this.newOptionValue.set("");
    this.newOptionSecret.set(false);
    this.newHeaderKey.set("");
    this.newHeaderValue.set("");
    this.newHeaderSecret.set(false);
    this.smsForm().reset();
  }

  get optionRows(): KeyValueRow[] {
    return Object.entries(this.customOptions)
      .map(([key, value]) => ({ key, value, secret: !!this.optionSecrets[key] }))
      .sort((a, b) => a.key.localeCompare(b.key));
  }

  get headerRows(): KeyValueRow[] {
    return Object.entries(this.customHeaders)
      .map(([key, value]) => ({ key, value, secret: !!this.headerSecrets[key] }))
      .sort((a, b) => a.key.localeCompare(b.key));
  }

  get hasChanges(): boolean {
    return (
      this.parametersDirty() ||
      !this.recordsEqual(this.smsModel(), this.initialSmsModel()) ||
      !this.recordsEqual(this.parametersModel(), this.initialParametersModel()) ||
      !this.recordsEqual(this.customOptions, this.initialCustomOptions) ||
      !this.recordsEqual(this.customHeaders, this.initialCustomHeaders) ||
      !this.recordsEqual(this.optionSecrets, this.initialOptionSecrets) ||
      !this.recordsEqual(this.headerSecrets, this.initialHeaderSecrets) ||
      !!this.newOptionKey() ||
      !!this.newOptionValue() ||
      this.newOptionSecret() ||
      !!this.newHeaderKey() ||
      !!this.newHeaderValue() ||
      this.newHeaderSecret()
    );
  }

  private recordsEqual<T extends object>(a: T, b: T): boolean {
    const aKeys = Object.keys(a) as (keyof T)[];
    const bKeys = Object.keys(b) as (keyof T)[];
    if (aKeys.length !== bKeys.length) {
      return false;
    }
    return aKeys.every((key) => a[key] === b[key]);
  }

  providerEntries(): { key: string; value: SmsProvider }[] {
    const providersObj = this.providers() ?? {};
    return Object.entries(providersObj).map(([key, value]) => ({ key, value }));
  }

  parameterEntries(): { key: string; value: SmsProviderParameter }[] {
    const paramsObj = this.selectedProvider()?.parameters ?? {};
    return Object.entries(paramsObj).map(([key, value]) => ({ key, value }));
  }

  get canSave(): boolean {
    return this.smsForm().valid() && this.parametersValid();
  }

  onProviderChange(module: string): void {
    const providers = this.providers();
    if (!providers) return;

    const provider = providers[module];
    this.selectedProvider.set(provider);

    const newParams: Record<string, string> = {};
    const newRequired = new Set<string>();

    if (provider && provider.parameters) {
      Object.entries(provider.parameters).forEach(([name, param]) => {
        if (param.required) {
          newRequired.add(name);
        }

        let initialValue = "";
        if (this.isEditMode() && this.data?.options) {
          initialValue = this.data.options[name] || "";
        }

        newParams[name] = initialValue;
      });
    }

    this.parametersModel.set(newParams);
    this.requiredParams.set(newRequired);
    this.parametersDirty.set(false);

    if (this.isEditMode() && this.data) {
      const paramKeys = provider ? Object.keys(provider.parameters) : [];

      const nextCustomOptions: Record<string, string> = {};
      Object.entries(this.data.options || {}).forEach(([key, value]) => {
        if (!paramKeys.includes(key)) {
          nextCustomOptions[key] = value;
        }
      });
      this.customOptions = nextCustomOptions;

      this.customHeaders = { ...(this.data.headers || {}) };

      // Restore the secret checkbox state from the API response
      const nextOptionSecrets: Record<string, boolean> = {};
      for (const key of this.data.secret_options || []) {
        if (!paramKeys.includes(key)) {
          nextOptionSecrets[key] = true;
        }
      }
      this.optionSecrets = nextOptionSecrets;

      const nextHeaderSecrets: Record<string, boolean> = {};
      for (const key of this.data.secret_headers || []) {
        nextHeaderSecrets[key] = true;
      }
      this.headerSecrets = nextHeaderSecrets;

      this.initialParametersModel.set({ ...newParams });
      this.initialCustomOptions = { ...nextCustomOptions };
      this.initialCustomHeaders = { ...this.customHeaders };
      this.initialOptionSecrets = { ...nextOptionSecrets };
      this.initialHeaderSecrets = { ...nextHeaderSecrets };
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  async save(): Promise<boolean> {
    if (!this.smsForm().valid() || !this.parametersValid()) {
      return false;
    }

    // Persist draft footer rows on Save as well, so users do not have to click Add first.
    if (this.newOptionKey()) {
      const key = this.newOptionKey();
      this.customOptions = {
        ...this.customOptions,
        [key]: this.newOptionValue()
      };
      if (this.newOptionSecret()) {
        this.optionSecrets = { ...this.optionSecrets, [key]: true };
      } else {
        const nextOptionSecrets = { ...this.optionSecrets };
        delete nextOptionSecrets[key];
        this.optionSecrets = nextOptionSecrets;
      }
      this.newOptionKey.set("");
      this.newOptionValue.set("");
      this.newOptionSecret.set(false);
    }

    if (this.newHeaderKey()) {
      const key = this.newHeaderKey();
      this.customHeaders = {
        ...this.customHeaders,
        [key]: this.newHeaderValue()
      };
      if (this.newHeaderSecret()) {
        this.headerSecrets = { ...this.headerSecrets, [key]: true };
      } else {
        const nextHeaderSecrets = { ...this.headerSecrets };
        delete nextHeaderSecrets[key];
        this.headerSecrets = nextHeaderSecrets;
      }
      this.newHeaderKey.set("");
      this.newHeaderValue.set("");
      this.newHeaderSecret.set(false);
    }

    const formValue = this.smsModel();
    const paramValue = this.parametersModel();

    const payload: SmsGatewayPayload = {
      name: formValue.name,
      description: formValue.description,
      module: formValue.providermodule
    };

    if (this.isEditMode()) {
      payload["id"] = this.data?.id;
    }

    Object.entries(paramValue).forEach(([key, value]) => {
      payload[`option.${key}`] = value;
      // If the provider declares this parameter as secret, send the flag
      const paramDef = this.selectedProvider()?.parameters?.[key];
      if (paramDef?.secret) {
        payload[`secret.option.${key}`] = 1;
      }
    });

    Object.entries(this.customOptions).forEach(([key, value]) => {
      payload[`option.${key}`] = value;
      payload[`secret.option.${key}`] = this.optionSecrets[key] ? 1 : 0;
    });

    Object.entries(this.customHeaders).forEach(([key, value]) => {
      payload[`header.${key}`] = value;
      payload[`secret.header.${key}`] = this.headerSecrets[key] ? 1 : 0;
    });

    try {
      await this.smsGatewayService.postSmsGateway(payload);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
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
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (!success) return;
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    }
  }

  addOption(): void {
    if (this.newOptionKey()) {
      this.customOptions = {
        ...this.customOptions,
        [this.newOptionKey()]: this.newOptionValue()
      };
      if (this.newOptionSecret()) {
        this.optionSecrets = { ...this.optionSecrets, [this.newOptionKey()]: true };
      }

      this.newOptionKey.set("");
      this.newOptionValue.set("");
      this.newOptionSecret.set(false);
    }
  }

  deleteOption(key: string): void {
    const rest = { ...this.customOptions };
    delete rest[key];
    this.customOptions = rest;
    const restSecrets = { ...this.optionSecrets };
    delete restSecrets[key];
    this.optionSecrets = restSecrets;
  }

  addHeader(): void {
    if (this.newHeaderKey()) {
      this.customHeaders = {
        ...this.customHeaders,
        [this.newHeaderKey()]: this.newHeaderValue()
      };
      if (this.newHeaderSecret()) {
        this.headerSecrets = { ...this.headerSecrets, [this.newHeaderKey()]: true };
      }

      this.newHeaderKey.set("");
      this.newHeaderValue.set("");
      this.newHeaderSecret.set(false);
    }
  }

  deleteHeader(key: string): void {
    const rest = { ...this.customHeaders };
    delete rest[key];
    this.customHeaders = rest;
    const restSecrets = { ...this.headerSecrets };
    delete restSecrets[key];
    this.headerSecrets = restSecrets;
  }

  toggleOptionSecret(key: string): void {
    this.optionSecrets = { ...this.optionSecrets, [key]: !this.optionSecrets[key] };
  }

  toggleHeaderSecret(key: string): void {
    this.headerSecrets = { ...this.headerSecrets, [key]: !this.headerSecrets[key] };
  }

  protected readonly input = input;
}
