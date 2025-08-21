import { computed, effect, inject, Injectable, Signal, signal } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { LocalService, LocalServiceInterface } from "../local/local.service";
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
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  private readonly sessionTimeoutMs = computed<number | undefined>(() => {
    const logoutTimeSeconds = this.authService.logoutTimeSeconds();
    if (logoutTimeSeconds) {
      return logoutTimeSeconds * 1_000;
    }
    return;
  });
  private timer: any;
  private intervalId: any;
  private startTime = signal(Date.now());
  private currentTime = signal(Date.now());
  remainingTime = computed(() => {
    const sessionTimeoutMs = this.sessionTimeoutMs();
    if (sessionTimeoutMs) {
      return sessionTimeoutMs - (this.currentTime() - this.startTime());
    }
    return;
  });

  constructor() {
    effect(() => {
      const remainingTime = this.remainingTime();
      if (remainingTime && remainingTime > 30_000 && remainingTime < 31_000) {
        this.notificationService.openSnackBar("Session will expire in 30 seconds.");
      }
    });
  }

  startTimer(): void {
    this.resetTimer();
    this.startTime.set(Date.now());
    const sessionTimeoutMs = this.sessionTimeoutMs();
    if (sessionTimeoutMs) {
      this.timer = setTimeout(() => {
        this.handleSessionTimeout();
      }, this.sessionTimeoutMs());
    } else {
      this.timer?.clear();
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

  private handleSessionTimeout(): void {
    this.authService.deauthenticate();
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
