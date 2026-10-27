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

import { HttpClient } from "@angular/common/http";
import {
  AfterViewInit,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  signal,
  untracked,
  ViewChild
} from "@angular/core";
import { takeUntilDestroyed, toSignal } from "@angular/core/rxjs-interop";
import { form } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatAccordion, MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ActivatedRoute } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { DaypasswordConfigComponent } from "@components/configuration/token-type-config/token-types/daypassword-config/daypassword-config.component";
import { EmailConfigComponent } from "@components/configuration/token-type-config/token-types/email-config/email-config.component";
import { HotpConfigComponent } from "@components/configuration/token-type-config/token-types/hotp-config/hotp-config.component";
import { QuestionnaireConfigComponent } from "@components/configuration/token-type-config/token-types/questionnaire-config/questionnaire-config.component";
import { RadiusConfigComponent } from "@components/configuration/token-type-config/token-types/radius-config/radius-config.component";
import { RemoteConfigComponent } from "@components/configuration/token-type-config/token-types/remote-config/remote-config.component";
import { SmsConfigComponent } from "@components/configuration/token-type-config/token-types/sms-config/sms-config.component";
import { TiqrConfigComponent } from "@components/configuration/token-type-config/token-types/tiqr-config/tiqr-config.component";
import { TotpConfigComponent } from "@components/configuration/token-type-config/token-types/totp-config/totp-config.component";
import { U2fConfigComponent } from "@components/configuration/token-type-config/token-types/u2f-config/u2f-config.component";
import { WebauthnConfigComponent } from "@components/configuration/token-type-config/token-types/webauthn-config/webauthn-config.component";
import { YubicoConfigComponent } from "@components/configuration/token-type-config/token-types/yubico-config/yubico-config.component";
import {
  ApiKeyData,
  YubikeyConfigComponent
} from "@components/configuration/token-type-config/token-types/yubikey-config/yubikey-config.component";
import {
  isOmittedWhenEmpty,
  isQuestionKey,
  systemConfigDiffers,
  toSystemConfig,
  toTokenTypeConfigModel,
  TokenTypeConfigModel,
  tokenTypeConfigSchema,
  withoutEmptyDefaulted
} from "@components/configuration/token-type-config/token-type-config.form";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";
import { SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { touchAll } from "@utils/form-state.utils";
import { forkJoin, lastValueFrom } from "rxjs";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";

@Component({
  selector: "app-token-type-config",
  standalone: true,
  imports: [
    TooltipAriaLabelDirective,
    MatExpansionModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    HotpConfigComponent,
    TotpConfigComponent,
    U2fConfigComponent,
    WebauthnConfigComponent,
    RadiusConfigComponent,
    RemoteConfigComponent,
    SmsConfigComponent,
    TiqrConfigComponent,
    EmailConfigComponent,
    QuestionnaireConfigComponent,
    YubicoConfigComponent,
    YubikeyConfigComponent,
    DaypasswordConfigComponent,
    StickyHeaderDirective
  ],
  templateUrl: "./token-type-config.component.html",
  styleUrl: "./token-type-config.component.scss"
})
export class TokenTypeConfigComponent implements OnInit, AfterViewInit, OnDestroy {
  readonly systemService: SystemServiceInterface = inject(SystemService);
  readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  queryParams = toSignal(this.route.queryParams);
  expandEmail = computed(() => this.queryParams()?.["expanded"] === "email");

  @ViewChild(MatAccordion) accordion!: MatAccordion;

  allPanelsOpen = signal(false);

  toggleAllPanels(): void {
    if (this.allPanelsOpen()) {
      this.accordion?.closeAll();
      this.allPanelsOpen.set(false);
    } else {
      this.accordion?.openAll();
      this.allPanelsOpen.set(true);
    }
  }

  formData = linkedSignal<Record<string, string>, TokenTypeConfigModel>({
    source: () => this.systemService.systemConfig(),
    computation: (config) => {
      const model = toTokenTypeConfigModel(config);
      return { ...model, values: this.reconcileQuestions(model.values, true) };
    }
  });
  readonly configForm = form(this.formData, tokenTypeConfigSchema);

  private requiredAnswers: number | null = null;

  constructor() {
    effect(() => {
      const values = this.formData().values;
      untracked(() => this.syncQuestionSlots(values));
    });
  }

  /** Adds or trims the empty question slots so they match the configured number of answers. */
  private syncQuestionSlots(values: Record<string, string>): void {
    const newRequired = parseInt(values[QUESTION_NUMBER_OF_ANSWERS] ?? "", 10) || 0;
    const prevRequired = this.requiredAnswers ?? newRequired;
    this.requiredAnswers = newRequired;
    const reconciled = this.reconcileQuestions(values, newRequired < prevRequired);
    if (!systemConfigDiffers(reconciled, values)) return;

    const backend = this.systemService.systemConfig() ?? {};
    Object.keys(backend).forEach((key) => {
      if (isQuestionKey(key) && !(key in reconciled)) {
        this.pendingDeletes.update((set) => new Set(set).add(key));
      }
    });
    this.updateValues(() => reconciled);
  }

  private updateValues(change: (values: Record<string, string>) => Record<string, string>): void {
    this.formData.update((model) => ({ ...model, values: change(model.values) }));
  }

  pendingDeletes = linkedSignal<Record<string, string>, Set<string>>({
    source: () => this.systemService.systemConfig(),
    computation: () => new Set<string>()
  });

  hasChanges = computed(() => {
    const original = this.systemConfig();
    if (this.pendingDeletes().size > 0) return true;
    return systemConfigDiffers(toSystemConfig(this.formData(), original), withoutEmptyDefaulted(original));
  });

  systemConfig = this.systemService.systemConfig;
  systemConfigInit = this.systemService.systemConfigInit;
  smsGateways = this.smsGatewayService.smsGateways;
  smtpServers = this.smtpService.smtpServers;

  smsGatewayNames = computed(() => this.smsGateways().map((g) => g.name));
  smtpServerIdentifiers = computed(() => this.smtpServers().map((s) => s.identifier));

  // Fallbacks when backend does not provide init values
  hashLibs = computed<string[]>(() => this.systemConfigInit()?.hashlibs ?? ["sha1", "sha256", "sha512"]);
  totpSteps = computed<string[]>(() => {
    const steps = this.systemConfigInit()?.totpSteps ?? [30, 60];
    return (Array.isArray(steps) ? steps : [steps]).map((s) => String(s));
  });

  expandedPanel: string | null = null;

  questionKeys = computed(() => Object.keys(this.formData().values).filter(isQuestionKey));

  private reconcileQuestions(data: Record<string, string>, allowTrim = false): Record<string, string> {
    const result: Record<string, string> = { ...data };
    const required = parseInt(result[QUESTION_NUMBER_OF_ANSWERS] ?? "", 10) || 0;

    const questionKeys = Object.keys(result).filter(isQuestionKey);
    const emptyKeys = questionKeys.filter((k) => !(result[k] ?? "").trim());
    const filledCount = questionKeys.length - emptyKeys.length;
    const targetEmpty = Math.max(0, required - filledCount);

    const removeCount = allowTrim ? Math.max(0, emptyKeys.length - targetEmpty) : 0;
    for (let i = 0; i < removeCount; i++) {
      delete result[emptyKeys[i]];
    }

    let toAdd = targetEmpty - (emptyKeys.length - removeCount);
    while (toAdd > 0) {
      result[this.nextQuestionKey(result)] = "";
      toAdd--;
    }

    return result;
  }

  private nextQuestionKey(data: Record<string, string>): string {
    let max = -1;
    Object.keys(data).forEach((key) => {
      if (key.startsWith("question.question.")) {
        const idx = parseInt(key.substring("question.question.".length), 10);
        if (!isNaN(idx) && idx > max) {
          max = idx;
        }
      }
    });
    return `question.question.${max + 1}`;
  }

  yubikeyApiIds = computed(() => Object.keys(this.formData().values).filter((k) => k.startsWith("yubikey.apiid.")));

  ngOnInit() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(() => this.savePromise());
    this.pendingChangesService.registerValidChanges(() => this.configForm().valid());

    // allow opening a specific panel via URL fragment, e.g. /configuration/token-types#yubico
    this.route.fragment.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((fragment) => {
      if (fragment) {
        this.expandedPanel = fragment;
      }
    });
  }

  ngAfterViewInit() {
    if (this.expandedPanel) {
      // scroll to the initially referenced panel
      const panel = document.getElementById(this.expandedPanel);
      if (panel) {
        panel.scrollIntoView({ behavior: "smooth" });
      }
    }
  }

  addQuestion() {
    this.updateValues((values) => ({ ...values, [this.nextQuestionKey(values)]: "" }));
  }

  deleteQuestion(key: string) {
    const existedInitially = Object.hasOwn(this.systemService.systemConfig() ?? {}, key);

    // Remove from local form data so it disappears from the list immediately
    this.updateValues((values) => {
      const next = { ...values };
      delete next[key];
      return this.reconcileQuestions(next);
    });

    // If it existed on the backend, collect it for deletion on save
    if (existedInitially) {
      this.pendingDeletes.update((set) => {
        const copy = new Set(set);
        copy.add(key);
        return copy;
      });
    }
  }

  deleteSystemEntry(key: string) {
    const existedInitially = Object.hasOwn(this.systemService.systemConfig() ?? {}, key);

    // Remove from local form data so it disappears from the list immediately
    this.updateValues((values) => {
      const next = { ...values };
      delete next[key];
      return next;
    });

    // If it existed on the backend, collect it for deletion on save
    if (existedInitially) {
      this.pendingDeletes.update((set) => {
        const copy = new Set(set);
        copy.add(key);
        return copy;
      });
    }
  }

  async yubikeyAddNewKey(apiKeyData: ApiKeyData) {
    const apiId = apiKeyData.apiId;
    const apiKey = apiKeyData.apiKey;
    const generateKey = apiKeyData.generateKey;

    if (generateKey) {
      try {
        const response = await lastValueFrom(
          this.http.get<PiResponse<string>>(environment.proxyUrl + "/system/random?len=20&encode=b64", {
            headers: this.authService.getHeaders()
          })
        );
        const generatedKey = response?.result?.value;
        if (generatedKey) {
          this.updateValues((values) => ({ ...values, [`yubikey.apiid.${apiId}`]: generatedKey }));
        }
      } catch {
        this.notificationService.error($localize`:@@tokenTypeConfig.failedGenerate:Failed to generate API key.`);
      }
    } else {
      this.updateValues((values) => ({ ...values, [`yubikey.apiid.${apiId}`]: apiKey }));
    }
  }

  save() {
    return this.savePromise();
  }

  async savePromise(): Promise<boolean> {
    // The unsaved-changes guard saves without the disabled button, so the form is checked here as well.
    if (!(await touchAll(this.configForm))) {
      return false;
    }

    const backend = this.systemService.systemConfig() ?? {};
    const payload = toSystemConfig(this.formData(), backend);
    // A question that is no longer in the form, and an emptied entry the backend defaults, are deleted in the
    // backend, not written back.
    const deletes = new Set(this.pendingDeletes());
    Object.keys(backend).forEach((key) => {
      if ((isQuestionKey(key) || isOmittedWhenEmpty(key)) && !(key in payload)) {
        deletes.add(key);
      }
    });
    // Never delete a key we are about to (re)save.
    Object.keys(payload).forEach((key) => deletes.delete(key));

    const deleteCalls = Array.from(deletes).map((key) => this.systemService.deleteSystemConfig(key));
    const saveCall = this.systemService.saveSystemConfig(payload);

    try {
      if (deleteCalls.length > 0) {
        await lastValueFrom(forkJoin(deleteCalls));
      }
      const response = await lastValueFrom(saveCall);
      if (response?.result?.status) {
        this.notificationService.success(
          $localize`:@@tokenTypeConfig.tokenConfiguration:Token configuration saved successfully.`
        );
        this.pendingDeletes.set(new Set());
        this.systemService.systemConfigResource.reload();
        this.configForm().reset();
        return true;
      } else {
        this.notificationService.error(
          $localize`:@@tokenTypeConfig.failedSaveToken:Failed to save token configuration.`
        );
        return false;
      }
    } catch {
      this.notificationService.error($localize`:@@tokenTypeConfig.errorSavingToken:Error saving token configuration.`);
      return false;
    }
  }

  ngOnDestroy() {
    this.pendingChangesService.clearAllRegistrations();
  }
}
