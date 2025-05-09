import { inject, Injectable } from '@angular/core';
import {
  CanActivate,
  CanActivateChild,
  CanMatchFn,
  Route,
  Router,
  UrlSegment,
} from '@angular/router';
import { AuthService } from '../services/auth/auth.service';
import { NotificationService } from '../services/notification/notification.service';

export const adminMatch: CanMatchFn = () =>
  inject(AuthService).role() === 'admin';

export const selfServiceMatch: CanMatchFn = () =>
  inject(AuthService).role() === 'user';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate, CanActivateChild {
  constructor(
    private authService: AuthService,
    private router: Router,
    private notificationService: NotificationService,
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
