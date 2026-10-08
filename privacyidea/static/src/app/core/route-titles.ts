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

// The names the pages are known by. The router carries them as each route's `title`, so a page is named where it is
// routed; the admin and the self-service routes share these.
export const PAGE_NAMES = {
  login: $localize`:@@pageTitle.login:Login`,
  dashboard: $localize`:@@pageTitle.dashboard:Dashboard`,
  settings: $localize`:@@pageTitle.settings:UI settings`,
  audit: $localize`:@@pageTitle.audit:Audit log`,
  news: $localize`:@@pageTitle.news:News`,
  clients: $localize`:@@pageTitle.clients:Clients`,
  authenticationLog: $localize`:@@pageTitle.authenticationLog:Authentication log`,
  lockedUsers: $localize`:@@pageTitle.lockedUsers:Locked users`,
  blocklist: $localize`:@@pageTitle.blocklist:Blocklist`,
  tokens: $localize`:@@pageTitle.tokens:Tokens`,
  challenges: $localize`:@@pageTitle.challenges:Token challenges`,
  applications: $localize`:@@pageTitle.applications:Token applications`,
  getSerial: $localize`:@@pageTitle.getSerial:Find a token serial`,
  importTokens: $localize`:@@pageTitle.importTokens:Import tokens`,
  enrollToken: $localize`:@@pageTitle.enrollToken:Enroll a token`,
  assignToken: $localize`:@@pageTitle.assignToken:Assign a token`,
  tokenWizard: $localize`:@@pageTitle.tokenWizard:Token enrollment wizard`,
  containers: $localize`:@@pageTitle.containers:Containers`,
  containerTemplates: $localize`:@@pageTitle.containerTemplates:Container templates`,
  containerWizard: $localize`:@@pageTitle.containerWizard:Container creation wizard`,
  users: $localize`:@@pageTitle.users:Users`,
  realms: $localize`:@@pageTitle.realms:Realms`,
  resolvers: $localize`:@@pageTitle.resolvers:Resolvers`,
  policies: $localize`:@@pageTitle.policies:Policies`,
  conditionalAccess: $localize`:@@pageTitle.conditionalAccess:Conditional access policies`,
  apiClients: $localize`:@@pageTitle.apiClients:API clients`,
  events: $localize`:@@pageTitle.events:Event handlers`,
  machineResolvers: $localize`:@@pageTitle.machineResolvers:Machine resolvers`,
  machines: $localize`:@@pageTitle.machines:Machines`,
  periodicTasks: $localize`:@@pageTitle.periodicTasks:Periodic tasks`,
  system: $localize`:@@pageTitle.system:System configuration`,
  tokenTypes: $localize`:@@pageTitle.tokenTypes:Token type configuration`,
  subscription: $localize`:@@pageTitle.subscription:Subscription`,
  smtp: $localize`:@@pageTitle.smtp:SMTP servers`,
  radius: $localize`:@@pageTitle.radius:RADIUS servers`,
  sms: $localize`:@@pageTitle.sms:SMS gateways`,
  privacyideaServers: $localize`:@@pageTitle.privacyideaServers:privacyIDEA servers`,
  caConnectors: $localize`:@@pageTitle.caConnectors:CA connectors`,
  tokengroups: $localize`:@@pageTitle.tokengroups:Token groups`,
  serviceIds: $localize`:@@pageTitle.serviceIds:Service IDs`
};

// The title of the page that creates a record of the list called `base`.
export function newTitle(base: string): string {
  return $localize`:@@pageTitle.new:${base}:PAGE: – new`;
}

// The title of the page that shows one record of the list called `base`.
export function detailsTitle(base: string): string {
  return $localize`:@@pageTitle.details:${base}:PAGE: – details`;
}
