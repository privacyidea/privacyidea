import { Component, computed, Inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatDialog } from '@angular/material/dialog';
import { forkJoin, switchMap } from 'rxjs';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { ContentService } from '../../../../services/content/content.service';
import { TokenService } from '../../../../services/token/token.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../../services/version/version.service';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { LostTokenComponent } from './lost-token/lost-token.component';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, MatDivider, NgClass],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.scss',
  animations: [tabToggleState],
})
export class TokenTabComponent {
  /* existing reactive properties ------------------------------- */
  selectedContent = this.contentService.selectedContent;
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  tokenSerial = this.tokenService.tokenSerial;
  tokenSelection = this.tokenService.tokenSelection;
  tokenIsSelected = computed(() => this.tokenSerial() !== '');
  isLost = signal(false);
  version!: string;

  constructor(
    private router: Router,
    private tokenService: TokenService,
    private dialog: MatDialog,
    @Inject(VersioningService)
    protected versioningService: VersioningServiceInterface,
    private contentService: ContentService,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  go(path: string) {
    this.contentService.isProgrammaticTabChange.set(true);
    this.router.navigateByUrl(path);
  }

  toggleActive(): void {
    this.tokenService
      .toggleActive(this.tokenSerial(), this.tokenIsActive())
      .pipe(
        switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial())),
      )
      .subscribe(() => this.tokenService.tokenDetailResource.reload());
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
      .subscribe((ok) => {
        if (ok) {
          this.tokenService
            .revokeToken(this.tokenSerial())
            .pipe(
              switchMap(() =>
                this.tokenService.getTokenDetails(this.tokenSerial()),
              ),
            )
            .subscribe(() => this.tokenService.tokenDetailResource.reload());
        }
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
      .subscribe((ok) => {
        if (ok) {
          this.tokenService.deleteToken(this.tokenSerial()).subscribe(() => {
            this.go('/tokens');
          });
        }
      });
  }

  deleteSelectedTokens(): void {
    const ts = this.tokenSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: ts.map((t) => t.serial),
          title: 'Delete All Tokens',
          type: 'token',
          action: 'delete',
          numberOfTokens: ts.length,
        },
      })
      .afterClosed()
      .subscribe((ok) => {
        if (ok) {
          forkJoin(
            ts.map((t) => this.tokenService.deleteToken(t.serial)),
          ).subscribe(() => this.tokenService.tokenResource.reload());
        }
      });
  }

  openLostTokenDialog() {
    this.dialog.open(LostTokenComponent, {
      data: { isLost: this.isLost, tokenSerial: this.tokenSerial },
    });
  }
}
