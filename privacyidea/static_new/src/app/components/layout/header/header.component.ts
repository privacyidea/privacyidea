import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { Component, inject } from '@angular/core';
import {
  MatFabAnchor,
  MatFabButton,
  MatIconButton,
} from '@angular/material/button';

import { MatIconModule } from '@angular/material/icon';
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
import { ContentService } from '../../../services/content/content.service';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { ChallengesService } from '../../../services/token/challenges/challenges.service';
import { MachineService } from '../../../services/machine/machine.service';
import { UserService } from '../../../services/user/user.service';
import { AuditService } from '../../../services/audit/audit.service';

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
  private readonly contentService = inject(ContentService);
  private readonly tokenService = inject(TokenService);
  private readonly containerService = inject(ContainerService);
  private readonly challengeService = inject(ChallengesService);
  private readonly machineService = inject(MachineService);
  private readonly userService = inject(UserService);
  private readonly auditService = inject(AuditService);
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
    if (this.contentService.routeUrl().startsWith('/tokens/details')) {
      this.tokenService.tokenDetailResource.reload();
      this.containerService.containerResource.reload();
    }
    if (
      this.contentService.routeUrl().startsWith('/tokens/containers/details')
    ) {
      this.containerService.containerDetailResource.reload();
      this.tokenService.tokenResource.reload();
    }
    switch (this.contentService.routeUrl()) {
      case '/tokens':
        this.tokenService.tokenResource.reload();
        break;
      case '/tokens/containers':
        this.containerService.containerResource.reload();
        break;
      case '/tokens/challenges':
        this.challengeService.challengesResource.reload();
        break;
      case '/tokens/applications':
        this.machineService.tokenApplicationResource.reload();
        break;
      case '/tokens/enroll':
        this.containerService.containerResource.reload();
        this.userService.usersResource.reload();
        break;
      case '/tokens/containers/create':
        this.userService.usersResource.reload();
        break;
      case '/audit':
        this.auditService.auditResource.reload();
        break;
      case '/users':
        this.userService.usersResource.reload();
        break;
    }
  }

  logout(): void {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.router
      .navigate(['login'])
      .then(() => this.notificationService.openSnackBar('Logout successful.'));
  }
}
