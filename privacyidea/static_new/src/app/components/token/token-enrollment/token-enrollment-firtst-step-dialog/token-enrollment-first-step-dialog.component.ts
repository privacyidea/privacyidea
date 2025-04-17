import { Component, Inject } from '@angular/core';
import { MatButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { LostTokenComponent } from '../../token-card/token-tab/lost-token/lost-token.component';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-token-enrollment-first-step-dialog',
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
  ],
  templateUrl: './token-enrollment-first-step-dialog.component.html',
  styleUrl: './token-enrollment-first-step-dialog.component.scss',
})
export class TokenEnrollmentFirstStepDialogComponent {
  protected readonly Object = Object;

  constructor(
    protected tokenService: TokenService,
    private dialogRef: MatDialogRef<LostTokenComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      response: any;
    },
  ) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.tokenService.stopPolling();
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.tokenService.tokenSelected(tokenSerial);
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.tokenService.containerSelected(containerSerial);
  }
}
