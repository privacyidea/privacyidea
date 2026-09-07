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
import { signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { Integration, IntegrationsServiceInterface } from "@services/integrations/integrations.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

// Mirrors the real backend catalog (privacyidea.lib.integrations.CATALOG) field for
// field, so specs exercising section grouping/ordering see the same shape production
// does.
export const MOCK_INTEGRATIONS: Integration[] = [
  {
    id: "privacyidea-app",
    label: "privacyIDEA Authenticator App",
    agent_names: ["privacyIDEA-App"],
    policy_value: "privacyIDEA-App",
    product_id: "privacyidea authenticator",
    api_client: false,
    dashboard: true,
    section: "use_cases",
    ptl_slug: "privacyidea-authenticator-app",
    github_repo: "privacyidea/pi-authenticator"
  },
  {
    id: "freeradius",
    label: "FreeRADIUS",
    agent_names: ["FreeRADIUS"],
    policy_value: "FreeRADIUS",
    product_id: "privacyidea",
    api_client: true,
    dashboard: true,
    section: "use_cases",
    ptl_slug: "privacyidea-freeradius",
    github_repo: "privacyidea/FreeRADIUS"
  },
  {
    id: "privacyidea-nextcloud",
    label: "Nextcloud",
    agent_names: ["privacyidea-nextcloud"],
    policy_value: "privacyidea-nextcloud",
    product_id: "privacyidea-nextcloud",
    api_client: true,
    dashboard: true,
    section: "use_cases",
    ptl_slug: "privacyidea-nextcloud",
    github_repo: "privacyidea/privacyidea-nextcloud-app"
  },
  {
    id: "privacyidea-cp",
    label: "Windows Credential Provider",
    agent_names: ["privacyidea-cp"],
    policy_value: "privacyidea-cp",
    product_id: "privacyidea-cp",
    api_client: true,
    dashboard: true,
    section: "system_login",
    ptl_slug: "privacyidea-windows-credential-provider",
    github_repo: "privacyidea/privacyidea-credential-provider"
  },
  {
    id: "pam",
    label: "PAM OTP & Push",
    agent_names: ["PAM", "pam-privacyidea"],
    policy_value: "PAM",
    product_id: "privacyidea-pam",
    api_client: true,
    dashboard: true,
    section: "system_login",
    ptl_slug: "privacyidea-pam-otp-push",
    github_repo: "privacyidea/privacyidea-pam"
  },
  {
    id: "pam-passkey",
    label: "PAM Passkey",
    agent_names: ["pam-passkey"],
    policy_value: "pam-passkey",
    product_id: "privacyidea-pam",
    api_client: true,
    dashboard: true,
    section: "system_login",
    ptl_slug: "privacyidea-pam-passkey",
    github_repo: "privacyidea/pam-passkey"
  },
  {
    id: "privacyidea-keycloak",
    label: "Keycloak",
    agent_names: ["privacyIDEA-Keycloak"],
    policy_value: "privacyIDEA-Keycloak",
    product_id: "privacyidea-keycloak",
    api_client: true,
    dashboard: true,
    section: "single_sign_on",
    ptl_slug: "privacyidea-keycloak",
    github_repo: "privacyidea/keycloak-provider"
  },
  {
    id: "entraid-via-keycloak",
    label: "EntraID via Keycloak",
    agent_names: ["entraid-via-keycloak"],
    policy_value: "entraid-via-keycloak",
    product_id: "privacyidea-keycloak",
    api_client: true,
    dashboard: true,
    section: "single_sign_on",
    ptl_slug: "privacyidea-entraid-integration",
    github_repo: "privacyidea/keycloak-protocolmapper-entraid"
  },
  {
    id: "privacyidea-adfs",
    label: "AD FS",
    agent_names: ["PrivacyIDEA-ADFS"],
    policy_value: "PrivacyIDEA-ADFS",
    product_id: "privacyidea-adfs",
    api_client: true,
    dashboard: true,
    section: "single_sign_on",
    ptl_slug: "privacyidea-adfs",
    github_repo: "privacyidea/adfs-provider"
  },
  {
    id: "privacyidea-shibboleth",
    label: "Shibboleth",
    agent_names: ["privacyIDEA-Shibboleth"],
    policy_value: "privacyIDEA-Shibboleth",
    product_id: "privacyidea-shibboleth",
    api_client: true,
    dashboard: true,
    section: "single_sign_on",
    ptl_slug: "privacyidea-shibboleth",
    github_repo: "privacyidea/shibboleth-plugin"
  },
  {
    id: "simplesamlphp",
    label: "SimpleSAMLphp",
    agent_names: ["simpleSAMLphp", "privacyidea-simplesamlphp"],
    policy_value: "simpleSAMLphp",
    product_id: "privacyidea-simplesamlphp",
    api_client: false,
    dashboard: false,
    section: null,
    ptl_slug: null,
    github_repo: null
  },
  {
    id: "privacyidea-ldap-proxy",
    label: "LDAP Proxy",
    agent_names: ["privacyIDEA-LDAP-Proxy"],
    policy_value: "privacyIDEA-LDAP-Proxy",
    product_id: "privacyidea-ldap-proxy",
    api_client: false,
    dashboard: false,
    section: null,
    ptl_slug: null,
    github_repo: null
  },
  {
    id: "privacyidea-webui",
    label: "privacyIDEA WebUI",
    agent_names: ["privacyIDEA-WebUI"],
    policy_value: "privacyIDEA-WebUI",
    product_id: null,
    api_client: false,
    dashboard: false,
    section: null,
    ptl_slug: null,
    github_repo: null
  }
];

export class MockIntegrationsService implements IntegrationsServiceInterface {
  integrationsResource = new MockHttpResourceRef<PiResponse<Integration[]> | undefined>(
    MockPiResponse.fromValue<Integration[]>(MOCK_INTEGRATIONS)
  );

  integrations = signal<Integration[]>(MOCK_INTEGRATIONS);

  apiClientIntegrations = jest.fn(() => this.integrations().filter((integration) => integration.api_client));
  dashboardIntegrations = jest.fn(() => this.integrations().filter((integration) => integration.dashboard));
  labelFor = jest.fn((id: string) => this.integrations().find((integration) => integration.id === id)?.label ?? id);
  labelForPolicyValue = jest.fn((policyValue: string) => {
    const normalized = policyValue.toLowerCase();
    return (
      this.integrations().find((integration) => integration.policy_value.toLowerCase() === normalized)?.label ??
      policyValue
    );
  });
}
