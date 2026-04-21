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
  DestroyRef,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  OnDestroy,
  OnInit,
  Renderer2,
  signal,
  untracked,
  ViewChild
} from "@angular/core";

import { MatExpansionModule } from "@angular/material/expansion";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "../../../services/sms-gateway/sms-gateway.service";
import { SmtpService, SmtpServiceInterface } from "../../../services/smtp/smtp.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { PendingChangesService } from "../../../services/pending-changes/pending-changes.service";
import { HttpClient } from "@angular/common/http";
import { environment } from "../../../../environments/environment";
import { forkJoin, lastValueFrom } from "rxjs";
import { PiResponse } from "../../../app.component";
import { HotpConfigComponent } from "./token-types/hotp-config/hotp-config.component";
import { TotpConfigComponent } from "./token-types/totp-config/totp-config.component";
import { U2fConfigComponent } from "./token-types/u2f-config/u2f-config.component";
import { WebauthnConfigComponent } from "./token-types/webauthn-config/webauthn-config.component";
import { RadiusConfigComponent } from "./token-types/radius-config/radius-config.component";
import { RemoteConfigComponent } from "./token-types/remote-config/remote-config.component";
import { SmsConfigComponent } from "./token-types/sms-config/sms-config.component";
import { TiqrConfigComponent } from "./token-types/tiqr-config/tiqr-config.component";
import { EmailConfigComponent } from "./token-types/email-config/email-config.component";
import { QuestionnaireConfigComponent } from "./token-types/questionnaire-config/questionnaire-config.component";
import { YubicoConfigComponent } from "./token-types/yubico-config/yubico-config.component";
import { ApiKeyData, YubikeyConfigComponent } from "./token-types/yubikey-config/yubikey-config.component";
import { DaypasswordConfigComponent } from "./token-types/daypassword-config/daypassword-config.component";
import { takeUntilDestroyed, toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute } from "@angular/router";

@Component({
  selector: "app-token-type-config",
  standalone: true,
  imports: [
    MatExpansionModule,
    MatButtonModule,
    MatIconModule,
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
    DaypasswordConfigComponent
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
  private readonly renderer = inject(Renderer2);
  private destroyRef = inject(DestroyRef);
  queryParams = toSignal(this.route.queryParams);
  expandEmail = computed(() => this.queryParams()?.["expanded"] === "email");

  @ViewChild("scrollContainer") scrollContainer!: ElementRef;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef;

  private observer!: IntersectionObserver;

  formData = linkedSignal<any, Record<string, any>>({
    source: () => this.systemService.systemConfig(),
    computation: (config) => ({ ...config })
  });
  nextQuestionIndex = linkedSignal<any, number>({
    source: () => this.systemService.systemConfig(),
    computation: (config) => {
      let max = -1;
      Object.keys(config).forEach((key) => {
        if (key.startsWith("question.question.")) {
          const idx = parseInt(key.substring("question.question.".length));
          if (!isNaN(idx) && idx > max) {
            max = idx;
          }
        }
      });
      return max + 1;
    }
  });
  pendingDeletes = linkedSignal<any, Set<string>>({
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
    return (Array.isArray(steps) ? steps : [steps]).map((s: any) => String(s));
  });

  expandedPanel: string | null = null;

  get questionKeys() {
    return Object.keys(this.formData()).filter((k) => k.startsWith("question.question."));
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

    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    const options: IntersectionObserverInit = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;

      if (isSticky) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  addQuestion(text: string) {
    if (!text) {
      this.notificationService.openSnackBar($localize`Please enter a question.`);
      return;
    }
    const index = this.nextQuestionIndex();
    this.formData.update((f) => ({
      ...f,
      [`question.question.${index}`]: text
    }));
    this.nextQuestionIndex.update((n) => n + 1);
  }

  deleteQuestion(key: string) {
    const existedInitially = this.systemService.systemConfig()?.hasOwnProperty(key) ?? false;

    // Remove from local form data so it disappears from the list immediately
    this.formData.update((f) => {
      const next = { ...f } as Record<string, any>;
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

  deleteSystemEntry(key: string) {
    const existedInitially = this.systemService.systemConfig()?.hasOwnProperty(key) ?? false;

    // Remove from local form data so it disappears from the list immediately
    this.formData.update((f) => {
      const next = { ...f } as Record<string, any>;
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
      this.notificationService.openSnackBar($localize`Please enter a Client ID.`);
      return;
    }

    if (generateKey) {
      try {
        const response = await lastValueFrom(
          this.http.get<PiResponse<string>>(environment.proxyUrl + "/system/random?len=20&encode=b64", {
            headers: this.authService.getHeaders()
          })
        );
        if (response?.result?.value) {
          this.formData.update((f) => ({
            ...f,
            [`yubikey.apiid.${apiId}`]: response.result?.value
          }));
        }
      } catch (e) {
        this.notificationService.openSnackBar($localize`Failed to generate API key.`);
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
    const deletes = Array.from(this.pendingDeletes());
    const deleteCalls = deletes.map((key) => this.systemService.deleteSystemConfig(key));
    const saveCall = this.systemService.saveSystemConfig(this.formData());

    try {
      if (deleteCalls.length > 0) {
        await lastValueFrom(forkJoin(deleteCalls));
      }
      const response = await lastValueFrom(saveCall);
      if (response?.result?.status) {
        this.notificationService.openSnackBar($localize`Token configuration saved successfully.`);
        this.pendingDeletes.set(new Set());
        this.systemService.systemConfigResource.reload();
        return true;
      } else {
        this.notificationService.openSnackBar($localize`Failed to save token configuration.`);
        return false;
      }
    } catch (e) {
      this.notificationService.openSnackBar($localize`Error saving token configuration.`);
      return false;
    }
  }

  ngOnDestroy() {
    this.pendingChangesService.clearAllRegistrations();
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  onCheckboxChange(key: string, event: any) {
    this.formData.update((f) => ({
      ...f,
      [key]: event.checked ? "True" : "False"
    }));
  }
}
