import { Component, computed, inject, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatDialog } from '@angular/material/dialog';
import { forkJoin, switchMap } from 'rxjs';
import { tabToggleState } from '../../../../../styles/animations/animations';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../../services/content/content.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../../services/version/version.service';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { LostTokenComponent } from './lost-token/lost-token.component';
import { Router, RouterLink } from '@angular/router';
import { AuditService } from '../../../../services/audit/audit.service';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    MatDivider,
    NgClass,
    RouterLink,
  ],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.scss',
  animations: [tabToggleState],
})
export class TokenTabComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  private readonly dialog: MatDialog = inject(MatDialog);
  private router = inject(Router);
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  tokenSerial = this.tokenService.tokenSerial;
  tokenSelection = this.tokenService.tokenSelection;
  tokenIsSelected = computed(() => this.tokenSerial() !== '');
  isLost = signal(false);
  version!: string;
  protected auditService = inject(AuditService);

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  toggleActive(): void {
    this.tokenService
      .toggleActive(this.tokenSerial(), this.tokenIsActive())
      .pipe(
        switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial())),
      )
      .subscribe({
        next: () => {
          this.tokenService.tokenDetailResource.reload();
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
          numberOfTokens: 1,
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
                  this.tokenService.tokenDetailResource.reload();
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
          numberOfTokens: 1,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(this.tokenSerial()).subscribe({
              next: () => {
                this.router.navigateByUrl('/tokens');
                this.tokenSerial.set('');
              },
            });
          }
        },
      });
  }

  deleteSelectedTokens(): void {
    const selectedTokens = this.tokenSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: selectedTokens.map((token) => token.serial),
          title: 'Delete All Tokens',
          type: 'token',
          action: 'delete',
          numberOfTokens: selectedTokens.length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            forkJoin(
              selectedTokens.map((token) =>
                this.tokenService.deleteToken(token.serial),
              ),
            ).subscribe({
              next: () => {
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                console.error('Error deleting tokens:', err);
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
}
