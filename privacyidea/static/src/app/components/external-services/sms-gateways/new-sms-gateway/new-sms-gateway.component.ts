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
import { Component, OnDestroy, computed, effect, inject, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FieldTree, FormField, applyEach, disabled, form, required } from "@angular/forms/signals";
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
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
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
import { ERR, identifierName } from "@utils/form-rules.utils";
import { clearField, hasError, touchAll } from "@utils/form-state.utils";

interface KeyValueRow {
  key: string;
  value: string;
  secret: boolean;
}

interface SmsFormModel {
  name: string;
  providermodule: string;
  description: string;
  /** Values of the selected provider's parameters, keyed by parameter name. */
  parameters: Record<string, string>;
}

interface DraftRowModel {
  key: string;
  value: string;
  secret: boolean;
}

const emptySmsForm = (): SmsFormModel => ({
  name: "",
  providermodule: "",
  description: "",
  parameters: {}
});

const emptyDraftRow = (): DraftRowModel => ({ key: "", value: "", secret: false });

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
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  protected data: SmsGateway | null = null;
  private gatewayName: string | null = null;

  isEditMode = signal(false);

  smsModel = signal<SmsFormModel>(emptySmsForm());
  /** The form values as loaded, so a field typed back to its loaded value does not count as a change. */
  private initialSmsModel: SmsFormModel = emptySmsForm();
  private initialCustomOptions: Record<string, string> = {};
  private initialCustomHeaders: Record<string, string> = {};

  smsForm = form(this.smsModel, (f) => {
    identifierName(f.name);
    required(f.providermodule);
    disabled(f.name, () => this.isEditMode());
    applyEach(f.parameters, (parameter) => required(parameter, { when: ({ key }) => this.isParameterRequired(key()) }));
  });

  /** Bumped by every form (re)initialization, so the provider effect re-applies the provider for freshly loaded gateway data. */
  private readonly formGeneration = signal(0);
  /** Module of the selected provider and form generation. The provider effect tracks it instead of the whole model, so typing a parameter does not re-run it. */
  private readonly providerSelection = computed(
    () => ({ module: this.smsModel().providermodule, generation: this.formGeneration() }),
    { equal: (a, b) => a.module === b.module && a.generation === b.generation }
  );
  /** The module and form generation the provider was last applied for. A re-run for the same pair keeps the typed values. */
  private appliedProvider: { module: string; generation: number } | null = null;

  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
  protected readonly clearField = clearField;

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
      const { module } = this.providerSelection();
      if (providers && module) {
        untracked(() => this.onProviderChange(module));
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const gateways = this.smsGatewayService.smsGateways();
      if (this.isEditMode() && this.gatewayName && untracked(() => !this.hasChanges)) {
        const found = gateways.find((g) => g.name === this.gatewayName);
        if (found) {
          this.data = found;
          untracked(() => this.initForm());
        }
      }
    });
  }

  /** The field of a provider parameter, or undefined while the model does not hold the key. */
  parameterField(key: string): FieldTree<string> | undefined {
    return this.smsForm.parameters[key];
  }

  private isParameterRequired(key: string): boolean {
    return !!this.selectedProvider()?.parameters?.[key]?.required;
  }

  customOptions: Record<string, string> = {};
  customHeaders: Record<string, string> = {};
  optionSecrets: Record<string, boolean> = {};
  headerSecrets: Record<string, boolean> = {};
  private initialOptionSecrets: Record<string, boolean> = {};
  private initialHeaderSecrets: Record<string, boolean> = {};

  /** Draft of the option row in the table footer. Its key is required before Add is enabled. */
  optionDraft = signal<DraftRowModel>(emptyDraftRow());
  optionDraftForm = form(this.optionDraft, (f) => required(f.key));
  /** Draft of the header row in the table footer. Its key is required before Add is enabled. */
  headerDraft = signal<DraftRowModel>(emptyDraftRow());
  headerDraftForm = form(this.headerDraft, (f) => required(f.key));

  optionDisplayedColumns: string[] = ["key", "value", "secret", "actions"];
  optionFooterColumns: string[] = ["footerKey", "footerValue", "footerSecret", "footerActions"];

  headerDisplayedColumns: string[] = ["key", "value", "secret", "actions"];
  headerFooterColumns: string[] = ["footerKey", "footerValue", "footerSecret", "footerActions"];

  providers = computed<Record<string, SmsProvider>>(() => {
    if (!this.smsGatewayService.smsProvidersResource.hasValue()) return {};
    return this.smsGatewayService.smsProvidersResource.value()?.result?.value ?? {};
  });

  selectedProvider = signal<SmsProvider | undefined>(undefined);
  private initForm(): void {
    this.formGeneration.update((generation) => generation + 1);
    const module = this.data?.providermodule || "";
    this.smsModel.set({
      name: this.data?.name || "",
      providermodule: module,
      description: this.data?.description || "",
      parameters: this.parameterValues(module)
    });
    this.initialSmsModel = { ...this.smsModel(), parameters: { ...this.smsModel().parameters } };
    this.initialCustomOptions = {};
    this.initialCustomHeaders = {};
    this.initialOptionSecrets = {};
    this.initialHeaderSecrets = {};
    this.optionDraft.set(emptyDraftRow());
    this.headerDraft.set(emptyDraftRow());
    this.smsForm().reset();
    this.optionDraftForm().reset();
    this.headerDraftForm().reset();
  }

  /** The parameter values of a provider: the given current values, else the stored options in edit mode, else empty strings. */
  private parameterValues(module: string, current: Record<string, string> = {}): Record<string, string> {
    const values: Record<string, string> = {};
    for (const name of Object.keys(this.providers()[module]?.parameters ?? {})) {
      values[name] = current[name] ?? ((this.isEditMode() && this.data?.options?.[name]) || "");
    }
    return values;
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
      // A value set by the component is not a change; a typed value is one until it equals the loaded value again.
      (this.smsForm().dirty() && !this.smsModelEqual(this.smsModel(), this.initialSmsModel)) ||
      !this.recordsEqual(this.customOptions, this.initialCustomOptions) ||
      !this.recordsEqual(this.customHeaders, this.initialCustomHeaders) ||
      !this.recordsEqual(this.optionSecrets, this.initialOptionSecrets) ||
      !this.recordsEqual(this.headerSecrets, this.initialHeaderSecrets) ||
      this.isDraftFilled(this.optionDraft()) ||
      this.isDraftFilled(this.headerDraft())
    );
  }

  private isDraftFilled(draft: DraftRowModel): boolean {
    return !!draft.key || !!draft.value || draft.secret;
  }

  private smsModelEqual(a: SmsFormModel, b: SmsFormModel): boolean {
    return (
      a.name === b.name &&
      a.providermodule === b.providermodule &&
      a.description === b.description &&
      this.recordsEqual(a.parameters, b.parameters)
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
    return this.smsForm().valid();
  }

  onProviderChange(module: string): void {
    const providers = this.providers();
    if (!providers) return;

    const provider = providers[module];
    this.selectedProvider.set(provider);

    const keepTyped =
      this.appliedProvider?.module === module && this.appliedProvider.generation === this.formGeneration();
    this.appliedProvider = { module, generation: this.formGeneration() };
    this.smsModel.update((m) => ({
      ...m,
      parameters: this.parameterValues(module, keepTyped ? m.parameters : undefined)
    }));
    this.initialSmsModel = {
      ...this.initialSmsModel,
      parameters: this.parameterValues(module, keepTyped ? this.initialSmsModel.parameters : undefined)
    };
    if (keepTyped) {
      return;
    }
    this.smsForm.parameters().reset();

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
    if (!this.canSave) {
      await touchAll(this.smsForm);
      return false;
    }

    // Persist draft footer rows on Save as well, so users do not have to click Add first.
    this.addOption();
    this.addHeader();

    const formValue = this.smsModel();

    const payload: SmsGatewayPayload = {
      name: formValue.name,
      description: formValue.description,
      module: formValue.providermodule
    };

    if (this.isEditMode()) {
      payload["id"] = this.data?.id;
    }

    Object.entries(formValue.parameters).forEach(([key, value]) => {
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

  async deleteGateway(): Promise<void> {
    const identifier = this.gatewayName;
    if (!identifier) {
      return;
    }
    const confirmed = await this.dialogService.confirmDelete({
      title: $localize`:@@smsGateway.deleteSmsGateway:Delete SMS Gateway`,
      items: [identifier],
      itemType: $localize`:@@smsGateway.smsGateway:SMS gateway`
    });
    if (!confirmed) {
      return;
    }
    try {
      await this.smsGatewayService.deleteSmsGateway(identifier);
    } catch {
      return;
    }
    this.pendingChangesService.clearAllRegistrations();
    await this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
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
    const draft = this.optionDraft();
    if (!this.optionDraftForm().valid()) {
      return;
    }
    this.customOptions = { ...this.customOptions, [draft.key]: draft.value };
    this.optionSecrets = this.withSecretFlag(this.optionSecrets, draft.key, draft.secret);
    this.optionDraft.set(emptyDraftRow());
    this.optionDraftForm().reset();
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
    const draft = this.headerDraft();
    if (!this.headerDraftForm().valid()) {
      return;
    }
    this.customHeaders = { ...this.customHeaders, [draft.key]: draft.value };
    this.headerSecrets = this.withSecretFlag(this.headerSecrets, draft.key, draft.secret);
    this.headerDraft.set(emptyDraftRow());
    this.headerDraftForm().reset();
  }

  deleteHeader(key: string): void {
    const rest = { ...this.customHeaders };
    delete rest[key];
    this.customHeaders = rest;
    const restSecrets = { ...this.headerSecrets };
    delete restSecrets[key];
    this.headerSecrets = restSecrets;
  }

  private withSecretFlag(secrets: Record<string, boolean>, key: string, secret: boolean): Record<string, boolean> {
    const next = { ...secrets };
    if (secret) {
      next[key] = true;
    } else {
      delete next[key];
    }
    return next;
  }

  toggleOptionSecret(key: string): void {
    this.optionSecrets = { ...this.optionSecrets, [key]: !this.optionSecrets[key] };
  }

  toggleHeaderSecret(key: string): void {
    this.headerSecrets = { ...this.headerSecrets, [key]: !this.headerSecrets[key] };
  }
}
