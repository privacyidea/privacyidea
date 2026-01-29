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
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { NavigationEnd, Router } from "@angular/router";
import { filter, map, pairwise, startWith } from "rxjs";
import { ROUTE_PATHS } from "../../route_paths";

export interface ContentServiceInterface {
  detailsUsername: WritableSignal<string>;
  router: Router;
  routeUrl: Signal<string>;
  previousUrl: Signal<string>;
  tokenSerial: WritableSignal<string>;
  containerSerial: WritableSignal<string>;

  onLogin: Signal<boolean>;
  onAudit: Signal<boolean>;
  onTokens: Signal<boolean>;
  onUsers: Signal<boolean>;
  onPolicies: Signal<boolean>;
  onTokenDetails: Signal<boolean>;
  onUserDetails: Signal<boolean>;
  onUserRealms: Signal<boolean>;
  onTokensEnrollment: Signal<boolean>;
  onTokensChallenges: Signal<boolean>;
  onTokensApplications: Signal<boolean>;
  onTokensGetSerial: Signal<boolean>;
  onTokensImport: Signal<boolean>;
  onTokensContainers: Signal<boolean>;
  onTokensContainersCreate: Signal<boolean>;
  onTokensContainersDetails: Signal<boolean>;
  onTokensAssignToken: Signal<boolean>;
  onTokensWizard: Signal<boolean>;
  onTokensContainersWizard: Signal<boolean>;
  onAnyTokensRoute: Signal<boolean>;
  onAnyUsersRoute: Signal<boolean>;
  onTokensContainersTemplates: Signal<boolean>;
  onSubscription: Signal<boolean>;

  tokenSelected: (serial: string) => void;
  containerSelected: (containerSerial: string) => void;
  userSelected: (username: string, realm: string) => void;
}

@Injectable({ providedIn: "root" })
export class ContentService implements ContentServiceInterface {
  detailsUsername = signal("");
  router = inject(Router);
  private readonly _urlPair = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
      pairwise()
    ),
    { initialValue: [this.router.url, this.router.url] as const }
  );
  readonly routeUrl = computed(() => this._urlPair()[1]);
  readonly previousUrl = computed(() => this._urlPair()[0]);
  tokenSerial = signal("");
  containerSerial = signal("");
  onLogin = computed(() => this.routeUrl() === ROUTE_PATHS.LOGIN);
  onAudit = computed(() => this.routeUrl() === ROUTE_PATHS.AUDIT);
  onTokens = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS);
  onUsers = computed(() => this.routeUrl() === ROUTE_PATHS.USERS);
  onPolicies = computed(() => this.routeUrl() === ROUTE_PATHS.POLICIES);
  onTokenDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS));
  onUserDetails = computed(() => this.routeUrl().startsWith(ROUTE_PATHS.USERS_DETAILS + "/"));
  onUserRealms = computed(() => this.routeUrl() === ROUTE_PATHS.USERS_REALMS);
  onTokensEnrollment = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_ENROLLMENT);
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
  onAnyTokensRoute = computed(
    () => this.routeUrl() === ROUTE_PATHS.TOKENS || this.routeUrl().startsWith(ROUTE_PATHS.TOKENS + "/")
  );
  onAnyUsersRoute = computed(
    () => this.routeUrl() === ROUTE_PATHS.USERS || this.routeUrl().startsWith(ROUTE_PATHS.USERS + "/")
  );
  onTokensContainersTemplates = computed(() => this.routeUrl() === ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES);
  onSubscription = computed(() => this.routeUrl() === ROUTE_PATHS.SUBSCRIPTION);

  tokenSelected(serial: string): void {
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string): void {
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
    this.containerSerial.set(containerSerial);
  }

  userSelected(username: string, realm: string): void {
    this.router.navigateByUrl(ROUTE_PATHS.USERS_DETAILS + "/" + username + `?realm=${encodeURIComponent(realm ?? "")}`);
    this.detailsUsername.set(username);
  }
}
