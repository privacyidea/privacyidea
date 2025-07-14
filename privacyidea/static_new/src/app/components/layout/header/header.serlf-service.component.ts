import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { Component } from '@angular/core';
import {
  MatFabAnchor,
  MatFabButton,
  MatIconButton,
} from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenu, MatMenuTrigger } from '@angular/material/menu';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../services/auth/auth.service';
import { LocalService } from '../../../services/local/local.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { SessionTimerService } from '../../../services/session-timer/session-timer.service';
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
    protected override sessionTimerService: SessionTimerService,
    protected override authService: AuthService,
    protected override localService: LocalService,
    protected override notificationService: NotificationService,
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
