import { Component, HostListener, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterOutlet } from '@angular/router';
import {
  AuthService,
  AuthServiceInterface,
} from './services/auth/auth.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from './services/notification/notification.service';
import {
  SessionTimerService,
  SessionTimerServiceInterface,
} from './services/session-timer/session-timer.service';

export interface PiResponse<Value, Detail = unknown> {
  id: number;
  jsonrpc: string;
  detail: Detail;
  result?: {
    authentication?: 'CHALLENGE' | 'POLL' | 'PUSH';
    status: boolean;
    value?: Value;
    error?: {
      code: number;
      message: string;
    };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'privacyidea-webui';
  lastSessionReset = 0;

  constructor(
    @Inject(AuthService)
    private readonly authService: AuthServiceInterface,
    @Inject(NotificationService)
    private readonly notificationService: NotificationServiceInterface,
    @Inject(SessionTimerService)
    private readonly sessionTimerService: SessionTimerServiceInterface,
  ) {
    this.sessionTimerService.startTimer();

    if (this.authService.isAuthenticatedUser()) {
      console.warn('User is already logged in.');
      this.notificationService.openSnackBar('User is already logged in.');
    }
  }

  @HostListener('document:click')
  @HostListener('document:keydown')
  @HostListener('document:mousemove')
  @HostListener('document:scroll')
  resetSessionTimer() {
    const now = Date.now();
    if (now - this.lastSessionReset >= 1000) {
      this.lastSessionReset = now;
      this.sessionTimerService.resetTimer();
      this.sessionTimerService.startTimer();
    }
  }
}
