import { Component } from '@angular/core';
import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { MatFabAnchor, MatFabButton } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';
import { SessionTimerService } from '../../../services/session-timer/session-timer.service';
import { AuthService } from '../../../services/auth/auth.service';

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
    protected sessionTimerService: SessionTimerService,
    protected authService: AuthService,
    private router: Router,
  ) {}

  isActive(link: string) {
    return this.router.url.includes(link);
  }

  refreshPage() {
    window.location.reload();
  }
}
