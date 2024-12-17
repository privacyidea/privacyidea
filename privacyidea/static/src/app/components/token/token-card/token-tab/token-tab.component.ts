import {Component, Input, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
import {NgClass} from '@angular/common';
import {switchMap} from 'rxjs';
import {TokenService} from '../../../../services/token/token.service';
import {tabToggleState} from '../../../../../styles/animations/animations';

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

  constructor(private tokenService: TokenService) {
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
}
