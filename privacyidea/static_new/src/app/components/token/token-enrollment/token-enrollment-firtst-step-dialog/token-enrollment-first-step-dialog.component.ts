import { Component, inject } from "@angular/core";
import { MatButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

@Component({
  selector: "app-token-enrollment-first-step-dialog",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle
  ],
  templateUrl: "./token-enrollment-first-step-dialog.component.html",
  styleUrl: "./token-enrollment-first-step-dialog.component.scss"
})
export class TokenEnrollmentFirstStepDialogComponent {
  protected readonly dialogRef: MatDialogRef<TokenEnrollmentFirstStepDialogComponent> =
    inject(MatDialogRef);
  public readonly data: {
    enrollmentResponse: EnrollmentResponse;
  } = inject(MAT_DIALOG_DATA);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);

  protected readonly Object = Object;

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }
}
