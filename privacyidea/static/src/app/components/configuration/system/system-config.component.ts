/*
 * (c) NetKnights GmbH 2025, https://netknights.it
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
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Component, computed, effect, inject, OnDestroy, OnInit, signal, untracked, ViewChild } from "@angular/core";
import { disabled, form, FormField, pattern } from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { ERR } from "@utils/form-rules.utils";
import { clearField, hasError, touchAll } from "@utils/form-state.utils";
import { isChecked } from "@utils/parse-boolean-value";
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog/system-documentation-dialog.component";

/** The settings this page edits. An unset setting is `false` or `""`. */
export interface SystemConfigModel {
  splitAtSign: boolean;
  IncFailCountOnFalsePin: boolean;
  no_auth_counter: boolean;
  PrependPin: boolean;
  AutoResync: boolean;
  AutoResyncTimeout: string;
  OverrideAuthorizationClient: string;
  UserCacheExpiration: string;
  failcounter_clear_timeout: string;
  DefaultChallengeValidityTime: string;
  DefaultCountWindow: string;
  DefaultMaxFailCount: string;
  DefaultOtpLen: string;
  DefaultSyncWindow: string;
  "recovery.identifier": string;
}

export type SystemConfigKey = keyof SystemConfigModel;

const EMPTY_SYSTEM_CONFIG: SystemConfigModel = {
  splitAtSign: false,
  IncFailCountOnFalsePin: false,
  no_auth_counter: false,
  PrependPin: false,
  AutoResync: false,
  AutoResyncTimeout: "",
  OverrideAuthorizationClient: "",
  UserCacheExpiration: "",
  failcounter_clear_timeout: "",
  DefaultChallengeValidityTime: "",
  DefaultCountWindow: "",
  DefaultMaxFailCount: "",
  DefaultOtpLen: "",
  DefaultSyncWindow: "",
  "recovery.identifier": ""
};

const SYSTEM_CONFIG_KEYS = Object.keys(EMPTY_SYSTEM_CONFIG) as SystemConfigKey[];
const BOOLEAN_KEYS: readonly SystemConfigKey[] = [
  "splitAtSign",
  "IncFailCountOnFalsePin",
  "no_auth_counter",
  "PrependPin",
  "AutoResync"
];

/** Settings without a control on this page. They are read as booleans and sent back with the saved settings. */
const PASS_THROUGH_BOOLEAN_KEYS = ["UiLoginDisplayHelpButton", "UiLoginDisplayRealmBox"];

/** Settings the backend reads with `int()`: a count, a length or a time span, never negative or fractional. */
const NON_NEGATIVE_INTEGER_PATTERN = /^\d+$/;

@Component({
  selector: "app-system-config",
  templateUrl: "./system-config.component.html",
  imports: [
    FormField,
    MatFormField,
    MatError,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
    MatHint,
    MatSuffix,
    RouterLink,
    MatCheckbox,
    ScrollToTopDirective,
    MatButton,
    MatIcon,
    ClearableInputComponent,
    ClearButtonComponent
  ],
  styleUrls: ["./system-config.component.scss"]
})
export class SystemConfigComponent implements OnInit, OnDestroy {
  private readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly authService = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly dialog = inject(MatDialog);
  private readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly pendingChangesService = inject(PendingChangesService);
  @ViewChild("scrollContainer", { static: true }) scrollContainer!: ScrollToTopDirective;

  readonly model = signal<SystemConfigModel>({ ...EMPTY_SYSTEM_CONFIG });
  readonly systemConfigForm = form(this.model, (f) => {
    disabled(f.AutoResyncTimeout, ({ valueOf }) => !valueOf(f.AutoResync));
    pattern(f.failcounter_clear_timeout, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.AutoResyncTimeout, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.UserCacheExpiration, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.DefaultOtpLen, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.DefaultCountWindow, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.DefaultMaxFailCount, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.DefaultSyncWindow, NON_NEGATIVE_INTEGER_PATTERN);
    pattern(f.DefaultChallengeValidityTime, NON_NEGATIVE_INTEGER_PATTERN);
  });

  /** The model as loaded or last saved. */
  private readonly savedModel = signal<SystemConfigModel>({ ...EMPTY_SYSTEM_CONFIG });
  /** Settings without a field in the model, sent back unchanged. */
  private extraConfig: Record<string, string | boolean> = {};
  /** Keys the backend holds. A key outside this set is sent only once it has a value. */
  private readonly storedKeys = new Set<string>();

  readonly hasChanges = computed(() => JSON.stringify(this.model()) !== JSON.stringify(this.savedModel()));
  readonly canSave = computed(() => this.systemConfigForm().valid());
  readonly smtpIdentifiers = computed<string[]>(() =>
    this.smtpService.smtpServers().map((server) => server.identifier)
  );

  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
  protected readonly clearField = clearField;
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  constructor() {
    effect(() => {
      const config = this.systemService.systemConfig();
      if (config && Object.keys(config).length > 0) {
        untracked(() => this.loadConfig(config));
      }
    });
  }

