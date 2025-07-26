import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { Component, inject } from '@angular/core';
import {
  MatFabAnchor,
  MatFabButton,
  MatIconButton,
} from '@angular/material/button';

import { MatIconModule } from '@angular/material/icon';
import { MatMenu, MatMenuTrigger } from '@angular/material/menu';
import { Router, RouterLink } from '@angular/router';
import {
  AuthService,
  AuthServiceInterface,
} from '../../../services/auth/auth.service';
import {
  LocalService,
  LocalServiceInterface,
} from '../../../services/local/local.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../../../services/notification/notification.service';
import {
  SessionTimerService,
  SessionTimerServiceInterface,
} from '../../../services/session-timer/session-timer.service';
import { ThemeSwitcherComponent } from '../../shared/theme-switcher/theme-switcher.component';
import { UserSelfServiceComponent } from '../../user/user.self-service.component';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    NgOptimizedImage,
    MatFabButton,
    MatFabAnchor,
    MatIconModule,
    RouterLink,
    DatePipe,
    NgClass,
    MatIconButton,
    MatMenuTrigger,
    MatMenu,
    UserSelfServiceComponent,
    ThemeSwitcherComponent,
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderComponent {
  protected readonly sessionTimerService: SessionTimerServiceInterface =
    inject(SessionTimerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly localService: LocalServiceInterface = inject(LocalService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected readonly router: Router = inject(Router);

  protected readonly AuthService = AuthService;
  profileText =
    this.authService.user() +
    ' @' +
    this.authService.realm() +
    ' (' +
    this.authService.role() +
    ')';

  isActive(link: string) {
    return this.router.url.includes(link);
  }

  refreshPage() {
    window.location.reload();
  }

  logout(): void {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.router
      .navigate(['login'])
      .then(() => this.notificationService.openSnackBar('Logout successful.'));
  }
}
