import {Component, effect, Inject, WritableSignal} from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from '@angular/material/dialog';
import {MatButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {TokenService} from '../../../../../services/token/token.service';
import {MatCard, MatCardContent} from '@angular/material/card';

@Component({
  selector: 'app-lost-token',
  imports: [
    MatDialogTitle,
    MatDialogContent,
    MatButton,
    MatDialogClose,
    MatIcon,
    MatCard,
    MatCardContent
  ],
  templateUrl: './lost-token.component.html',
  styleUrl: './lost-token.component.scss'
})
export class LostTokenComponent {
  response: any;

  constructor(protected tokenService: TokenService,
              @Inject(MAT_DIALOG_DATA) public data: {
                isLost: WritableSignal<boolean>,
                tokenSerial: WritableSignal<string>,
                tokenIsSelected: WritableSignal<boolean>
              },
              private dialogRef: MatDialogRef<LostTokenComponent>) {
    effect(() => {
      this.dialogRef.disableClose = this.data.isLost();
    });

    this.dialogRef.afterClosed().subscribe(() => {
      this.data.isLost.set(false);
    });
  }

  lostToken(): void {
    this.tokenService.lostToken(this.data.tokenSerial()).subscribe({
      next: (response) => {
        this.data.isLost.set(true);
        this.response = response;
        console.log('Token marked as lost: ', this.data.tokenSerial());
      },
      error: error => {
        console.error('Failed to mark token as lost.', error);
      }
    });
  }

  tokenSelected(tokenSerial: string) {
    this.dialogRef.close();
    this.data.tokenSerial.set(tokenSerial);
    this.data.tokenIsSelected.set(true)
  }
}
