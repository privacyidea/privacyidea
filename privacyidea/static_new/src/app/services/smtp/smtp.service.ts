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
import { HttpClient, HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

export interface SmtpServer {
  identifier: string;
  server: string;
  port: number;
  timeout: number;
  sender: string;
  username?: string;
  password?: string;
  description?: string;
  tls: boolean;
  enqueue_job: boolean;
  certificate?: string;
  private_key?: string;
  private_key_password?: string;
  smime: boolean;
  dont_send_on_error: boolean;
}

export type SmtpServers = Record<string, SmtpServer>;

export interface SmtpServiceInterface {
  smtpServerResource: HttpResourceRef<PiResponse<SmtpServers> | undefined>;
  readonly smtpServers: Signal<SmtpServer[]>;

  postSmtpServer(server: SmtpServer): Promise<void>;

  testSmtpServer(params: SmtpServer & { recipient: string }): Promise<boolean>;

  deleteSmtpServer(identifier: string): Promise<void>;
}

@Injectable()
export class SmtpService implements SmtpServiceInterface {
  readonly smtpServerBaseUrl = environment.proxyUrl + "/smtpserver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly http: HttpClient = inject(HttpClient);

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.smtpServerResource.error(), "SMTP servers");
    });
  }

  readonly smtpServerResource = httpResource<PiResponse<SmtpServers>>(() => {
    if (
      !this.contentService.onExternalSmtp() &&
      !this.contentService.onConfigurationTokenTypes() &&
      !this.contentService.onConfigurationSystem()
    ) {
      return undefined;
    }
    return {
      url: `${this.smtpServerBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly smtpServers = computed<SmtpServer[]>(() => {
    if (!this.smtpServerResource.hasValue()) return [];
    const res = this.smtpServerResource.value();
    const values = res?.result?.value;
    if (values) {
      return Object.entries(values).map(([identifier, server]) => ({
        ...server,
        identifier
      }));
    }
    return [];
  });

  async postSmtpServer(server: SmtpServer): Promise<void> {
    const url = `${this.smtpServerBaseUrl}${encodeURIComponent(server.identifier)}`;
    const request = this.http.post<PiResponse<boolean>>(url, server, { headers: this.authService.getHeaders() });

    try {
      await lastValueFrom(request);
      this.notificationService.success($localize`Successfully saved SMTP server.`);
      this.smtpServerResource.reload();
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to save SMTP server. ` + message);
      throw new Error("post-failed", { cause: error });
    }
  }

  async testSmtpServer(params: SmtpServer & { recipient: string }): Promise<boolean> {
    const url = `${this.smtpServerBaseUrl}send_test_email`;
    const request = this.http.post<PiResponse<boolean>>(url, params, { headers: this.authService.getHeaders() });
    try {
      const res = await lastValueFrom(request);
      if (res?.result?.value) {
        this.notificationService.success($localize`Test email sent successfully.`);
        return true;
      }
      return false;
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to send test email. ` + message);
      return false;
    }
  }

  async deleteSmtpServer(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<boolean>>(
      `${this.smtpServerBaseUrl}${encodeURIComponent(identifier)}`,
      {
        headers: this.authService.getHeaders()
      }
    );
    try {
      await lastValueFrom(request);
      this.notificationService.success($localize`Successfully deleted SMTP server: ${identifier}.`);
      this.smtpServerResource.reload();
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to delete SMTP server. ` + message);
      throw new Error("delete-failed", { cause: error });
    }
  }
}
