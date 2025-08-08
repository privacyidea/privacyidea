import { Component, effect, inject, WritableSignal } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatCard, MatCardContent } from '@angular/material/card';
import {
  MAT_DIALOG_DATA,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatIcon } from '@angular/material/icon';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../../../../../services/notification/notification.service';
import {
  LostTokenData,
  TokenService,
  TokenServiceInterface,
} from '../../../../../services/token/token.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-lost-token',
  standalone: true,
  imports: [
    MatDialogTitle,
    MatDialogContent,
    MatButton,
    MatDialogClose,
    MatIcon,
    MatCard,
    MatCardContent,
    DatePipe,
  ],
  templateUrl: './lost-token.component.html',
  styleUrl: './lost-token.component.scss',
})
export class LostTokenComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  public readonly data: {
    isLost: WritableSignal<boolean>;
    tokenSerial: WritableSignal<string>;
  } = inject(MAT_DIALOG_DATA);

  lostTokenData?: LostTokenData;

  constructor(private dialogRef: MatDialogRef<LostTokenComponent>) {
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
