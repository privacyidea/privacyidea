import {Component} from '@angular/core';
import {RouterLink, RouterOutlet} from '@angular/router';
import {LoginComponent} from './components/login/login.component';
import {FormsModule} from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, LoginComponent, FormsModule, RouterLink],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'privacyidea-webui';
}
