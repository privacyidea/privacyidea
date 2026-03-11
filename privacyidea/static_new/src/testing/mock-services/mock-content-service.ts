/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { computed, Signal, signal, WritableSignal } from "@angular/core";
import { Router } from "@angular/router";
import { ContentServiceInterface } from "../../app/services/content/content.service";
import { ROUTE_PATHS } from "../../app/route_paths";

export class MockContentService implements ContentServiceInterface {
  detailsUsername = signal("");
  router: Router = {} as Router;
  routeUrl = signal("");
  previousUrl = signal("");
  tokenSerial = signal("");
  containerSerial = signal("");
  machineResolver = signal("");

  onLogin = computed(() => this.routeUrl() === ROUTE_PATHS.LOGIN);
  onAudit = computed(() => this.routeUrl() === ROUTE_PATHS.AUDIT);
  onTokens = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS);
  onUsers = computed(() => this.routeUrl() === ROUTE_PATHS.USERS);
  onPolicies = computed(() => this.routeUrl() === ROUTE_PATHS.POLICIES);
  onTokenDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS));
  onUserDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.USERS_DETAILS + "/"));
  onUserRealms = computed(() => this.routeUrl() === ROUTE_PATHS.USERS_REALMS);
  onTokensEnrollment = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_ENROLLMENT);
  onTokenEnrollmentLikely = signal(false);
  onTokensChallenges = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CHALLENGES);
  onTokensApplications = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_APPLICATIONS);
  onTokensGetSerial = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_GET_SERIAL);
  onTokensImport = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_IMPORT);
  onTokensContainers = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CONTAINERS);
  onTokensContainersCreate = computed(() => [ROUTE_PATHS.TOKENS_CONTAINERS_CREATE, ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD].includes(this.routeUrl()));
  onTokensContainersDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS));
  onTokensAssignToken = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_ASSIGN_TOKEN);
  onTokensWizard = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_WIZARD);
  onTokensContainersWizard = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);
  onAnyTokensRoute = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS || this.routeUrl().startsWith(ROUTE_PATHS.TOKENS + "/"));
  onAnyUsersRoute = computed(() => this.routeUrl() === ROUTE_PATHS.USERS || this.routeUrl().startsWith(ROUTE_PATHS.USERS + "/"));
  onTokensContainersTemplates: Signal<boolean> = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES);
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
  onConfigurationSubscription = computed(() => this.routeUrl() === ROUTE_PATHS.SUBSCRIPTION);
  onMachineResolver = computed(() => this.routeUrl() === ROUTE_PATHS.MACHINE_RESOLVER);

  tokenSelected = jest.fn();
  containerSelected = jest.fn();
  userSelected = jest.fn();
  machineResolverSelected = jest.fn();
}
