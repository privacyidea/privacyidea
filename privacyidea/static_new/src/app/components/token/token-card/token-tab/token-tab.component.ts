import {
  Component,
  computed,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { NgClass } from '@angular/common';
import { switchMap } from 'rxjs';
import { TokenService } from '../../../../services/token/token.service';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { MatDialog } from '@angular/material/dialog';
import { LostTokenComponent } from './lost-token/lost-token.component';
import { VersionService } from '../../../../services/version/version.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { ConfirmationDialogComponent } from '../../confirmation-dialog/confirmation-dialog.component';
import { TokenSelectedContent } from '../../token.component';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, MatDivider, NgClass],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.scss',
  animations: [tabToggleState],
})
export class TokenTabComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  tokenIsSelected = computed(() => this.tokenSerial() !== '');
  isLost = signal(false);
  version!: string;

  constructor(
    private tokenService: TokenService,
    private dialog: MatDialog,
    protected versioningService: VersionService,
    private notificationService: NotificationService,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  toggleActive(): void {
    this.tokenService
      .toggleActive(this.tokenSerial(), this.active())
      .pipe(
        switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial())),
      )
      .subscribe({
        next: () => {
          this.refreshTokenDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to toggle active. ' + message,
          );
        },
      });
  }

  revokeToken(): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [this.tokenSerial()],
          title: 'Revoke Token',
          type: 'token',
          action: 'revoke',
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService
              .revokeToken(this.tokenSerial())
              .pipe(
                switchMap(() =>
                  this.tokenService.getTokenDetails(this.tokenSerial()),
                ),
              )
              .subscribe({
                next: () => {
                  this.refreshTokenDetails.set(true);
                },
                error: (error) => {
                  console.error('Failed to revoke token.', error);
                  const message = error.error?.result?.error?.message || '';
                  this.notificationService.openSnackBar(
                    'Failed to revoke token. ' + message,
                  );
                },
              });
          }
        },
      });
  }

  deleteToken(): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [this.tokenSerial()],
          title: 'Delete Token',
          type: 'token',
          action: 'delete',
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(this.tokenSerial()).subscribe({
              next: () => {
                this.selectedContent.set('token_overview');
                this.tokenSerial.set('');
              },
              error: (error) => {
                console.error('Failed to delete token.', error);
                const message = error.error?.result?.error?.message || '';
                this.notificationService.openSnackBar(
                  'Failed to delete token. ' + message,
                );
              },
            });
          }
        },
      });
  }

  openLostTokenDialog() {
    this.dialog.open(LostTokenComponent, {
      data: {
        isLost: this.isLost,
        tokenSerial: this.tokenSerial,
      },
    });
  }

  onClickOverview() {
    this.selectedContent.set('token_overview');
    this.tokenSerial.set('');
  }

  onClickEnrollment() {
    this.selectedContent.set('token_enrollment');
    this.tokenSerial.set('');
  }

  onClickShowChallenges() {
    this.selectedContent.set('token_challenges');
    this.tokenSerial.set('');
  }

  onClickTokenApplications() {
    this.selectedContent.set('token_applications');
    this.tokenSerial.set('');
  }

  onClickGetSerial() {
    this.selectedContent.set('token_get_serial');
    this.tokenSerial.set('');
  }
}
