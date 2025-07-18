import {
  computed,
  effect,
  inject,
  Injectable,
  Signal,
  signal,
} from '@angular/core';
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
  private readonly router: Router = inject(Router);
  private readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  private readonly sessionTimeout = 3570_000;
  private timer: any;
  private intervalId: any;
  private startTime = signal(Date.now());
  private currentTime = signal(Date.now());
  remainingTime = computed(
    () => this.sessionTimeout - (this.currentTime() - this.startTime()),
  );

  constructor() {
    effect(() => {
      if (this.remainingTime() > 30_000 && this.remainingTime() < 31_000) {
        this.notificationService.openSnackBar(
          'Session will expire in 30 seconds.',
        );
      }
    });
  }

  startTimer(): void {
    this.resetTimer();
    this.startTime.set(Date.now());
    this.timer = setTimeout(() => {
      this.handleSessionTimeout();
    }, this.sessionTimeout);
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
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.notificationService.openSnackBar(
      'Session expired. Redirecting to login page.',
    );
    this.router.navigate(['login']);
    this.clearRefreshInterval();
  }

  private clearRefreshInterval(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }
}
