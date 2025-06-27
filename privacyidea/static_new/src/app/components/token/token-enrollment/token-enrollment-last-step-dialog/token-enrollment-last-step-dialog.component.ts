import { Component, Inject } from '@angular/core';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatIcon } from '@angular/material/icon';
import { TokenService } from '../../../../services/token/token.service';
import { ContentService } from '../../../../services/content/content.service';
import { UserData } from '../../../../services/user/user.service';
import { EnrollmentResponse } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';

export type TokenEnrollmentLastStepDialogData = {
  response: EnrollmentResponse;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: 'app-token-enrollment-second-step-dialog',
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
    MatIconButton,
  ],
  templateUrl: './token-enrollment-last-step-dialog.component.html',
  styleUrl: './token-enrollment-last-step-dialog.component.scss',
})
export class TokenEnrollmentLastStepDialogComponent {
  protected readonly Object = Object;

  constructor(
    protected tokenService: TokenService,
    private contentService: ContentService,
    private dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: TokenEnrollmentLastStepDialogData,
  ) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }

  regenerateQRCode() {
    this.data.enrollToken();
    this.dialogRef.close();
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }

  printOtps(): void {
    const printContents = document.getElementById('otp-values')?.innerHTML;
    if (printContents) {
      const printWindow = window.open('', '_blank', 'width=800,height=600');
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
