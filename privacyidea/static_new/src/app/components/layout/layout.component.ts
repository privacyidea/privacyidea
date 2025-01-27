import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from './header/header.component';
import { FooterComponent } from './footer/footer.component';

@Component({
  selector: 'layout',
  templateUrl: 'layout.component.html',
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, FooterComponent],
  styleUrl: './layout.component.scss',
})
export class LayoutComponent {}
