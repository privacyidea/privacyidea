import { Component, signal } from '@angular/core';
import { AuthService } from '../../services/auth/auth.service';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { NgOptimizedImage } from '@angular/common';
import { FooterComponent } from '../layout/footer/footer.component';
import { LocalService } from '../../services/local/local.service';
import { NotificationService } from '../../services/notification/notification.service';
import { SessionTimerService } from '../../services/session-timer/session-timer.service';
import { ValidateService } from '../../services/validate/validate.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    NgOptimizedImage,
    MatIconModule,
    MatFabButton,
    FooterComponent,
  ],
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  username = signal<string>('');
  password = signal<string>('');

  constructor(
    private authService: AuthService,
    private router: Router,
    private localService: LocalService,
    private notificationService: NotificationService,
    private sessionTimerService: SessionTimerService,
    private validateService: ValidateService,
  ) {
    if (this.authService.isAuthenticatedUser()) {
      console.warn('User is already logged in.');
      this.notificationService.openSnackBar('User is already logged in.');
    }
  }

  onSubmit() {
    const username = this.username();
    const password = this.password();

    this.authService.authenticate({ username, password }).subscribe({
      next: (response) => {
        if (
          response.result &&
          response.result?.value &&
          response.result?.value.token &&
          this.authService.isAuthenticatedUser()
        ) {
          this.localService.saveData(
            this.localService.bearerTokenKey,
            response.result?.value.token,
          );
          this.sessionTimerService.startRefreshingRemainingTime();
          this.sessionTimerService.startTimer();
          this.router.navigate(['token']).then();
          this.notificationService.openSnackBar('Login successful.');
        } else {
          console.error('Login failed. Challenge response required.');
          this.notificationService.openSnackBar(
            'Login failed. Challenge response required.',
          );
        }
      },
    });
  }

  logout(): void {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.router
      .navigate(['login'])
      .then(() => this.notificationService.openSnackBar('Logout successful.'));
  }

  loginPasskey(): void {
    this.validateService.authenticatePasskey().subscribe({
      next: (response) => {
        if (
          response.result &&
          response.result.value &&
          response.result.value.token &&
          this.authService.isAuthenticatedUser()
        ) {
          this.localService.saveData(
            this.localService.bearerTokenKey,
            response.result?.value.token,
          );
          this.sessionTimerService.startRefreshingRemainingTime();
          this.sessionTimerService.startTimer();
          this.router.navigate(['token']).then();
          this.notificationService.openSnackBar('Login successful.');
        } else {
          this.notificationService.openSnackBar('Login with passkey failed.');
        }
      },
      error: (err: any) => {
        console.error('Error during Passkey login', err);
        this.notificationService.openSnackBar(
          err?.message || 'Error during Passkey login',
        );
      },
    });
  }
}
