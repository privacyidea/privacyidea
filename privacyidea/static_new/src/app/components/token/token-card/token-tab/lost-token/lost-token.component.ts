import { Component, effect, Inject, WritableSignal } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import {
  LostTokenData,
  TokenService,
} from '../../../../../services/token/token.service';
import { MatCard, MatCardContent } from '@angular/material/card';
import { NotificationService } from '../../../../../services/notification/notification.service';

@Component({
  selector: 'app-lost-token',
  imports: [
    MatDialogTitle,
    MatDialogContent,
    MatButton,
    MatDialogClose,
    MatIcon,
    MatCard,
    MatCardContent,
  ],
  templateUrl: './lost-token.component.html',
  styleUrl: './lost-token.component.scss',
})
export class LostTokenComponent {
  lostTokenData?: LostTokenData;

  constructor(
    protected tokenService: TokenService,
    private notificationService: NotificationService,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      isLost: WritableSignal<boolean>;
      tokenSerial: WritableSignal<string>;
    },
    private dialogRef: MatDialogRef<LostTokenComponent>,
  ) {
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
        this.lostTokenData = response?.result?.value;
        this.notificationService.openSnackBar(
          'Token marked as lost: ' + this.data.tokenSerial(),
        );
      },
    });
  }

  tokenSelected(tokenSerial?: string) {
    if (!tokenSerial) {
      this.notificationService.openSnackBar(
        'No token selected, please select a token.',
      );
      return;
    }
    this.dialogRef.close();
    this.data.tokenSerial.set(tokenSerial);
  }
}
