import { Component } from "@angular/core";
import { UserComponent } from "./user.component";
import { MatCardContent, MatCardModule } from "@angular/material/card";

@Component({
  selector: "app-user-self-service",
  imports: [MatCardModule, MatCardContent],
  templateUrl: "./user.self-service.component.html",
  styleUrl: "./user.component.scss"
})
export class UserSelfServiceComponent extends UserComponent {
  userData = this.userService.user;
}
