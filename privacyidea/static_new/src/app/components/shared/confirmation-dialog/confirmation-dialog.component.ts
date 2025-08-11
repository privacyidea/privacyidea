import { NgClass } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle,
} from '@angular/material/dialog';

@Component({
  selector: 'app-confirmation-dialog',
  imports: [
    MatDialogContent,
    MatDialogTitle,
    MatDialogActions,
    MatButton,
    MatDialogClose,
    NgClass,
  ],
  templateUrl: './confirmation-dialog.component.html',
  styleUrl: './confirmation-dialog.component.scss',
})
export class ConfirmationDialogComponent {
  public readonly data: ConfirmationDialogData = inject(MAT_DIALOG_DATA);
}

export type ConfirmationDialogData = {
  numberOfTokens?: string;
  type: 'token' | string;
  serial_list?: string[];
  title: string;
  action: 'remove' | 'delete' | 'revoke' | 'search' | 'unassign';
};
