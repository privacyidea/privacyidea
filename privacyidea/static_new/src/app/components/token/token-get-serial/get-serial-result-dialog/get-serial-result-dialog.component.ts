import { Component, Inject } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-get-serial-result-dialog',
  imports: [
    MatDialogContent,
    MatDialogTitle,
    MatDialogActions,
    MatButton,
    MatDialogClose,
  ],
  templateUrl: './get-serial-result-dialog.component.html',
  styleUrl: './get-serial-result-dialog.component.scss',
})
export class GetSerialResultDialogComponent {
  constructor(
    @Inject(MAT_DIALOG_DATA)
    public data: {
      foundSerial: string;
      otpValue: string;
      dialogRef: MatDialogRef<GetSerialResultDialogComponent>;
      onClickSerial: () => void;
      reset: () => void;
    },
  ) {}
}
