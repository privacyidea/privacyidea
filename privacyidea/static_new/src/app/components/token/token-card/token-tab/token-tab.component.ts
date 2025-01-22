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
import {VersionService} from '../../../../services/version/version.service';
import {NotificationService} from '../../../../services/notification/notification.service';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, MatDivider, NgClass],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.scss',
  animations: [tabToggleState],
})
export class TokenTabComponent {
  @Input() selectedPage!: WritableSignal<string>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  isLost = signal(false);

  version!: string;

  constructor(
    private tokenService: TokenService,
    private dialog: MatDialog,
    private versioningService: VersionService,
    private notificationService: NotificationService
  ) {
  }

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  toggleActive(): void {
    this.tokenService
      .toggleActive(this.tokenSerial(), this.active())
      .pipe(
        switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial()))
      )
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
          this.notificationService.openSnackBar('Failed to toggle active.');
        },
      });
  }

  revokeToken(): void {
    this.tokenService
      .revokeToken(this.tokenSerial())
      .pipe(
        switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial()))
      )
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to revoke token.', error);
          this.notificationService.openSnackBar('Failed to revoke token.');
        },
      });
  }

  deleteToken(): void {
    this.tokenService.deleteToken(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenSerial.set('');
      },
      error: (error) => {
        console.error('Failed to delete token.', error);
        this.notificationService.openSnackBar('Failed to delete token.');
      },
    });
  }

  openLostTokenDialog() {
    this.dialog.open(LostTokenComponent, {
      data: {
        isLost: this.isLost,
        tokenSerial: this.tokenSerial,
        tokenIsSelected: this.tokenIsSelected,
      },
    });
  }

  openTheDocs() {
    window.open(
      `https://privacyidea.readthedocs.io/en/v${this.version}/webui/index.html#tokens`,
      '_blank'
    );
  }

  tokenIsSelected(): boolean {
    return this.tokenSerial() !== '';
  }

  containerIsSelected(): boolean {
    return this.tokenSerial() !== '';
  }

  onClickTokenTab = () => this.onClickOverview();

  onClickOverview() {
    this.selectedPage.set('token_overview');
    this.tokenSerial.set('');
  }

  onClickGetSerial() {
    this.selectedPage.set('token_get_serial');
  }
}
