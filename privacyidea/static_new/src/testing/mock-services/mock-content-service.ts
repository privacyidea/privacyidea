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
  tokenSerial = signal("");
  containerSerial = signal("");
  machineResolver = signal("");

  onLogin = computed(() => this.routeUrl() === ROUTE_PATHS.LOGIN);
  onAudit = computed(() => this.routeUrl() === ROUTE_PATHS.AUDIT);
  onAuthenticationLog = computed(() => this.routeUrl() === ROUTE_PATHS.AUTHENTICATION_LOG);
  onClients = computed(() => this.routeUrl() === ROUTE_PATHS.CLIENTS);
  onTokens = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS);
  onUsers = computed(() => this.routeUrl() === ROUTE_PATHS.USERS);
  onPolicies = computed(() => this.routeUrl() === ROUTE_PATHS.POLICIES);
  onTokenDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS));
  onUserDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.USERS_DETAILS + "/"));
  onUserDetailsSelfService = computed(() => this.routeUrl() === ROUTE_PATHS.USERS_DETAILS);
  onUserRealms = computed(() => this.routeUrl() === ROUTE_PATHS.USERS_REALMS);
  onTokensEnrollment = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_ENROLLMENT);
  onTokenEnrollmentLikely = signal(false);
  onTokensChallenges = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CHALLENGES);
  onTokensApplications = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_APPLICATIONS);
  onTokensGetSerial = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_GET_SERIAL);
  onTokensImport = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_IMPORT);
  onContainers = computed(() => this.routeUrl() === ROUTE_PATHS.CONTAINERS);
  onContainersCreate = computed(() =>
    [ROUTE_PATHS.CONTAINERS_CREATE, ROUTE_PATHS.CONTAINERS_WIZARD].includes(this.routeUrl())
  );
  onContainersDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.CONTAINERS_DETAILS));
  onTokensAssignToken = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_ASSIGN_TOKEN);
  onTokensWizard = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_WIZARD);
  onContainersWizard = computed(() => this.routeUrl() === ROUTE_PATHS.CONTAINERS_WIZARD);
  onAnyTokensRoute = computed(
    () => this.routeUrl() === ROUTE_PATHS.TOKENS || this.routeUrl().startsWith(ROUTE_PATHS.TOKENS + "/")
  );
  onAnyUsersRoute = computed(
    () => this.routeUrl() === ROUTE_PATHS.USERS || this.routeUrl().startsWith(ROUTE_PATHS.USERS + "/")
  );
  onContainersTemplates: Signal<boolean> = computed(() => this.routeUrl() === ROUTE_PATHS.CONTAINERS_TEMPLATES);
  onContainersTemplatesCreate: Signal<boolean> = computed(
    () => this.routeUrl() === ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE
  );
  onContainersTemplatesDetails: Signal<boolean> = computed(() =>
    this.routeUrl().startsWith(ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS)
  );
  onAnyContainerTemplatesRoute = computed(
    () => this.onContainersTemplates() || this.onContainersTemplatesCreate() || this.onContainersTemplatesDetails()
  );
  onEvents = computed(() => this.routeUrl() === ROUTE_PATHS.EVENTS);
  onConfigurationSystem: Signal<boolean> = computed(() => this.routeUrl() === ROUTE_PATHS.CONFIGURATION_SYSTEM);
  onConfigurationTokenTypes: Signal<boolean> = computed(() => this.routeUrl() === ROUTE_PATHS.CONFIGURATION_TOKENTYPES);
  onConfigurationMachines = computed(() => this.routeUrl() === ROUTE_PATHS.CONFIGURATION_MACHINES);

  onExternalSmtp = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
  onExternalRadius = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
  onExternalSms = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
  onExternalCaConnectors = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
  onExternalPrivacyIdea = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
  onExternalTokenGroups = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS);
  onExternalServiceIds = computed(() => this.routeUrl() === ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS);
  onUsersResolvers = computed(() => this.routeUrl() === ROUTE_PATHS.USERS_RESOLVERS);
  onConfigurationPeriodicTasks = computed(() => this.routeUrl() === ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS);
  onSubscription = computed(() => this.routeUrl() === ROUTE_PATHS.SUBSCRIPTION);
  onMachineResolver = computed(() => this.routeUrl() === ROUTE_PATHS.MACHINE_RESOLVER);

  tokenSelected = jest.fn();
  navigateContainerDetails = jest.fn();
  userSelected = jest.fn();
  machineResolverSelected = jest.fn();
}
