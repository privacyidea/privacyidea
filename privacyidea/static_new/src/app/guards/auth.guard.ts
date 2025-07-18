import { Inject, inject, Injectable } from '@angular/core';
import {
  CanActivate,
  CanActivateChild,
  CanMatchFn,
  Router,
} from '@angular/router';
import {
  AuthService,
  AuthServiceInterface,
} from '../services/auth/auth.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../services/notification/notification.service';

export const adminMatch: CanMatchFn = () =>
  inject(AuthService).role() === 'admin';

export const selfServiceMatch: CanMatchFn = () =>
  inject(AuthService).role() === 'user';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate, CanActivateChild {
  constructor(
    private router: Router,
    @Inject(AuthService)
    private authService: AuthServiceInterface,
    @Inject(NotificationService)
    private notificationService: NotificationServiceInterface,
  ) {}

  canActivate(): boolean {
    return this.checkAuth();
  }

  canActivateChild(): boolean {
    return this.checkAuth();
  }

  private checkAuth(): boolean {
    if (this.authService.isAuthenticatedUser()) {
      return true;
    } else {
      this.router.navigate(['/login']).then((r) => {
        console.warn('Navigation blocked by AuthGuard!', r);
        this.notificationService.openSnackBar(
          'Navigation blocked by AuthGuard!',
        );
      });
      return false;
    }
  }
}
