import {Component, Input, signal, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
import {NgClass} from '@angular/common';
import {switchMap} from 'rxjs';
import {TokenService} from '../../../../services/token/token.service';
import {tabToggleState} from '../../../../../styles/animations/animations';
import {MatDialog} from '@angular/material/dialog';
import {LostTokenComponent} from './lost-token/lost-token.component';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    MatDivider,
    NgClass
  ],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.scss',
  animations: [tabToggleState]
})
export class TokenTabComponent {
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() serial!: WritableSignal<string>
  @Input() active!: WritableSignal<boolean>
  @Input() revoked!: WritableSignal<boolean>
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  isLost = signal(false);

  constructor(private tokenService: TokenService,
              private dialog: MatDialog) {
  }

  toggleActive(): void {
    this.tokenService.toggleActive(this.serial(), this.active()).pipe(
      switchMap(() => this.tokenService.getTokenDetails(this.serial()))
    ).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }

  revokeToken(): void {
    this.tokenService.revokeToken(this.serial()).pipe(
      switchMap(() => this.tokenService.getTokenDetails(this.serial()))
    ).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: error => {
        console.error('Failed to revoke token', error);
      }
    });
  }

  deleteToken(): void {
    this.tokenService.deleteToken(this.serial()).subscribe({
      next: () => {
        this.tokenIsSelected.set(false);
      },
      error: error => {
        console.error('Failed to delete token', error);
      }
    });
  }

  openLostTokenDialog() {
    this.dialog.open(LostTokenComponent, {
      data: {
        serial: this.serial,
        isLost: this.isLost,
        token_serial: this.serial,
        tokenIsSelected: this.tokenIsSelected
      }
    });
  }
}
