import {Component} from '@angular/core';
import {NgOptimizedImage} from '@angular/common';
import {MatFabAnchor, MatFabButton} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {RouterLink} from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    NgOptimizedImage,
    MatFabButton,
    MatFabAnchor,
    MatIconModule,
    RouterLink
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {

  refreshPage() {
    window.location.reload();
  }
}
