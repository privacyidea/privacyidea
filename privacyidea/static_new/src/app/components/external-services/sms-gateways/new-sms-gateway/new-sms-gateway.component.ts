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
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed, toSignal } from "@angular/core/rxjs-interop";
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatOptionModule } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import {
  SmsGateway,
  SmsGatewayService,
  SmsGatewayServiceInterface,
  SmsProvider
} from "../../../../services/sms-gateway/sms-gateway.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { CommonModule } from "@angular/common";

type KeyValueRow = { key: string; value: string };

@Component({
  selector: "app-sms-edit-dialog",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FormsModule,
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
  private readonly formBuilder = inject(FormBuilder);
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly renderer = inject(Renderer2);

  protected data: SmsGateway | null = null;
  private gatewayName: string | null = null;

  smsForm: FormGroup = this.formBuilder.group({
    name: ["", [Validators.required]],
    providermodule: ["", [Validators.required]],
    description: [""]
  });
  parametersForm: FormGroup = this.formBuilder.group({});
  isEditMode = false;

  customOptions: Record<string, string> = {};
  customHeaders: Record<string, string> = {};

  newOptionKey = "";
  newOptionValue = "";
  newHeaderKey = "";
  newHeaderValue = "";

  optionDisplayedColumns: string[] = ["key", "value", "actions"];
  optionFooterColumns: string[] = ["footerKey", "footerValue", "footerActions"];

  headerDisplayedColumns: string[] = ["key", "value", "actions"];
  headerFooterColumns: string[] = ["footerKey", "footerValue", "footerActions"];

  providers = computed<Record<string, SmsProvider>>(() => {
    if (!this.smsGatewayService.smsProvidersResource.hasValue()) return {};
    return this.smsGatewayService.smsProvidersResource.value()?.result?.value ?? {};
  });

  selectedProvider = signal<SmsProvider | undefined>(undefined);

  providermoduleSignal = toSignal(this.smsForm.get("providermodule")!.valueChanges, {
    initialValue: this.data?.providermodule || ""
  });

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
      this.isEditMode = !!this.gatewayName;

      // Load data for editing existing gateway
      if (this.isEditMode && this.gatewayName) {
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
      const module = this.providermoduleSignal();
      if (providers && module) {
        untracked(() => this.onProviderChange(module));
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const gateways = this.smsGatewayService.smsGateways();
      if (this.isEditMode && this.gatewayName && this.smsForm?.pristine) {
        const found = gateways.find((g) => g.name === this.gatewayName);
        if (found) {
          this.data = found;
          this.initForm();
        }
      }
    });
  }

  private initForm(): void {
    this.smsForm.patchValue({
      name: this.data?.name || "",
      providermodule: this.data?.providermodule || "",
      description: this.data?.description || ""
    });
    if (this.isEditMode) {
      this.smsForm.get("name")?.disable();
    } else {
      this.smsForm.get("name")?.enable();
    }
    this.smsForm.markAsPristine();
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
      !this.smsForm.pristine ||
      !this.parametersForm?.pristine ||
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
    return this.smsForm.valid;
  }

  onProviderChange(module: string): void {
    const providers = this.providers();
    if (!providers) return;

    const provider = providers[module];
    this.selectedProvider.set(provider);

    const group: Record<string, any> = {};

    if (provider && provider.parameters) {
      Object.entries(provider.parameters).forEach(([name, param]) => {
        const validators = [];
        if ((param as any).required) {
          validators.push(Validators.required);
        }

        let initialValue = "";
        if (this.isEditMode && this.data?.options) {
          initialValue = this.data.options[name] || "";
        }

        group[name] = [initialValue, validators];
      });
    }

    this.parametersForm = this.formBuilder.group(group);

    if (this.isEditMode && this.data) {
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
    if (this.smsForm.invalid || this.parametersForm.invalid) {
      return false;
    }
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
    if (this.newOptionKey) {
      this.customOptions = {
        ...this.customOptions,
        [this.newOptionKey]: this.newOptionValue
      };

      this.newOptionKey = "";
      this.newOptionValue = "";
    }
  }

  deleteOption(key: string): void {
    const { [key]: _, ...rest } = this.customOptions;
    this.customOptions = rest;
  }

  addHeader(): void {
    if (this.newHeaderKey) {
      this.customHeaders = {
        ...this.customHeaders,
        [this.newHeaderKey]: this.newHeaderValue
      };

      this.newHeaderKey = "";
      this.newHeaderValue = "";
    }
  }

  deleteHeader(key: string): void {
    const { [key]: _, ...rest } = this.customHeaders;
    this.customHeaders = rest;
  }
}
