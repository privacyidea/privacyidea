import { Component, EventEmitter, Output } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-template-add-token-row",
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    CommonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    FormsModule
  ],
  templateUrl: "./template-add-token-row.component.html",
  styleUrls: ["./template-add-token-row.component.scss"]
})
export class TemplateAddTokenRowComponent {
  tokenTypes: string[] = ["HOTP", "TOTP", "SMS"]; // Example token types
  selectedTokenType: string = this.tokenTypes[0];

  @Output() selectionChange = new EventEmitter<string>();

  onTokenTypeChange(tokenType: string) {
    this.selectedTokenType = tokenType;
    this.selectionChange.emit(tokenType);
  }
  addToken() {
    // TODO: Implement add token logic
    console.log("Add token clicked");
  }
}
