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
import { effect, inject, Injectable, signal, Signal } from "@angular/core";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { AdditionalCondition } from "@services/policies/policies.service";
import { catchError, map, Observable, of, shareReplay, tap } from "rxjs";

export type PolicyTemplateIndex = Record<string, string>;

const EMPTY_INDEX: PolicyTemplateIndex = {};

export interface PolicyTemplate {
  name: string;
  scope: string;
  description?: string;
  action?: Record<string, string | boolean>;
  realm?: string[];
  resolver?: string[];
  adminrealm?: string[];
  conditions?: AdditionalCondition[];
  user_agents?: string[];
}

export interface PolicyTemplatesServiceInterface {
  readonly policyTemplatesIndex: Signal<PolicyTemplateIndex>;

  getTemplate(templateName: string): Observable<PolicyTemplate | undefined>;
}

/**
 * Relative URL that is resolved against the document's `<base href>`:
 *   - In dev (`ng serve`) the `public/` folder is mounted at `/`, so the
 *     request hits `/policy-templates/...` directly.
 *   - In a production build the build output places the files under
 *     `dist/privacyidea-webui/browser/policy-templates/`, which is served at
 *     `/static/dist/privacyidea-webui/browser/policy-templates/...`.
 */
const POLICY_TEMPLATE_URL = "policy-templates/";

/**
 * The backend defaults `policy_template_url` to this legacy path, which is
 * served by the old WebUI but does not exist in the new bundle. Treat it as
 * "unset" and fall back to the locally bundled templates.
 */
const LEGACY_POLICY_TEMPLATE_URL = "/static/policy-templates/";

@Injectable({
  providedIn: "root"
})
export class PolicyTemplatesService implements PolicyTemplatesServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  private readonly _index = signal<PolicyTemplateIndex>(EMPTY_INDEX);
  readonly policyTemplatesIndex: Signal<PolicyTemplateIndex> = this._index.asReadonly();

  private templateCache = new Map<string, Observable<PolicyTemplate | undefined>>();
  private lastBaseUrl: string | null = null;

  constructor() {
    effect(() => {
      const baseUrl = this.resolveBaseUrl(this.authService.policyTemplateUrl());
      if (baseUrl === this.lastBaseUrl) return;
      this.lastBaseUrl = baseUrl;
      this.templateCache.clear();
      this.fetchIndex(baseUrl);
    });
  }

  getTemplate(templateName: string): Observable<PolicyTemplate | undefined> {
    const cached = this.templateCache.get(templateName);
    if (cached) return cached;

    const baseUrl = this.lastBaseUrl ?? this.resolveBaseUrl(this.authService.policyTemplateUrl());
    const request = this.http.get<PolicyTemplate>(`${baseUrl}${templateName}.json`).pipe(
      map((template) => ({ ...template, name: template.name ?? templateName })),
      catchError(() => {
        this.templateCache.delete(templateName);
        this.notificationService.error($localize`Error fetching policy template ${templateName}.`);
        return of(undefined);
      }),
      shareReplay(1)
    );
    this.templateCache.set(templateName, request);
    return request;
  }

  private fetchIndex(baseUrl: string): void {
    this.http
      .get<PolicyTemplateIndex>(`${baseUrl}index.json`)
      .pipe(
        tap((index) => {
          if (this.lastBaseUrl !== baseUrl) return;
          this._index.set(index);
        }),
        catchError(() => {
          if (this.lastBaseUrl !== baseUrl) return of(null);
          this.notificationService.error($localize`Error fetching policy templates.`);
          this._index.set(EMPTY_INDEX);
          return of(null);
        })
      )
      .subscribe();
  }

  private resolveBaseUrl(url: string | undefined | null): string {
    const raw = url && url.length > 0 ? url : POLICY_TEMPLATE_URL;
    const withTrailingSlash = raw.endsWith("/") ? raw : `${raw}/`;
    // The backend's default points to the old WebUI which no longer exists in
    // the new bundle; use the locally bundled templates instead.
    if (withTrailingSlash === LEGACY_POLICY_TEMPLATE_URL) {
      return POLICY_TEMPLATE_URL;
    }
    // Absolute URLs (https://...) are used verbatim.
    if (/^https?:\/\//i.test(withTrailingSlash)) {
      return withTrailingSlash;
    }

    // Absolute-path URLs are prefixed with the dev proxy so they reach the
    // Flask backend in `ng serve`; in production `proxyUrl` is empty.
    if (withTrailingSlash.startsWith("/")) {
      return `${environment.proxyUrl}${withTrailingSlash}`;
    }
    // Path-relative URLs resolve against `<base href>` and are served by the
    // Angular bundle itself in both dev and prod.
    return withTrailingSlash;
  }
}
