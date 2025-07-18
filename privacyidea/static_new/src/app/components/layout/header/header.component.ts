import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { Component, Inject } from '@angular/core';
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
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderComponent {
  protected readonly AuthService = AuthService;
  profileText =
    this.authService.user() +
    ' @' +
    this.authService.realm() +
    ' (' +
    this.authService.role() +
    ')';

  constructor(
    @Inject(SessionTimerService)
    protected sessionTimerService: SessionTimerServiceInterface,
    @Inject(AuthService)
    protected authService: AuthServiceInterface,
    @Inject(LocalService)
    protected localService: LocalServiceInterface,
    @Inject(NotificationService)
    protected notificationService: NotificationServiceInterface,
    @Inject(Router)
    protected router: Router,
  ) {}

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
