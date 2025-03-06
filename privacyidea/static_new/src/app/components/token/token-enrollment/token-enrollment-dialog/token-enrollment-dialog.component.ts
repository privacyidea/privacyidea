import { Component, Inject, Input, WritableSignal } from '@angular/core';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { LostTokenComponent } from '../../token-card/token-tab/lost-token/lost-token.component';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatIcon } from '@angular/material/icon';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-token-enrollment-dialog',
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
  templateUrl: './token-enrollment-dialog.component.html',
  styleUrl: './token-enrollment-dialog.component.scss',
})
export class TokenEnrollmentDialogComponent {
  @Input() regenerateToken!: WritableSignal<boolean>;
  protected readonly Object = Object;

  constructor(
    protected tokenService: TokenService,
    private dialogRef: MatDialogRef<LostTokenComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      response: any;
      tokenSerial: WritableSignal<string>;
      containerSerial: WritableSignal<string>;
      selectedContent: WritableSignal<string>;
      regenerateToken: WritableSignal<boolean>;
      isProgrammaticChange: WritableSignal<boolean>;
      pushEnrolled: WritableSignal<boolean>;
      username: string;
      userRealm: string;
      onlyAddToRealm: WritableSignal<boolean>;
    },
  ) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.data.selectedContent.set('token_details');
    this.data.tokenSerial.set(tokenSerial);
  }

  regenerateQRCode() {
    this.data.regenerateToken.set(true);
    this.dialogRef.close();
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.data.selectedContent.set('container_details');
    this.data.isProgrammaticChange.set(true);
    this.data.containerSerial.set(containerSerial);
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
