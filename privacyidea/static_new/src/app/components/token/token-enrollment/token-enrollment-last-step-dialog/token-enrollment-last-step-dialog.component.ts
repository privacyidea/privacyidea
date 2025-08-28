import { Component, inject, WritableSignal } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";

export type TokenEnrollmentLastStepDialogData = {
  response: EnrollmentResponse;
  serial: WritableSignal<string | null>;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: "app-token-enrollment-last-step-dialog",
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton
  ],
  templateUrl: "./token-enrollment-last-step-dialog.component.html",
  styleUrl: "./token-enrollment-last-step-dialog.component.scss"
})
export class TokenEnrollmentLastStepDialogComponent {
  protected readonly dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent> = inject(MatDialogRef);
  public readonly data: TokenEnrollmentLastStepDialogData = inject(MAT_DIALOG_DATA);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  protected readonly Object = Object;

  constructor() {
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }

  regenerateQRCode() {
    this.data.serial.set(this.data.response.detail?.serial ?? null);
    this.data.enrollToken();
    this.data.serial.set(null);
    this.dialogRef.close();
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }

  printOtps(): void {
    const printContents = document.getElementById("otp-values")?.innerHTML;
    if (printContents) {
      const printWindow = window.open("", "_blank", "width=800,height=600");
      if (printWindow) {
        printWindow.document.open();
        printWindow.document.write(`
          <html lang="en">
              <style>
                .otp-values {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 8px;
                }
                .otp-value {
                  min-width: 6rem;
                  border: 1px solid #e2e2e2;
                  padding: 6px;
                  border-radius: 6px;
                }
              </style>
              ${printContents}
          </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        printWindow.close();
      }
    }
  }
}
