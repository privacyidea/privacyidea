import {Component} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatFabAnchor, MatFabButton} from '@angular/material/button';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [
    MatIconModule,
    MatFabButton,
    MatFabAnchor
  ],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.css'
})
export class FooterComponent {
}
