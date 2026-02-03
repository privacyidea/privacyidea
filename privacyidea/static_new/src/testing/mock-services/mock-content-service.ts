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
import { computed, signal, WritableSignal } from "@angular/core";
import { Router } from "@angular/router";
import { ContentServiceInterface } from "../../app/services/content/content.service";

export class MockContentService implements ContentServiceInterface {
  detailsUsername = signal("");
  router: Router = {} as Router;
  routeUrl = signal("");
  previousUrl = signal("");
  tokenSerial = signal("");
  containerSerial = signal("");

  onLogin = computed(() => false);
  onAudit = computed(() => false);
  onTokens = computed(() => false);
  onUsers = computed(() => false);
  onPolicies = computed(() => false);
  onTokenDetails = computed(() => false);
  onUserDetails = computed(() => false);
  onUserRealms = computed(() => false);
  onTokensEnrollment = computed(() => false);
  onTokensChallenges = computed(() => false);
  onTokensApplications = computed(() => false);
  onTokensGetSerial = computed(() => false);
  onTokensImport = computed(() => false);
  onTokensContainers = computed(() => false);
  onTokensContainersCreate = computed(() => false);
  onTokensContainersDetails = computed(() => false);
  onTokensAssignToken = computed(() => false);
  onTokensWizard = computed(() => false);
  onTokensContainersWizard = computed(() => false);
  onAnyTokensRoute = computed(() => false);
  onAnyUsersRoute = computed(() => false);
  onTokensContainersTemplates = computed(() => false);

  tokenSelected = jest.fn();
  containerSelected = jest.fn();
  userSelected = jest.fn();
}
