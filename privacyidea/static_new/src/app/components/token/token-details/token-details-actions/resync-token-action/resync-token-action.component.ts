import { Component, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIcon } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";

@Component({
  selector: "app-resync-token-action",
  imports: [FormsModule, MatIcon, MatButtonModule],
  templateUrl: "./resync-token-action.component.html",
  styleUrl: "./resync-token-action.component.scss"
})
export class ResyncTokenActionComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  fristOTPValue: string = "";
  secondOTPValue: string = "";

  resyncOTPToken() {
    this.tokenService
      .resyncOTPToken(
        this.tokenService.tokenSerial(),
        this.fristOTPValue,
        this.secondOTPValue
      )
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
        }
      });
  }
}
