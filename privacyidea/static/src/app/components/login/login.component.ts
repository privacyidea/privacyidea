import {Component, signal} from '@angular/core';
import {AuthService} from '../../services/auth/auth.service';
import {Router} from '@angular/router';
import {FormsModule} from '@angular/forms';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatIconModule} from '@angular/material/icon';
import {MatButton, MatFabButton} from '@angular/material/button';
import {NgOptimizedImage} from '@angular/common';
import {FooterComponent} from '../grid-layout/footer/footer.component';
import {LocalService} from '../../services/local/local.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  standalone: true,
  imports: [FormsModule, MatFormField, MatInput, MatButton, MatLabel, NgOptimizedImage, MatIconModule, MatFabButton, FooterComponent],
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username = signal<string>('');
  password = signal<string>('');
  private bearerTokenKey = 'bearer_token';

  constructor(private authService: AuthService, private router: Router, private localStore: LocalService) {
  }

  onSubmit() {
    const usernameValue = this.username();
    const passwordValue = this.password();

    this.authService.authenticate(usernameValue, passwordValue).subscribe({
      next: (response: any) => {
        if (response.result && response.result.value && response.result.value.token
          && this.authService.isAuthenticatedUser()) {
          this.localStore.saveData(this.bearerTokenKey, response.result.value.token);
          this.router.navigate(['token']);
        } else {
          console.warn('Login failed. Challenge response required.');
        }
      }, error: (error: any) => {
        console.error('Login failed', error);
      }
    });
  }

  logout(): void {
    this.localStore.removeData(this.bearerTokenKey);
    this.authService.deauthenticate();
  }
}
