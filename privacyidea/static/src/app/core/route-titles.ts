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
  dashboard: $localize`:@@common.dashboard:Dashboard`,
  settings: $localize`:@@pageTitle.settings:UI Settings`,
  audit: $localize`:@@pageTitle.audit:Audit Log`,
  news: $localize`:@@common.news:News`,
  clients: $localize`:@@pageTitle.clients:Clients`,
  authenticationLog: $localize`:@@pageTitle.authenticationLog:Authentication Log`,
  lockedUsers: $localize`:@@pageTitle.lockedUsers:Locked Users`,
  blocklist: $localize`:@@pageTitle.blocklist:Blocklist`,
  tokens: $localize`:@@common.tokens:Tokens`,
  challenges: $localize`:@@pageTitle.challenges:Token Challenges`,
  applications: $localize`:@@pageTitle.applications:Token Applications`,
  getSerial: $localize`:@@pageTitle.getSerial:Find a Token Serial`,
  importTokens: $localize`:@@pageTitle.importTokens:Import Tokens`,
  enrollToken: $localize`:@@pageTitle.enrollToken:Enroll a Token`,
  assignToken: $localize`:@@pageTitle.assignToken:Assign a Token`,
  tokenWizard: $localize`:@@pageTitle.tokenWizard:Token Enrollment Wizard`,
  containers: $localize`:@@pageTitle.containers:Containers`,
  containerTemplates: $localize`:@@common.containerTemplates:Container Templates`,
  containerWizard: $localize`:@@pageTitle.containerWizard:Container Creation Wizard`,
  users: $localize`:@@common.users:Users`,
  realms: $localize`:@@common.realms:Realms`,
  resolvers: $localize`:@@common.resolvers:Resolvers`,
  policies: $localize`:@@common.policies:Policies`,
  conditionalAccess: $localize`:@@common.conditionalAccess:Conditional Access Policies`,
  apiClients: $localize`:@@common.apiClients:API Clients`,
  events: $localize`:@@common.eventHandlers:Event Handlers`,
  machineResolvers: $localize`:@@pageTitle.machineResolvers:Machine Resolvers`,
  machines: $localize`:@@common.machines:Machines`,
  periodicTasks: $localize`:@@common.periodicTasks:Periodic Tasks`,
  system: $localize`:@@pageTitle.system:System Configuration`,
  tokenTypes: $localize`:@@pageTitle.tokenTypes:Token Type Configuration`,
  subscription: $localize`:@@common.subscription:Subscription`,
  smtp: $localize`:@@common.smtpServers:SMTP Servers`,
  radius: $localize`:@@common.radiusServers:RADIUS Servers`,
  sms: $localize`:@@common.smsGateways:SMS Gateways`,
  privacyideaServers: $localize`:@@common.privacyideaServers:privacyIDEA Servers`,
  caConnectors: $localize`:@@common.caConnectors:CA Connectors`,
  tokengroups: $localize`:@@common.tokengroups:Token Groups`,
  serviceIds: $localize`:@@common.serviceIds:Service IDs`
};

// The title of the page that creates a record of the list called `base`.
export function newTitle(base: string): string {
  return $localize`:@@pageTitle.new:${base}:PAGE: - New`;
}

// The title of the page that shows one record of the list called `base`.
export function detailsTitle(base: string): string {
  return $localize`:@@pageTitle.details:${base}:PAGE: - Details`;
}
