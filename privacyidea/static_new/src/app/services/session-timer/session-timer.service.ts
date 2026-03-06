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
import { computed, effect, inject, Injectable, Signal, signal } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";

export interface SessionTimerServiceInterface {
  remainingTime: Signal<number | undefined>;

  initialTimerStart(): void;

  startTimer(): void;

  resetTimer(): void;

  startRefreshingRemainingTime(): void;
}

@Injectable({
  providedIn: "root"
})
export class SessionTimerService implements SessionTimerServiceInterface {
  private readonly router: Router = inject(Router);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  private readonly authService: AuthServiceInterface = inject(AuthService);

  private readonly logoutTimeMs = computed(() => {
    // Logout time which can be refreshed by user activity
    let logoutTime = this.authService.logoutTimeS();
    if (logoutTime === null) return null;
    logoutTime *= 1_000;
    const offset = this.currentTime() - this.startTime();
    if (offset > 0) {
      // Initially, loginTime and startTime are set to the actual time which can cause a negative offset.
      logoutTime -= offset;
    }
    return Math.max(0, logoutTime);
  });

  private readonly jwtLogoutTimeMs = computed(() => {
    // Logout time based on JWT token expiration, cannot be refreshed by user activity
    let jwtLogoutTime = this.authService.jwtLogoutTimeS();
    if (jwtLogoutTime === null) return null;
    jwtLogoutTime *= 1_000;
    const offset = this.currentTime() - this.loginTime();
    if (offset > 0) {
      // Initially, loginTime and currentTime are set to the actual time which can cause a negative offset.
      jwtLogoutTime -= offset;
    }
    return Math.max(0, jwtLogoutTime);
  });

  private timer: NodeJS.Timeout | undefined;
  private intervalId: NodeJS.Timeout | undefined;
  private startTime = signal(Date.now());
  private loginTime = signal(Date.now());
  private currentTime = signal(Date.now());
  remainingTime = computed(() => {
    if (this.jwtLogoutTimeMs() == null && this.logoutTimeMs() == null) return;
    if (this.logoutTimeMs() == null) return this.jwtLogoutTimeMs() ?? undefined;
    if (this.jwtLogoutTimeMs() == null) return this.logoutTimeMs() ?? undefined;
    return Math.min(this.jwtLogoutTimeMs() ?? 0, this.logoutTimeMs() ?? 0);
  });

  initialTimerStart(): void {
    this.loginTime.set(Date.now());
    this.startRefreshingRemainingTime();
    this.startTimer();
  }

  startTimer(): void {
    this.resetTimer();
    this.startTime.set(Date.now());
    let sessionTimeoutMs = this.remainingTime();
    if (sessionTimeoutMs != null) {
      // Trigger logout slightly before the actual timeout to already open the notification and ensure the user sees it
      sessionTimeoutMs = Math.max(0, sessionTimeoutMs - 500);
      this.timer = setTimeout(() => {
        this.handleSessionTimeout();
      }, sessionTimeoutMs);
    } else {
      clearTimeout(this.timer);
      this.timer = undefined;
      console.warn("Session timeout is not defined. Cannot start session timer.");
    }
  }

  resetTimer(): void {
    if (this.timer) {
      clearTimeout(this.timer);
    }
  }

  startRefreshingRemainingTime(): void {
    this.intervalId = setInterval(() => {
      this.currentTime.set(Date.now());
    }, 1000);
  }

  constructor() {
    effect(() => {
      const remainingTime = this.remainingTime();
      if (remainingTime && remainingTime > 30_000 && remainingTime < 31_000) {
        this.notificationService.openSnackBar("Session will expire in 30 seconds.");
      }
    });
  }

  private handleSessionTimeout(): void {
    this.notificationService.openSnackBar(
      $localize`Your session has expired. You will be logged out and redirected to the login page.`);
    // Keep notification visible for 1.5s before logging out to ensure the user sees it
    setTimeout(() => {
      this.clearRefreshInterval();
      this.resetTimer();
      this.authService.logout();
    }, 1500);
  }

  private clearRefreshInterval(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }
}
