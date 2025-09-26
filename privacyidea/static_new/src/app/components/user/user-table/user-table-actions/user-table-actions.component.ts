import { Component, inject } from "@angular/core";
import { NgClass } from "@angular/common";
import { RouterLink } from "@angular/router";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-user-table-actions",
  imports: [
    MatButtonModule,
    NgClass,
    RouterLink,
    MatIcon
  ],
  templateUrl: "./user-table-actions.component.html",
  styleUrl: "./user-table-actions.component.scss"
})
export class UserTableActionsComponent {
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
}
