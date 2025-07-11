import { NgClass } from '@angular/common';
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AuthService } from '../../services/auth/auth.service';
import { FooterComponent } from './footer/footer.component';
import { HeaderComponent } from './header/header.component';
import { HeaderSelfServiceComponent } from './header/header.serlf-service.component';

@Component({
  selector: 'layout',
  templateUrl: 'layout.component.html',
  standalone: true,
  imports: [
    RouterOutlet,
    HeaderComponent,
    FooterComponent,
    HeaderSelfServiceComponent,
    NgClass,
  ],
  styleUrl: './layout.component.scss',
})
export class LayoutComponent {
  constructor(protected authService: AuthService) {}
}
