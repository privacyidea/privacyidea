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

import { computed, signal, Signal } from "@angular/core";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContentServiceInterface } from "@services/content/content.service";

export class MockContentService implements ContentServiceInterface {
  detailsUser = signal({ username: "", realm: "" });
  router: Router = {} as Router;
  routeUrl = signal("");
  previousUrl = signal("");
  queryParams = signal<Record<string, string>>({});
  tokenSerial = signal("");
  containerSerial = signal("");
  machineResolver = signal("");

  onLogin = computed(() => this.matchesPath(ROUTE_PATHS.LOGIN));
  onAudit = computed(() => this.matchesPath(ROUTE_PATHS.AUDIT));
  onClients = computed(() => this.matchesPath(ROUTE_PATHS.CLIENTS));
  onTokens = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS));
  onUsers = computed(() => this.matchesPath(ROUTE_PATHS.USERS));
  onPolicies = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.POLICIES));
  onTokenDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS));
  onUserDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.USERS_DETAILS + "/"));
  onUserDetailsSelfService = computed(() => this.matchesPath(ROUTE_PATHS.USERS_DETAILS));
  onUserRealms = computed(() => this.matchesPath(ROUTE_PATHS.USERS_REALMS));
  onTokensEnrollment = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_ENROLLMENT));
  onTokenEnrollmentLikely = signal(false);
  onTokensChallenges = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_CHALLENGES));
  onTokensApplications = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_APPLICATIONS));
  onTokensGetSerial = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_GET_SERIAL));
  onTokensImport = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_IMPORT));
  onContainers = computed(() => this.matchesPath(ROUTE_PATHS.CONTAINERS));
  onContainersCreate = computed(
    () => this.matchesPath(ROUTE_PATHS.CONTAINERS_CREATE) || this.matchesPath(ROUTE_PATHS.CONTAINERS_WIZARD)
  );
  onContainersDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.CONTAINERS_DETAILS));
  onTokensAssignToken = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_ASSIGN_TOKEN));
  onTokensWizard = computed(() => this.matchesPath(ROUTE_PATHS.TOKENS_WIZARD));
  onContainersWizard = computed(() => this.matchesPath(ROUTE_PATHS.CONTAINERS_WIZARD));
  onAnyTokensRoute = computed(
    () => this.matchesPath(ROUTE_PATHS.TOKENS) || this.routeUrl().startsWith(ROUTE_PATHS.TOKENS + "/")
  );
  onAnyUsersRoute = computed(
    () => this.matchesPath(ROUTE_PATHS.USERS) || this.routeUrl().startsWith(ROUTE_PATHS.USERS + "/")
  );
  onContainersTemplates: Signal<boolean> = computed(() => this.matchesPath(ROUTE_PATHS.CONTAINERS_TEMPLATES));
  onContainersTemplatesCreate: Signal<boolean> = computed(() =>
    this.matchesPath(ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE)
  );
  onContainersTemplatesDetails: Signal<boolean> = computed(() =>
    this.routeUrl().startsWith(ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS)
  );
  onAnyContainerTemplatesRoute = computed(
    () => this.onContainersTemplates() || this.onContainersTemplatesCreate() || this.onContainersTemplatesDetails()
  );
  onEvents = computed(() => this.matchesPath(ROUTE_PATHS.EVENTS));
  onConfigurationSystem: Signal<boolean> = computed(() => this.matchesPath(ROUTE_PATHS.CONFIGURATION_SYSTEM));
  onConfigurationTokenTypes: Signal<boolean> = computed(() => this.matchesPath(ROUTE_PATHS.CONFIGURATION_TOKENTYPES));
  onConfigurationMachines = computed(() => this.matchesPath(ROUTE_PATHS.CONFIGURATION_MACHINES));

  onExternalSmtp = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP));
  onExternalRadius = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS));
  onExternalSms = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_SMS));
  onExternalCaConnectors = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS));
  onExternalPrivacyIdea = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA));
  onExternalTokenGroups = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS));
  onExternalServiceIds = computed(() => this.matchesPath(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS));
  onUsersResolvers = computed(() => this.matchesPath(ROUTE_PATHS.USERS_RESOLVERS));
  onConfigurationPeriodicTasks = computed(() => this.matchesPath(ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS));
  onSubscription = computed(() => this.matchesPath(ROUTE_PATHS.SUBSCRIPTION));
  onMachineResolver = computed(() => this.matchesPath(ROUTE_PATHS.MACHINE_RESOLVER));

  private matchesPath(path: string): boolean {
    const url = this.routeUrl();
    return url === path || url.startsWith(path + "?");
  }

  tokenSelected = jest.fn();
  navigateContainerDetails = jest.fn();
  userSelected = jest.fn();
  machineResolverSelected = jest.fn();
}
