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
import { Component, computed, effect, inject, signal, untracked } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatDividerModule } from "@angular/material/divider";
import { SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "../../../services/sms-gateway/sms-gateway.service";
import { SmtpService, SmtpServiceInterface } from "../../../services/smtp/smtp.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { HttpClient } from "@angular/common/http";
import { environment } from "../../../../environments/environment";
import { lastValueFrom } from "rxjs";
import { PiResponse } from "../../../app.component";
import { RouterLink } from "@angular/router";

@Component({
  selector: "app-token-type-config",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    RouterLink
  ],
  templateUrl: "./token-type-config.component.html",
  styleUrl: "./token-type-config.component.scss"
})
export class TokenTypeConfigComponent {
  readonly systemService: SystemServiceInterface = inject(SystemService);
  readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  formData = signal<Record<string, any>>({});
  nextQuestion = signal(0);
  newApiId = signal("");
  newQuestionText = signal("");

  systemConfig = this.systemService.systemConfig;
  systemConfigInit = this.systemService.systemConfigInit;
  smsGateways = this.smsGatewayService.smsGateways;
  smtpServers = this.smtpService.smtpServers;

  // Fallbacks when backend does not provide init values
  hashLibs = computed<string[]>(() => this.systemConfigInit()?.hashlibs ?? ["sha1", "sha256", "sha512"]);
  totpSteps = computed<string[]>(() => {
    const steps = this.systemConfigInit()?.totpSteps ?? [30, 60];
    return (Array.isArray(steps) ? steps : [steps]).map((s: any) => String(s));
  });
  smsProviders = computed<string[]>(() => this.systemConfigInit()?.smsProviders ?? []);

  constructor() {
    effect(() => {
      // Initialize form with system config values
      const config = this.systemService.systemConfig();
      if (config && Object.keys(config).length > 0) {
        untracked(() => {
          this.formData.set({ ...config });

          // Find next question index
          let max = -1;
          Object.keys(config).forEach(key => {
            if (key.startsWith("question.question.")) {
              const idx = parseInt(key.substring("question.question.".length));
              if (!isNaN(idx) && idx > max) {
                max = idx;
              }
            }
          });
          this.nextQuestion.set(max + 1);
        });
      }
    });
  }

  get questionKeys() {
    return Object.keys(this.formData()).filter(k => k.startsWith("question.question."));
  }

  get yubikeyApiIds() {
    return Object.keys(this.formData()).filter(k => k.startsWith("yubikey.apiid."));
  }

  addQuestion() {
    const text = String(this.newQuestionText() ?? "").trim();
    if (!text) {
      this.notificationService.openSnackBar($localize`Please enter a question.`);
      return;
    }
    const index = this.nextQuestion();
    this.formData.update(f => ({
      ...f,
      [`question.question.${index}`]: text
    }));
    this.newQuestionText.set("");
    this.nextQuestion.update(n => n + 1);
  }

  deleteSystemEntry(key: string) {
    this.systemService.deleteSystemConfig(key).subscribe({
      next: (response) => {
        if (response?.result?.status) {
          this.notificationService.openSnackBar($localize`System entry deleted.`);
          this.systemService.systemConfigResource.reload();
        } else {
          this.notificationService.openSnackBar($localize`Failed to delete system entry.`);
        }
      },
      error: () => {
        this.notificationService.openSnackBar($localize`Failed to delete system entry.`);
      }
    });
  }

  async yubikeyCreateNewKey(apiId: string) {
    if (!apiId) {
      this.notificationService.openSnackBar($localize`Please enter a Client ID.`);
      return;
    }
    try {
      const response = await lastValueFrom(
        this.http.get<PiResponse<string>>(
          environment.proxyUrl + "/system/random?len=20&encode=b64",
          { headers: this.authService.getHeaders() }
        )
      );
      if (response?.result?.value) {
        this.formData.update(f => ({
          ...f,
          [`yubikey.apiid.${apiId}`]: response.result?.value
        }));
      }
    } catch (e) {
      this.notificationService.openSnackBar($localize`Failed to generate API key.`);
    }
  }

  save() {
    this.systemService.saveSystemConfig(this.formData()).subscribe({
      next: () => {
        this.notificationService.openSnackBar($localize`Token configuration saved successfully.`);
        this.systemService.systemConfigResource.reload();
      }
    });
  }

  isChecked(val: any): boolean {
    return val === "True" || val === true || val === "1" || val === 1;
  }

  onCheckboxChange(key: string, event: any) {
    this.formData.update(f => ({
      ...f,
      [key]: event.checked ? "True" : "False"
    }));
  }
}
