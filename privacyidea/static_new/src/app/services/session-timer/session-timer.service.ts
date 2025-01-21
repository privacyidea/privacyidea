import {computed, effect, Injectable, signal} from '@angular/core';
import {Router} from '@angular/router';
import {NotificationService} from '../notification/notification.service';
import {LocalService} from '../local/local.service';
import {AuthService} from '../auth/auth.service';

@Injectable({
  providedIn: 'root'
})
export class SessionTimerService {
  private timer: any;
  private intervalId: any;
  private startTime = signal(Date.now());
  private currentTime = signal(Date.now());
  private readonly sessionTimeout = 3570_000;
  remainingTime = computed(() => this.sessionTimeout - (this.currentTime() - this.startTime()));

  constructor(private router: Router,
              private notificationService: NotificationService,
              private localService: LocalService,
              private authService: AuthService) {
    effect(() => {
      if (this.remainingTime() > 29_000 && this.remainingTime() < 30_000) {
        this.notificationService.openSnackBar('Session will expire in 30 seconds.');
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
    this.notificationService.openSnackBar('Session expired. Redirecting to login page.');
    this.router.navigate(['login']);
    this.clearRefreshInterval();
  }

  private clearRefreshInterval() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }
}
