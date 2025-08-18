import { Component } from "@angular/core";
import { TokenComponent } from "./token.component";
import { MatCardModule } from "@angular/material/card";
import { componentFadeAnimation } from "../../../styles/animations/animations";
import { NavigationSelfServiceComponent } from "./navigation-self-service/navigation-self-service.component";
import { RouterOutlet } from "@angular/router";

@Component({
  selector: "app-token-self-service",
  imports: [MatCardModule, NavigationSelfServiceComponent, RouterOutlet],
  animations: [componentFadeAnimation],
  templateUrl: "./token.self-service.component.html",
  styleUrl: "./token.component.scss"
})
export class TokenSelfServiceComponent extends TokenComponent {
}
