import { Component, inject } from '@angular/core';
import { MatButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';

export type GetSerialResultDialogData = {
  foundSerial: string;
  otpValue: string;
  onClickSerial: () => void;
  reset: () => void;
};

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
  standalone: true,
})
export class GetSerialResultDialogComponent {
  public readonly dialogRef: MatDialogRef<GetSerialResultDialogComponent> =
    inject(MatDialogRef);
  public readonly data: GetSerialResultDialogData = inject(MAT_DIALOG_DATA);

  constructor() {}
}
