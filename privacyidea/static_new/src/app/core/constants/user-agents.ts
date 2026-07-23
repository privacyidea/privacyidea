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

/**
 * A known privacyIDEA client user agent: a friendly `displayName` shown in the UI, plus the `identifier` that
 * actually prefixes the user-agent string the plugin sends.
 */
export interface UserAgentPreset {
  displayName: string;
  identifier: string;
}

export const USER_AGENT_PRESETS: readonly UserAgentPreset[] = [
  { displayName: "Credential Provider", identifier: "privacyidea-cp" },
  { displayName: "Keycloak", identifier: "privacyIDEA-Keycloak" },
  { displayName: "AD FS", identifier: "PrivacyIDEA-ADFS" },
  { displayName: "SimpleSAMLphp", identifier: "simpleSAMLphp" },
  { displayName: "PAM", identifier: "PAM" },
  { displayName: "Shibboleth", identifier: "privacyIDEA-Shibboleth" },
  { displayName: "Nextcloud", identifier: "privacyidea-nextcloud" },
  { displayName: "FreeRADIUS", identifier: "FreeRADIUS" },
  { displayName: "LDAP Proxy", identifier: "privacyIDEA-LDAP-Proxy" },
  { displayName: "privacyIDEA Authenticator", identifier: "privacyIDEA-App" },
  { displayName: "privacyIDEA WebUI", identifier: "privacyIDEA-WebUI" }
];
