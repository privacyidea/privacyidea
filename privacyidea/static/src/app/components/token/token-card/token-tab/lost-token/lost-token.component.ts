import {Component, Inject, WritableSignal} from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle
} from '@angular/material/dialog';
import {MatButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {TokenService} from '../../../../../services/token/token.service';

@Component({
  selector: 'app-lost-token',
  imports: [
    MatDialogTitle,
    MatDialogContent,
    MatButton,
    MatDialogClose,
    MatIcon
  ],
  templateUrl: './lost-token.component.html',
  styleUrl: './lost-token.component.scss'
})
export class LostTokenComponent {
  constructor(protected tokenService: TokenService,
              @Inject(MAT_DIALOG_DATA) public data: { serial: WritableSignal<string> }) {
  }

  lostToken(): void {
    this.tokenService.lostToken(this.data.serial()).subscribe({
      next: () => {
        console.log('TODO: lost token needs to be fixed in the backend. #4196');
      },
      error: error => {
        console.error('Failed to mark token as lost.', error);
      }
    });
  }
}
