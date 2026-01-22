/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { computed, inject, Injectable, Signal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { PiResponse } from "../../app.component";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
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
}

export type SmtpServers = {
  [key: string]: SmtpServer;
};

export interface SmtpServiceInterface {
  smtpServerResource: HttpResourceRef<PiResponse<SmtpServers> | undefined>;
  readonly smtpServers: Signal<SmtpServer[]>;
  postSmtpServer(server: SmtpServer): Promise<void>;
  testSmtpServer(params: any): Promise<boolean>;
  deleteSmtpServer(identifier: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class SmtpService implements SmtpServiceInterface {
  readonly smtpServerBaseUrl = environment.proxyUrl + "/smtpserver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly http: HttpClient = inject(HttpClient);

  readonly smtpServerResource = httpResource<PiResponse<SmtpServers>>(() => {
    return {
      url: `${this.smtpServerBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly smtpServers = computed<SmtpServer[]>(() => {
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
    const url = `${this.smtpServerBaseUrl}${server.identifier}`;
    const request = this.http.post<PiResponse<any>>(url, server, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved SMTP server.`);
        this.smtpServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save SMTP server. ` + message);
        throw new Error("post-failed");
      });
  }

  async testSmtpServer(params: any): Promise<boolean> {
    const url = `${this.smtpServerBaseUrl}send_test_email`;
    const request = this.http.post<PiResponse<boolean>>(url, params, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then((res) => {
        if (res?.result?.value) {
          this.notificationService.openSnackBar($localize`Test email sent successfully.`);
          return true;
        }
        return false;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to send test email. ` + message);
        return false;
      });
  }

  async deleteSmtpServer(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.smtpServerBaseUrl}${identifier}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted SMTP server: ${identifier}.`);
        this.smtpServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete SMTP server. ` + message);
        throw new Error("delete-failed");
      });
  }
}
