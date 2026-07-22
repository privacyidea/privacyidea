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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { Observable, of } from "rxjs";
import { catchError, map } from "rxjs/operators";

export interface UserLockoutStatus {
  resolver: string;
  uid: string;
  realm: string;
  username: string;
  permanent: boolean;
  lock_expires_at: string | null;
  seconds_remaining: number | null;
  is_locked: boolean;
  last_updated: string;
}

export type ResetUserLockoutRequest =
  | {
      uid: string;
      realm: string;
      resolver: string;
    }
  | {
      login: string;
      realm: string;
      resolver: string;
    };

export interface ConditionalAccessStateServiceInterface {
  userLockoutResource: HttpResourceRef<PiResponse<UserLockoutStatus | null> | undefined>;
  userLockoutStatus: Signal<UserLockoutStatus | null>;
  resetUserLockout(request: ResetUserLockoutRequest): Observable<boolean>;
}

@Injectable()
export class ConditionalAccessStateService implements ConditionalAccessStateServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  private readonly conditionalAccessBaseUrl = environment.proxyUrl + "/conditionalaccess/";

  private readonly canReadUserLockout = computed(() => this.authService.actionAllowed("user_lockout_read"));

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.userLockoutResource.error(), "user lockout state");
    });
  }

  userLockoutResource = httpResource<PiResponse<UserLockoutStatus | null>>(() => {
    if (!this.contentService.onUserDetails() || !this.canReadUserLockout()) {
      return undefined;
    }
    const selectedUser = this.contentService.detailsUser();
    if (!selectedUser.username || !selectedUser.realm) {
      return undefined;
    }
    const resolver = this.userService.user().resolver;
    const params: Record<string, string> = {
      user: selectedUser.username,
      realm: selectedUser.realm
    };
    if (resolver) {
      params["resolver"] = resolver;
    }
    return {
      url: this.conditionalAccessBaseUrl + "lockout/user",
      method: "GET",
      headers: this.authService.getHeaders(),
      params
    };
  });

  userLockoutStatus = computed<UserLockoutStatus | null>(() => {
    if (!this.userLockoutResource.hasValue()) {
      return null;
    }
    return this.userLockoutResource.value()?.result?.value ?? null;
  });

  resetUserLockout(request: ResetUserLockoutRequest): Observable<boolean> {
    const payload =
      "uid" in request
        ? { user_id: request.uid, realm: request.realm, resolver: request.resolver }
        : { user: request.login, realm: request.realm, resolver: request.resolver };

    return this.http
      .delete<PiResponse<boolean>>(this.conditionalAccessBaseUrl + "lockout/user", {
        headers: this.authService.getHeaders(),
        body: payload
      })
      .pipe(
        map((response) => response.result?.value ?? false),
        catchError((error) => {
          console.error("Failed to reset user lockout.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to reset user lockout. ` + message);
          return of(false);
        })
      );
  }
}
