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
import { TokenService } from '../../../../services/token/token.service';
import { ContentService } from '../../../../services/content/content.service';
import { EnrollmentResponse } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';

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
    private contentService: ContentService,
    private dialogRef: MatDialogRef<TokenEnrollmentFirstStepDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      enrollmentResponse: EnrollmentResponse;
    },
  ) {}

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.contentService.tokenSelected(tokenSerial);
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.contentService.containerSelected(containerSerial);
  }
}
