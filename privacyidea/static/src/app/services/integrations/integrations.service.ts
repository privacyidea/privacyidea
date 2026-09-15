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
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";

/**
 * One entry of the shared ecosystem-integration catalog served by the backend
 * (privacyidea.lib.integrations). Replaces what used to be three independently
 * hardcoded lists: the API client `client_type` dropdown, the policy `user_agents`
 * condition picker, and the dashboard subscription widget's rows.
 */
export interface Integration {
  id: string;
  label: string;
  agent_names: string[];
  policy_value: string;
  product_id: string | null;
  api_client: boolean;
  dashboard: boolean;
  section: string | null;
  ptl_slug: string | null;
  github_repo: string | null;
}

export interface IntegrationsServiceInterface {
  integrationsResource: HttpResourceRef<PiResponse<Integration[]> | undefined>;
  integrations: WritableSignal<Integration[]>;

  apiClientIntegrations(): Integration[];

  dashboardIntegrations(): Integration[];

  labelFor(id: string): string;

  labelForPolicyValue(policyValue: string): string;
}

@Injectable()
export class IntegrationsService implements IntegrationsServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  private readonly integrationsBaseUrl = environment.proxyUrl + "/info/integrations";

  integrationsResource = httpResource<PiResponse<Integration[]>>(() => {
    if (this.authService.isSelfServiceUser()) return undefined;
    if (!this.contentService.onDashboard() && !this.contentService.onApiClients() && !this.contentService.onPolicies()) {
      return undefined;
    }
    return {
      url: this.integrationsBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  integrations: WritableSignal<Integration[]> = linkedSignal({
    source: () => ({
      value: this.integrationsResource.hasValue() ? this.integrationsResource.value() : undefined,
      isLoading: this.integrationsResource.isLoading(),
      error: this.integrationsResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return [];
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? (previous?.value ?? []) : [];
      return value;
    }
  });

  apiClientIntegrations(): Integration[] {
    return this.integrations().filter((integration) => integration.api_client);
  }

  dashboardIntegrations(): Integration[] {
    return this.integrations().filter((integration) => integration.dashboard);
  }

  labelFor(id: string): string {
    return this.integrations().find((integration) => integration.id === id)?.label ?? id;
  }

  labelForPolicyValue(policyValue: string): string {
    // The server matches policy user_agents case-insensitively, so a hand-typed value
    // still gets the label of the preset it means.
    const normalized = policyValue.toLowerCase();
    return (
      this.integrations().find((integration) => integration.policy_value.toLowerCase() === normalized)?.label ??
      policyValue
    );
  }
}
