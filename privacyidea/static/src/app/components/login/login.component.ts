import {Component} from '@angular/core';
import {AuthService} from '../../services/auth/auth.service';
import {Router} from '@angular/router';
import {FormsModule} from '@angular/forms';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatButton} from '@angular/material/button';
import {NgOptimizedImage} from '@angular/common';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  standalone: true,
  imports: [FormsModule, MatFormField, MatInput, MatButton, MatLabel, NgOptimizedImage],
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username: string = '';
  password: string = '';
  private authSecretKey = 'bearer_token';

  constructor(private authService: AuthService, private router: Router) {
  }

  onSubmit() {
    this.authService.authenticate(this.username, this.password).subscribe({
      next: (response: any) => {
        if (response.result && response.result.value && response.result.value.token
          && this.authService.isAuthenticatedUser()) {
          console.log('Login successful', response);
          localStorage.setItem(this.authSecretKey, response.result.value.token);
          this.router.navigate(['token']).then(r => console.log('Navigated to token page', r));
        } else {
          console.warn('Login failed. Challenge response required.');
        }
      }, error: (error: any) => {
        console.error('Login failed', error);
      }
    });
  }

  logout(): void {
    localStorage.removeItem(this.authSecretKey);
    this.authService.deauthenticate();
  }

}
