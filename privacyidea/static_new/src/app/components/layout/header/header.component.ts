import {Component} from '@angular/core';
import {DatePipe, NgClass, NgOptimizedImage} from '@angular/common';
import {MatFabAnchor, MatFabButton} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {RouterLink} from '@angular/router';
import {SessionTimerService} from '../../../services/session-timer/session-timer.service';

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
    NgClass
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  constructor(protected sessionTimerService: SessionTimerService) {
  }

  refreshPage() {
    window.location.reload();
  }
}
