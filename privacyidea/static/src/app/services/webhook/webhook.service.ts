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
import { lastValueFrom, Observable } from "rxjs";

/**
 * The placeholder the API sends in place of a stored secret, and the value to send back to keep
 * that secret unchanged. An empty string clears it; anything else replaces it. Mirrors CENSORED in
 * privacyidea.lib.crypto.
 */
export const WEBHOOK_CENSORED = "__CENSORED__";

export type WebhookAuthType = "none" | "basic" | "header" | "mtls";
export type WebhookHttpMethod = "GET" | "POST" | "PUT" | "PATCH";

export const WEBHOOK_AUTH_TYPES: readonly WebhookAuthType[] = ["none", "basic", "header", "mtls"];
export const WEBHOOK_HTTP_METHODS: readonly WebhookHttpMethod[] = ["GET", "POST", "PUT", "PATCH"];

/** The content types offered in the editor; any valid MIME type may be typed instead. */
export const WEBHOOK_CONTENT_TYPES: readonly string[] = ["application/json", "application/x-www-form-urlencoded"];

/**
 * A webhook definition as GET /webhook/ returns it. The endpoint belongs to the object (URL, method,
 * auth, headers, TLS, proxy, timeout); the payload belongs to the call site, so `default_payload` is
 * only the body used when the caller supplies none.
 */
export interface Webhook {
  id?: number;
  identifier: string;
  description?: string;
  url: string;
  http_method: WebhookHttpMethod;
  content_type: string;
  default_payload?: string | null;
  auth_type: WebhookAuthType;
  username?: string;
  password?: string;
  verify_tls: boolean;
  tls_ca_bundle?: string;
  client_certificate?: string;
  client_key?: string;
  client_key_password?: string;
  http_proxy?: string;
  https_proxy?: string;
  timeout: number;
  headers: Record<string, string>;
  /**
   * Names of the headers whose values are stored encrypted. Sent back as `secret.header.*` so a
   * round-trip does not rewrite an encrypted header in clear text.
   */
  secret_headers: string[];
}

/** What POST /webhook/<identifier>/test reports; a failed delivery is still HTTP 200. */
export interface WebhookTestResult {
  success: boolean;
  status_code: number | null;
  response: string;
  error: string | null;
}

export interface WebhookServiceInterface {
  webhookResource: HttpResourceRef<PiResponse<Webhook[]> | undefined>;
  readonly webhooks: Signal<Webhook[]>;
  readonly webhookIdentifiers: Signal<string[]>;

  postWebhook(webhook: Webhook): Promise<void>;

  testWebhook(identifier: string, payload?: string): Promise<WebhookTestResult | null>;

  deleteWebhook(identifier: string): Promise<void>;

  listWebhooks(): Observable<PiResponse<Webhook[]>>;
}

@Injectable()
export class WebhookService implements WebhookServiceInterface {
  readonly webhookBaseUrl = environment.proxyUrl + "/webhook/";
  readonly webhooks = computed<Webhook[]>(() => {
    if (!this.webhookResource.hasValue()) return [];
    return this.webhookResource.value()?.result?.value ?? [];
  });
  readonly webhookIdentifiers = computed<string[]>(() => this.webhooks().map((webhook) => webhook.identifier));
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly webhookResource = httpResource<PiResponse<Webhook[]>>(() => {
    // Conditional access appears in this list because its WEBHOOK stage action picks the webhook that
    // is fired from these identifiers, the way the email actions pick an SMTP server.
    const onPageUsingTheList = this.contentService.onExternalWebhook() || this.contentService.onConditionalAccess();
    // /webhook/ itself requires webhook_read, so this guard skips the request rather than letting it 403; only
    // the Webhooks menu entry is gated on that right, so pages that merely consume the list need this check too.
    if (!onPageUsingTheList || !this.authService.actionAllowed("webhook_read")) {
      return undefined;
    }
    return {
      url: `${this.webhookBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.webhookResource.error(), "webhooks");
    });
  }

  /**
   * Flatten a webhook into the parameters POST /webhook/<identifier> expects: the headers go out as
   * `header.<name>`, their secret flags as `secret.header.<name>`, and `clear_headers` is what says
   * "remove the last one" - with no `header.*` parameter at all the server keeps the stored set,
   * so an emptied header table would otherwise be a silent no-op.
   */
  private static toRequestBody(webhook: Webhook): Record<string, unknown> {
    // `id` is the database key the list carries; the endpoint takes the identifier from the path.
    const { headers, secret_headers, id: __, ...rest } = webhook;
    const body: Record<string, unknown> = { ...rest };
    const names = Object.keys(headers ?? {});
    for (const name of names) {
      body[`header.${name}`] = headers[name];
      if ((secret_headers ?? []).includes(name)) {
        body[`secret.header.${name}`] = "1";
      }
    }
    if (names.length === 0) {
      body["clear_headers"] = true;
    }
    return body;
  }

  async postWebhook(webhook: Webhook): Promise<void> {
    const url = `${this.webhookBaseUrl}${encodeURIComponent(webhook.identifier)}`;
    const request = this.http.post<PiResponse<number>>(url, WebhookService.toRequestBody(webhook), {
      headers: this.authService.getHeaders()
    });

    try {
      await lastValueFrom(request);
      this.notificationService.success($localize`:@@webhook.successfullySaved:Successfully saved webhook.`);
      this.webhookResource.reload();
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`:@@webhook.failedSave:Failed to save webhook. ${message}:MESSAGE:`);
      throw new Error("post-failed", { cause: error });
    }
  }

  /**
   * Fire the stored webhook once. A webhook that answers with an error is not an API error: the
   * request succeeds and the result carries `success: false` with the reason, which is reported
   * here rather than thrown. `null` means the request itself failed (no webhook, no right).
   */
  async testWebhook(identifier: string, payload?: string): Promise<WebhookTestResult | null> {
    const url = `${this.webhookBaseUrl}${encodeURIComponent(identifier)}/test`;
    const body = payload ? { payload } : {};
    const request = this.http.post<PiResponse<WebhookTestResult>>(url, body, {
      headers: this.authService.getHeaders()
    });
    try {
      const res = await lastValueFrom(request);
      const result = res?.result?.value ?? null;
      if (result?.success) {
        this.notificationService.success(
          $localize`:@@webhook.testSucceeded:The endpoint answered with status ${result.status_code}:STATUS:.`
        );
      } else {
        this.notificationService.error(
          $localize`:@@webhook.testFailed:The webhook failed: ${result?.error || result?.status_code || ""}:REASON:`
        );
      }
      return result;
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`:@@webhook.failedTest:Could not test the webhook. ${message}:MESSAGE:`);
      return null;
    }
  }

  async deleteWebhook(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<number>>(`${this.webhookBaseUrl}${encodeURIComponent(identifier)}`, {
      headers: this.authService.getHeaders()
    });
    try {
      await lastValueFrom(request);
      this.notificationService.success(
        $localize`:@@webhook.successfullyDeleted:Successfully deleted webhook: ${identifier}:IDENTIFIER:.`
      );
      this.webhookResource.reload();
    } catch (error) {
      const message = (error as HttpErrorResponse).error?.result?.error?.message || "";
      this.notificationService.error($localize`:@@webhook.failedDelete:Failed to delete webhook. ${message}:MESSAGE:`);
      throw new Error("delete-failed", { cause: error });
    }
  }

  listWebhooks(): Observable<PiResponse<Webhook[]>> {
    return this.http.get<PiResponse<Webhook[]>>(this.webhookBaseUrl, {
      headers: this.authService.getHeaders()
    });
  }
}
