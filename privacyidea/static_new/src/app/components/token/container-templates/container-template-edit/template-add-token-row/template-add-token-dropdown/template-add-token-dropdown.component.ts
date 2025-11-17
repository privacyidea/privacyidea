import { Component, EventEmitter, Output } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-template-add-token-dropdown",
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    FormsModule,
  ],
  templateUrl: "./template-add-token-dropdown.component.html",
  styleUrls: ["./template-add-token-dropdown.component.scss"],
})
export class TemplateAddTokenDropdownComponent {
  tokenTypes: string[] = ["HOTP", "TOTP", "SMS"]; // Example token types
  selectedTokenType: string = this.tokenTypes[0];

  @Output() selectionChange = new EventEmitter<string>();

  onTokenTypeChange(tokenType: string) {
    this.selectedTokenType = tokenType;
    this.selectionChange.emit(tokenType);
  }
}
