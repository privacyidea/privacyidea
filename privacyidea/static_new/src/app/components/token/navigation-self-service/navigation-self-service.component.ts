import { Component, inject } from "@angular/core";
import { NavigationSelfServiceButtonComponent } from "./navigation-self-service-button/navigation-self-service-button.component";
import { ROUTE_PATHS } from "../../../app.routes";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";

@Component({
  selector: "app-navigation-self-service",
  standalone: true,
  imports: [NavigationSelfServiceButtonComponent],
  templateUrl: "./navigation-self-service.component.html",
  styleUrl: "./navigation-self-service.component.scss"
})
export class NavigationSelfServiceComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
}
