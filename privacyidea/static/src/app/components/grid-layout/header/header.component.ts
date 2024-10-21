import {Component} from '@angular/core';
import {NgOptimizedImage} from '@angular/common';
import {MatFabAnchor, MatFabButton} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {Router} from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    NgOptimizedImage,
    MatFabButton,
    MatFabAnchor,
    MatIconModule
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css'
})
export class HeaderComponent {
  constructor(private router: Router) {
  }

  refreshPage() {
    window.location.reload();
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
