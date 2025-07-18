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
import { HeaderComponent } from './header.component';

@Component({
  selector: 'app-header-self-service',
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
  templateUrl: './header.self-service.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderSelfServiceComponent extends HeaderComponent {
  constructor(
    @Inject(SessionTimerService)
    protected override sessionTimerService: SessionTimerServiceInterface,
    @Inject(AuthService)
    protected override authService: AuthServiceInterface,
    @Inject(LocalService)
    protected override localService: LocalServiceInterface,
    @Inject(NotificationService)
    protected override notificationService: NotificationServiceInterface,
    protected override router: Router,
  ) {
    super(
      sessionTimerService,
      authService,
      localService,
      notificationService,
      router,
    );
  }
}
