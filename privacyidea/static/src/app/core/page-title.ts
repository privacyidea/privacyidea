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

import { LiveAnnouncer } from "@angular/cdk/a11y";
import { inject, Injectable, signal } from "@angular/core";
import { Title } from "@angular/platform-browser";
import { RouterStateSnapshot, TitleStrategy } from "@angular/router";
import { ROUTE_PATHS } from "../route_paths";

// The name of each page, matched against the path without its query. A page below one of these ("new", "create",
// "details/…") takes the page's name plus what it is.
function pageTitles(): [string, string][] {
  return [
    [ROUTE_PATHS.LOGIN, $localize`:@@pageTitle.login:Login`],
    [ROUTE_PATHS.DASHBOARD, $localize`:@@pageTitle.dashboard:Dashboard`],
    [ROUTE_PATHS.SETTINGS, $localize`:@@pageTitle.settings:UI settings`],
    [ROUTE_PATHS.AUDIT, $localize`:@@pageTitle.audit:Audit log`],
    [ROUTE_PATHS.NEWS, $localize`:@@pageTitle.news:News`],
    [ROUTE_PATHS.CLIENTS, $localize`:@@pageTitle.clients:Clients`],
    [ROUTE_PATHS.AUTHENTICATION_LOG, $localize`:@@pageTitle.authenticationLog:Authentication log`],
    [ROUTE_PATHS.LOCKED_USERS, $localize`:@@pageTitle.lockedUsers:Locked users`],
    [ROUTE_PATHS.BLOCKLIST, $localize`:@@pageTitle.blocklist:Blocklist`],
    [ROUTE_PATHS.TOKENS, $localize`:@@pageTitle.tokens:Tokens`],
    [ROUTE_PATHS.TOKENS_CHALLENGES, $localize`:@@pageTitle.challenges:Token challenges`],
    [ROUTE_PATHS.TOKENS_APPLICATIONS, $localize`:@@pageTitle.applications:Token applications`],
    [ROUTE_PATHS.TOKENS_GET_SERIAL, $localize`:@@pageTitle.getSerial:Find a token serial`],
    [ROUTE_PATHS.TOKENS_IMPORT, $localize`:@@pageTitle.importTokens:Import tokens`],
    [ROUTE_PATHS.TOKENS_ENROLLMENT, $localize`:@@pageTitle.enrollToken:Enroll a token`],
    [ROUTE_PATHS.TOKENS_ASSIGN_TOKEN, $localize`:@@pageTitle.assignToken:Assign a token`],
    [ROUTE_PATHS.TOKENS_WIZARD, $localize`:@@pageTitle.tokenWizard:Token enrollment wizard`],
    [ROUTE_PATHS.CONTAINERS, $localize`:@@pageTitle.containers:Containers`],
    [ROUTE_PATHS.CONTAINERS_TEMPLATES, $localize`:@@pageTitle.containerTemplates:Container templates`],
    [ROUTE_PATHS.CONTAINERS_WIZARD, $localize`:@@pageTitle.containerWizard:Container creation wizard`],
    [ROUTE_PATHS.USERS, $localize`:@@pageTitle.users:Users`],
    [ROUTE_PATHS.USERS_REALMS, $localize`:@@pageTitle.realms:Realms`],
    [ROUTE_PATHS.USERS_RESOLVERS, $localize`:@@pageTitle.resolvers:Resolvers`],
    [ROUTE_PATHS.POLICIES, $localize`:@@pageTitle.policies:Policies`],
    [ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS, $localize`:@@pageTitle.conditionalAccess:Conditional access policies`],
    [ROUTE_PATHS.POLICIES_API_CLIENTS, $localize`:@@pageTitle.apiClients:API clients`],
    [ROUTE_PATHS.EVENTS, $localize`:@@pageTitle.events:Event handlers`],
    [ROUTE_PATHS.MACHINE_RESOLVER, $localize`:@@pageTitle.machineResolvers:Machine resolvers`],
    [ROUTE_PATHS.CONFIGURATION_MACHINES, $localize`:@@pageTitle.machines:Machines`],
    [ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS, $localize`:@@pageTitle.periodicTasks:Periodic tasks`],
    [ROUTE_PATHS.CONFIGURATION_SYSTEM, $localize`:@@pageTitle.system:System configuration`],
    [ROUTE_PATHS.CONFIGURATION_TOKENTYPES, $localize`:@@pageTitle.tokenTypes:Token type configuration`],
    [ROUTE_PATHS.SUBSCRIPTION, $localize`:@@pageTitle.subscription:Subscription`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_SMTP, $localize`:@@pageTitle.smtp:SMTP servers`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS, $localize`:@@pageTitle.radius:RADIUS servers`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_SMS, $localize`:@@pageTitle.sms:SMS gateways`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA, $localize`:@@pageTitle.privacyideaServers:privacyIDEA servers`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS, $localize`:@@pageTitle.caConnectors:CA connectors`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS, $localize`:@@pageTitle.tokengroups:Token groups`],
    [ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS, $localize`:@@pageTitle.serviceIds:Service IDs`]
  ];
}

// The name of the page at `path`, or undefined for a path no page is known by.
export function pageTitleFor(path: string): string | undefined {
  const clean = path.split(/[?#]/)[0].replace(/\/+$/, "") || "/";
  const titles = new Map(pageTitles());
  const exact = titles.get(clean);
  if (exact) {
    return exact;
  }
  const detail = /^(.*)\/(new|create|details)(\/.*)?$/.exec(clean);
  const base = detail ? titles.get(detail[1]) : undefined;
  if (!detail || !base) {
    return undefined;
  }
  return detail[2] === "details"
    ? $localize`:@@pageTitle.details:${base}:PAGE: – details`
    : $localize`:@@pageTitle.new:${base}:PAGE: – new`;
}

/**
 * Names the page for whoever cannot see it: the document title, a heading the page itself does not draw, and a
 * polite announcement when the route changes (the page does not reload, so nothing else tells a screen reader that it
 * moved).
 */
@Injectable({ providedIn: "root" })
export class PageTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);
  private readonly announcer = inject(LiveAnnouncer);
  private readonly appTitle = this.title.getTitle();

  // The page's name, for the heading the app shell renders.
  readonly heading = signal("");

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const heading = pageTitleFor(snapshot.url) ?? "";
    this.heading.set(heading);
    this.title.setTitle(heading ? `${heading} – ${this.appTitle}` : this.appTitle);
    if (heading) {
      void this.announcer.announce(heading, "polite");
    }
  }
}
