import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: "app-template-add-token-button",
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  templateUrl: "./template-add-token-button.component.html",
  styleUrls: ["./template-add-token-button.component.scss"],
})
export class TemplateAddTokenButtonComponent {
  addToken() {
    // TODO: Implement add token logic
    console.log("Add token clicked");
  }
}
