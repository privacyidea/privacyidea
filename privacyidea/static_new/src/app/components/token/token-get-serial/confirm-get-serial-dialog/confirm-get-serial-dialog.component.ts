import { Component, Inject } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-confirm-get-serial-dialog',
  imports: [
    MatDialogContent,
    MatDialogTitle,
    MatDialogActions,
    MatButton,
    MatDialogClose,
  ],
  templateUrl: './confirm-get-serial-dialog.component.html',
  styleUrl: './confirm-get-serial-dialog.component.scss',
  standalone: true,
})
export class ConfirmGetSerialDialogComponent {
  constructor(
    @Inject(MAT_DIALOG_DATA)
    public data: {
      numberOfTokens: any;
      onAbort: () => void;
      onConfirm: () => void;
    },
  ) {}
}
