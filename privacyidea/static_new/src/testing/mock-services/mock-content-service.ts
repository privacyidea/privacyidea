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
  onLogin = computed(() => this.routeUrl() === "/login");
  onAudit = computed(() => this.routeUrl() === "/audit");
  onTokens = computed(() => this.routeUrl() === "/tokens");
  onUsers = computed(() => this.routeUrl() === "/users");
  onPolicies = computed(() => this.routeUrl() === "/policies");
  onTokenDetails = computed(() => this.routeUrl().startsWith("/tokens/details"));
  onUserDetails = computed(() => this.routeUrl().startsWith("/users/details"));
  onUserRealms = computed(() => this.routeUrl() === "/users/realms");
  onTokensEnrollment = computed(() => this.routeUrl() === "/tokens/enrollment");
  onTokensChallenges = computed(() => this.routeUrl() === "/tokens/challenges");
  onTokensApplications = computed(() => this.routeUrl() === "/tokens/applications");
  onTokensGetSerial = computed(() => this.routeUrl() === "/tokens/get_serial");
  onTokensImport = computed(() => this.routeUrl() === "/tokens/import");
  onTokensContainers = computed(() => this.routeUrl() === "/tokens/containers");
  onTokensContainersCreate = computed(() => ["/tokens/containers/create", "/tokens/containers/wizard"].includes(this.routeUrl()));
  onTokensContainersDetails = computed(() => this.routeUrl().startsWith("/tokens/containers/details"));
  onTokensAssignToken = computed(() => this.routeUrl() === "/tokens/assign_token");
  onTokensWizard = computed(() => this.routeUrl() === "/tokens/wizard");
  onTokensContainersWizard = computed(() => this.routeUrl() === "/tokens/containers/wizard");
  onAnyTokensRoute = computed(() => this.routeUrl() === "/tokens" || this.routeUrl().startsWith("/tokens/"));
  onAnyUsersRoute = computed(() => this.routeUrl() === "/users" || this.routeUrl().startsWith("/users/"));
  onTokensContainersTemplates: WritableSignal<boolean> = signal(false);
  onEvents = computed(() => this.routeUrl() === "/events");
  onConfigurationSystem: Signal<boolean> = computed(() => this.routeUrl() === ROUTE_PATHS.CONFIGURATION_SYSTEM);
  tokenSelected = jest.fn();
  containerSelected = jest.fn();
  userSelected = jest.fn();
}
