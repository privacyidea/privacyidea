import {Component} from '@angular/core';
import {RouterOutlet} from '@angular/router';
import {FormsModule} from '@angular/forms';
import {AuthService} from './services/auth/auth.service';
import {NotificationService} from './services/notification/notification.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  constructor(private authService: AuthService,
              private notificationService: NotificationService) {
    if (this.authService.isAuthenticatedUser()) {
      console.warn('User is already logged in.');
      this.notificationService.openSnackBar('User is already logged in.');
    }
  }

  title = 'privacyidea-webui';
}
