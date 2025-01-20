import { Component, effect, signal, ViewChild } from '@angular/core';
import { TokenTableComponent } from './token-table/token-table.component';
import { CommonModule } from '@angular/common';
import { ContainerTableComponent } from './container-table/container-table.component';
import { TokenDetailsComponent } from '../token-details/token-details.component';
import { ContainerDetailsComponent } from '../container-details/container-details.component';
import { MatDrawer, MatDrawerContainer, MatSidenavModule } from '@angular/material/sidenav';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { OverflowService } from '../../../services/overflow/overflow.service';
import { TokenCardComponent } from '../token-card/token-card.component';
import { NotificationService } from '../../../services/notification/notification.service';

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
    TokenTableComponent,
    TokenCardComponent,
    ContainerTableComponent,
    TokenDetailsComponent,
    ContainerDetailsComponent,
    MatDrawerContainer,
    MatDrawer,
    MatSidenavModule,
    MatIcon,
    MatFabButton
  ],
  templateUrl: './token-layout.component.html',
  styleUrl: './token-layout.component.scss'
})
export class TokenLayoutComponent {
  selectedPage = signal('token_overview');
  tokenSerial = signal('');
  containerSerial = signal('');
  tokenIsActive = signal(true);
  revoked = signal(true);
  refreshTokenDetails = signal(false);
  refreshContainerDetails = signal(false);
  states = signal<string[]>([]);
  isProgrammaticChange = signal(false);

  @ViewChild('tokenDetailsComponent') tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild('containerDetailsComponent') containerDetailsComponent!: ContainerDetailsComponent;
  @ViewChild('drawer') drawer!: MatDrawer;

  constructor(protected overflowService: OverflowService,
    private notificationService: NotificationService) {
    effect(() => {
      if (this.refreshTokenDetails()) {
        this.onRefreshTokenDetails();
      }
    });
    effect(() => {
      if (this.refreshContainerDetails()) {
        this.onRefreshContainerDetails();
      }
    });
  }

  onRefreshTokenDetails(): void {
    if (this.tokenDetailsComponent) {
      this.tokenDetailsComponent.showTokenDetail().subscribe({
        next: () => {
          this.refreshTokenDetails.set(false);
        },
        error: (error) => {
          console.error('Error refreshing token details.', error);
          this.notificationService.openSnackBar('Error refreshing token details.')
        }
      });
    } else {
      console.warn('TokenDetailsComponent is not yet initialized.');
      this.notificationService.openSnackBar('TokenDetailsComponent is not yet initialized.')
    }
  }

  onRefreshContainerDetails(): void {
    if (this.containerDetailsComponent) {
      this.containerDetailsComponent.showContainerDetail().subscribe({
        next: () => {
          this.refreshContainerDetails.set(false);
        },
        error: (error) => {
          console.error('Error refreshing token details.', error);
          this.notificationService.openSnackBar('Error refreshing token details.')
        }
      });
    } else {
      console.warn('ContainerDetailsComponent is not yet initialized.');
      this.notificationService.openSnackBar('ContainerDetailsComponent is not yet initialized.')
    }
  }

  tokenIsSelected(): boolean {
    return this.tokenSerial() !== '';
  }

  containerIsSelected(): boolean {
    return this.containerSerial() !== '';
  }
}
