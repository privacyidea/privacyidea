import { computed, effect, Inject, Injectable, Signal, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService, AuthServiceInterface } from '../auth/auth.service';
import { LocalService, LocalServiceInterface } from '../local/local.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../notification/notification.service';

export interface SessionTimerServiceInterface {
  startTimer(): void;
  resetTimer(): void;
  startRefreshingRemainingTime(): void;
  remainingTime: Signal<number>;
}

@Injectable({
  providedIn: 'root',
})
export class SessionTimerService implements SessionTimerServiceInterface {
  private readonly sessionTimeout = 3570_000;
  private timer: any;
  private intervalId: any;
  private startTime = signal(Date.now());
  private currentTime = signal(Date.now());
  remainingTime = computed(
    () => this.sessionTimeout - (this.currentTime() - this.startTime()),
  );

  constructor(
    private readonly router: Router,
    @Inject(NotificationService)
    private readonly notificationService: NotificationServiceInterface,
    @Inject(LocalService)
    private readonly localService: LocalServiceInterface,
    @Inject(AuthService)
    private readonly authService: AuthServiceInterface,
  ) {
    effect(() => {
      if (this.remainingTime() > 30_000 && this.remainingTime() < 31_000) {
        this.notificationService.openSnackBar(
          'Session will expire in 30 seconds.',
        );
      }
    });
  }

  startTimer() {
    this.resetTimer();
    this.startTime.set(Date.now());
    this.timer = setTimeout(() => {
      this.handleSessionTimeout();
    }, this.sessionTimeout);
  }

  resetTimer() {
    if (this.timer) {
      clearTimeout(this.timer);
    }
  }

  startRefreshingRemainingTime() {
    this.intervalId = setInterval(() => {
      this.currentTime.set(Date.now());
    }, 1000);
  }

  private handleSessionTimeout() {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.notificationService.openSnackBar(
      'Session expired. Redirecting to login page.',
    );
    this.router.navigate(['login']);
    this.clearRefreshInterval();
  }

  private clearRefreshInterval() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }
}
