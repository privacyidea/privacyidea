import { Component, HostListener } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from './services/auth/auth.service';
import { NotificationService } from './services/notification/notification.service';
import { SessionTimerService } from './services/session-timer/session-timer.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'privacyidea-webui';

  constructor(
    private authService: AuthService,
    private notificationService: NotificationService,
    private sessionTimerService: SessionTimerService,
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
    this.sessionTimerService.resetTimer();
    this.sessionTimerService.startTimer();
  }
}
