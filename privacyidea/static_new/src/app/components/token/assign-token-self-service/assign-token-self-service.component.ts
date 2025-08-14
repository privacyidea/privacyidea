import { Component, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../app.routes";

@Component({
  selector: "app-assign-token-self-service",
  imports: [
    MatError,
    MatFormField,
    MatFormField,
    MatLabel,
    MatInput,
    FormsModule,
    MatButton,
    MatIcon
  ],
  templateUrl: "./assign-token-self-service.component.html",
  styleUrl: "./assign-token-self-service.component.scss"
})
export class AssignTokenSelfServiceComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private router = inject(Router);
  tokenSerial = this.tokenService.tokenSerial;
  selectedToken = signal("");
  setPinValue = signal("");
  repeatPinValue = signal("");

  assignUserToToken() {
    this.tokenService
      .assignUser({
        tokenSerial: this.selectedToken(),
        username: "",
        realm: "",
        pin: this.setPinValue()
      })
      .subscribe({
        next: () => {
          this.router.navigateByUrl(
            ROUTE_PATHS.TOKENS_DETAILS + this.selectedToken()
          );
          this.tokenSerial.set(this.selectedToken());
        }
      });
  }
}
