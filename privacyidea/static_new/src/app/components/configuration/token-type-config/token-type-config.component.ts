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
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  signal,
  ViewChild
} from "@angular/core";
import { takeUntilDestroyed, toSignal } from "@angular/core/rxjs-interop";
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
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";
import { SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { forkJoin, lastValueFrom } from "rxjs";

@Component({
  selector: "app-token-type-config",
  standalone: true,
  imports: [
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

  formData = linkedSignal<Record<string, string>, Record<string, string>>({
    source: () => this.systemService.systemConfig(),
    computation: (config) => this.reconcileQuestions({ ...config }, true)
  });

  onFormDataChange(data: Record<string, string | number | boolean>): void {
    const normalized: Record<string, string> = {};
    for (const [key, value] of Object.entries(data)) {
      normalized[key] = typeof value === "boolean" ? (value ? "True" : "False") : String(value);
    }
    const prevRequired = parseInt(this.formData()[QUESTION_NUMBER_OF_ANSWERS] ?? "", 10) || 0;
    const newRequired = parseInt(normalized[QUESTION_NUMBER_OF_ANSWERS] ?? "", 10) || 0;
    const reconciled = this.reconcileQuestions(normalized, newRequired < prevRequired);
    const backend = this.systemService.systemConfig() ?? {};
    Object.keys(backend).forEach((key) => {
      if (key.startsWith("question.question.") && !(key in reconciled)) {
        this.pendingDeletes.update((set) => new Set(set).add(key));
      }
    });
    this.formData.set(reconciled);
  }

  pendingDeletes = linkedSignal<Record<string, string>, Set<string>>({
    source: () => this.systemService.systemConfig(),
    computation: () => new Set<string>()
  });

  hasChanges = computed(() => {
    const current = this.formData();
    const original = this.systemConfig();
    const deletes = this.pendingDeletes();

    if (deletes.size > 0) return true;

    const currentKeys = Object.keys(current);
    const originalKeys = Object.keys(original);

    if (currentKeys.length !== originalKeys.length) return true;

    for (const key of currentKeys) {
      if (current[key] !== original[key]) return true;
    }

    return false;
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

  get questionKeys() {
    return Object.keys(this.formData()).filter((k) => k.startsWith("question.question."));
  }

  get hasEmptyQuestions() {
    return this.questionKeys.some((k) => !(this.formData()[k] ?? "").trim());
  }

  private reconcileQuestions(data: Record<string, string>, allowTrim = false): Record<string, string> {
    const result: Record<string, string> = { ...data };
    const required = parseInt(result[QUESTION_NUMBER_OF_ANSWERS] ?? "", 10) || 0;

    const questionKeys = Object.keys(result).filter((k) => k.startsWith("question.question."));
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

  get yubikeyApiIds() {
    return Object.keys(this.formData()).filter((k) => k.startsWith("yubikey.apiid."));
  }

  ngOnInit() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(() => this.savePromise());

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
    this.formData.update((f) => ({ ...f, [this.nextQuestionKey(f)]: "" }));
  }

  deleteQuestion(key: string) {
    const existedInitially = Object.hasOwn(this.systemService.systemConfig() ?? {}, key);

    // Remove from local form data so it disappears from the list immediately
    this.formData.update((f) => {
      const next = { ...f };
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
    this.formData.update((f) => {
      const next = { ...f };
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

    if (!apiId) {
      this.notificationService.warning($localize`Please enter a Client ID.`);
      return;
    }

    if (generateKey) {
      try {
        const response = await lastValueFrom(
          this.http.get<PiResponse<string>>(environment.proxyUrl + "/system/random?len=20&encode=b64", {
            headers: this.authService.getHeaders()
          })
        );
        const generatedKey = response?.result?.value;
        if (generatedKey) {
          this.formData.update((f) => ({
            ...f,
            [`yubikey.apiid.${apiId}`]: generatedKey
          }));
        }
      } catch {
        this.notificationService.error($localize`Failed to generate API key.`);
      }
    } else {
      this.formData.update((f) => ({
        ...f,
        [`yubikey.apiid.${apiId}`]: apiKey
      }));
    }
  }

  save() {
    return this.savePromise();
  }

  async savePromise(): Promise<boolean> {
    // Empty question slots are UI scaffolding for the user to fill in; they must
    // never be persisted. Strip them from the payload, and make sure any backend
    // question that is now empty or removed gets deleted rather than written back
    // as an empty string (which would resurrect a deleted question or save a blank
    // one when saving bypasses the disabled button, e.g. via the unsaved-changes guard).
    const payload: Record<string, string> = {};
    for (const [key, value] of Object.entries(this.formData())) {
      if (key.startsWith("question.question.") && !(value ?? "").trim()) {
        continue;
      }
      payload[key] = value;
    }

    const backend = this.systemService.systemConfig() ?? {};
    const deletes = new Set(this.pendingDeletes());
    Object.keys(backend).forEach((key) => {
      if (key.startsWith("question.question.") && !(key in payload)) {
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
        this.notificationService.success($localize`Token configuration saved successfully.`);
        this.pendingDeletes.set(new Set());
        this.systemService.systemConfigResource.reload();
        return true;
      } else {
        this.notificationService.error($localize`Failed to save token configuration.`);
        return false;
      }
    } catch {
      this.notificationService.error($localize`Error saving token configuration.`);
      return false;
    }
  }

  ngOnDestroy() {
    this.pendingChangesService.clearAllRegistrations();
  }

  onCheckboxChange(key: string, event: { checked: boolean }) {
    this.formData.update((f) => ({
      ...f,
      [key]: event.checked ? "True" : "False"
    }));
  }
}
