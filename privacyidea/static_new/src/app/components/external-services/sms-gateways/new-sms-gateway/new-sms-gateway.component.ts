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
import {
  AfterViewInit,
  Component,
  computed,
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
import { MatOptionModule } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  SmsGateway,
  SmsGatewayService,
  SmsGatewayServiceInterface,
  SmsProvider
} from "@services/sms-gateway/sms-gateway.service";

type KeyValueRow = { key: string; value: string };

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
    ClearableInputComponent,
    CommonModule
  ],
  templateUrl: "./new-sms-gateway.component.html",
  styleUrl: "./new-sms-gateway.component.scss"
})
export class NewSmsGatewayComponent implements AfterViewInit, OnDestroy {
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly renderer = inject(Renderer2);

  protected data: SmsGateway | null = null;
  private gatewayName: string | null = null;

  isEditMode = signal(false);

  smsModel = signal<SmsFormModel>({ ...EMPTY_SMS_FORM });

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

  customOptions: Record<string, string> = {};
  customHeaders: Record<string, string> = {};

  newOptionKey = signal("");
  newOptionValue = signal("");
  newHeaderKey = signal("");
  newHeaderValue = signal("");

  optionDisplayedColumns: string[] = ["key", "value", "actions"];
  optionFooterColumns: string[] = ["footerKey", "footerValue", "footerActions"];

  headerDisplayedColumns: string[] = ["key", "value", "actions"];
  headerFooterColumns: string[] = ["footerKey", "footerValue", "footerActions"];

  providers = computed<Record<string, SmsProvider>>(() => {
    if (!this.smsGatewayService.smsProvidersResource.hasValue()) return {};
    return this.smsGatewayService.smsProvidersResource.value()?.result?.value ?? {};
  });

  selectedProvider = signal<SmsProvider | undefined>(undefined);

  private _observer!: IntersectionObserver;

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

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
    this.smsModel.set({
      name: this.data?.name || "",
      providermodule: this.data?.providermodule || "",
      description: this.data?.description || ""
    });
    this.smsForm().reset();
  }

  get optionRows(): KeyValueRow[] {
    return Object.entries(this.customOptions)
      .map(([key, value]) => ({ key, value }))
      .sort((a, b) => a.key.localeCompare(b.key));
  }

  get headerRows(): KeyValueRow[] {
    return Object.entries(this.customHeaders)
      .map(([key, value]) => ({ key, value }))
      .sort((a, b) => a.key.localeCompare(b.key));
  }

  get hasChanges(): boolean {
    return (
      this.smsForm().dirty() ||
      this.parametersDirty() ||
      Object.keys(this.customOptions).length > 0 ||
      Object.keys(this.customHeaders).length > 0
    );
  }

  providerEntries(): Array<{ key: string; value: SmsProvider }> {
    const providersObj = this.providers() ?? {};
    return Object.entries(providersObj).map(([key, value]) => ({ key, value }));
  }

  parameterEntries(): Array<{ key: string; value: any }> {
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
        if ((param as any).required) {
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
    }
  }

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) return;
    this._observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const shouldFloat = entry.boundingClientRect.top < entry.rootBounds.top;
        if (shouldFloat) {
          this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
        } else {
          this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
        }
      },
      { root: this.scrollContainer.nativeElement, threshold: [0, 1] }
    );
    this._observer.observe(this.stickySentinel.nativeElement);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
    this._observer?.disconnect();
  }

  async save(): Promise<boolean> {
    if (!this.smsForm().valid() || !this.parametersValid()) {
      return false;
    }
    const formValue = this.smsModel();
    const paramValue = this.parametersModel();

    const payload: any = {
      name: formValue.name,
      description: formValue.description,
      module: formValue.providermodule
    };

    if (this.isEditMode()) {
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

    try {
      await this.smsGatewayService.postSmsGateway(payload);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
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

      this.newOptionKey.set("");
      this.newOptionValue.set("");
    }
  }

  deleteOption(key: string): void {
    const { [key]: _, ...rest } = this.customOptions;
    this.customOptions = rest;
  }

  addHeader(): void {
    if (this.newHeaderKey()) {
      this.customHeaders = {
        ...this.customHeaders,
        [this.newHeaderKey()]: this.newHeaderValue()
      };

      this.newHeaderKey.set("");
      this.newHeaderValue.set("");
    }
  }

  deleteHeader(key: string): void {
    const { [key]: _, ...rest } = this.customHeaders;
    this.customHeaders = rest;
  }
}