  ngOnInit(): void {
    this.loadSystemConfig();
    this.smtpService.smtpServerResource.reload();
    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerValidChanges(() => this.hasConfigWritePermission() && this.canSave());
    this.pendingChangesService.registerSave(() => this._saveAndReturn());
  }

  loadSystemConfig(): void {
    this.systemService.systemConfigResource.reload();
  }

  saveSystemConfig(): void {
    if (!this.canSave()) {
      void touchAll(this.systemConfigForm);
      return;
    }
    this.systemService.saveSystemConfig(this.saveBody()).subscribe({
      next: (response) => {
        if (response.result?.status) {
          this.markSaved();
          this.notificationService.success(
            $localize`:@@systemConfig.systemConfigurationSaved:System configuration saved successfully.`
          );
        } else {
          this.notificationService.error(
            $localize`:@@systemConfig.failedSaveSystem:Failed to save system configuration.`
          );
        }
      },
      error: (error) => {
        console.error("Error saving system configuration:", error);
        this.notificationService.error($localize`:@@systemConfig.errorSavingSystem:Error saving system configuration.`);
      }
    });
  }

  private _saveAndReturn(): Promise<boolean> {
    if (!this.canSave()) {
      void touchAll(this.systemConfigForm);
      return Promise.resolve(false);
    }
    return new Promise<boolean>((resolve) => {
      this.systemService.saveSystemConfig(this.saveBody()).subscribe({
        next: (response) => {
          if (response.result?.status) {
            this.markSaved();
            this.notificationService.success(
              $localize`:@@systemConfig.systemConfigurationSaved:System configuration saved successfully.`
            );
            resolve(true);
          } else {
            this.notificationService.error(
              $localize`:@@systemConfig.failedSaveSystem:Failed to save system configuration.`
            );
            resolve(false);
          }
        },
        error: () => {
          this.notificationService.error(
            $localize`:@@systemConfig.errorSavingSystem:Error saving system configuration.`
          );
          resolve(false);
        }
      });
    });
  }

  private loadConfig(config: Record<string, string>): void {
    const loaded: Record<string, string | boolean> = { ...EMPTY_SYSTEM_CONFIG };
    const extra: Record<string, string | boolean> = {};
    this.storedKeys.clear();
    for (const [key, value] of Object.entries(config)) {
      if (value === undefined) {
        continue;
      }
      if (this.isModelKey(key)) {
        this.storedKeys.add(key);
        loaded[key] = BOOLEAN_KEYS.includes(key) ? isChecked(value) : value;
      } else {
        extra[key] = PASS_THROUGH_BOOLEAN_KEYS.includes(key) ? isChecked(value) : value;
      }
    }
    this.extraConfig = extra;
    this.model.set(loaded as unknown as SystemConfigModel);
    this.savedModel.set({ ...this.model() });
    this.systemConfigForm().reset();
    // A stored invalid setting disables Save, so its error is shown right away.
    if (!this.canSave()) void touchAll(this.systemConfigForm);
  }

  private isModelKey(key: string): key is SystemConfigKey {
    return SYSTEM_CONFIG_KEYS.includes(key as SystemConfigKey);
  }

  /**
   * The settings sent on save: every setting outside the model unchanged, plus each modelled setting the backend
   * already holds or the admin has set. An unset setting is not written as `""` or `false`.
   */
  private saveBody(): Record<string, string | boolean> {
    const model = this.model();
    const body: Record<string, string | boolean> = { ...this.extraConfig };
    for (const key of SYSTEM_CONFIG_KEYS) {
      if (this.storedKeys.has(key) || model[key] !== EMPTY_SYSTEM_CONFIG[key]) {
        body[key] = model[key];
      }
    }
    return body;
  }

  private markSaved(): void {
    const model = this.model();
    SYSTEM_CONFIG_KEYS.filter((key) => model[key] !== EMPTY_SYSTEM_CONFIG[key]).forEach((key) =>
      this.storedKeys.add(key)
    );
    this.savedModel.set({ ...model });
  }

  deleteUserCache(): void {
    this.systemService.deleteUserCache().subscribe({
      next: (response) => {
        if (response.result?.status) {
          this.notificationService.success(
            $localize`:@@systemConfig.userCacheDeleted:User cache deleted successfully.`
          );
        } else {
          this.notificationService.error($localize`:@@systemConfig.failedDeleteUser:Failed to delete user cache.`);
        }
      },
      error: (error) => {
        console.error("Error deleting user cache:", error);
        this.notificationService.error($localize`:@@systemConfig.errorDeleting:Error deleting user cache.`);
      }
    });
  }

  hasConfigWritePermission(): boolean {
    return this.authService.actionAllowed("configwrite");
  }

  protected openDocumentationDialog() {
    this.systemService.getDocumentation().subscribe({
      next: (documentation) => {
        this.dialog.open(SystemDocumentationDialogComponent, {
          data: { documentation }
        });
      },
      error: (error) => {
        console.error("Error loading system documentation:", error);
        this.notificationService.error(
          $localize`:@@systemConfig.errorLoadingSystem:Error loading system documentation.`
        );
      }
    });
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }
}
