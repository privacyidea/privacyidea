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

  private readonly sessionTimeoutMs = computed<number | undefined>(() => {
    const logoutTimeSeconds = this.authService.logoutTimeSeconds();
    if (logoutTimeSeconds) {
      return logoutTimeSeconds * 1_000;
    }
    return;
  });
  private timer: NodeJS.Timeout | undefined;
  private intervalId: NodeJS.Timeout | undefined;
  private startTime = signal(Date.now());
  private currentTime = signal(Date.now());
  remainingTime = computed(() => {
    const sessionTimeoutMs = this.sessionTimeoutMs();
    if (sessionTimeoutMs) {
      return sessionTimeoutMs - (this.currentTime() - this.startTime());
    }
    return;
  });

  startTimer(): void {
    this.resetTimer();
    this.startTime.set(Date.now());
    const sessionTimeoutMs = this.sessionTimeoutMs();
    if (sessionTimeoutMs) {
      this.timer = setTimeout(() => {
        this.handleSessionTimeout();
      }, this.sessionTimeoutMs());
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
    this.authService.logout();
    this.notificationService.openSnackBar("Session expired. Redirecting to login page.");
    this.router.navigate(["login"]);
    this.clearRefreshInterval();
  }

  private clearRefreshInterval(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }
}
