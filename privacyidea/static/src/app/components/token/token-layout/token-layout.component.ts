import {Component, effect, signal, ViewChild} from '@angular/core';
import {TokenTableComponent} from '../token-table/token-table.component';
import {CommonModule} from '@angular/common';
import {TokenCardComponent} from '../token-card/token-card.component';
import {ContainerTableComponent} from '../container-table/container-table.component';
import {TokenDetailsComponent} from '../token-details/token-details.component';
import {ContainerDetailsComponent} from '../container-details/container-details.component';
import {MatDrawer, MatDrawerContainer, MatSidenavModule} from '@angular/material/sidenav';
import {MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import { OverflowService } from '../../../services/overflow/overflow.service';

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
    MatIconButton
  ],
  templateUrl: './token-layout.component.html',
  styleUrl: './token-layout.component.scss'
})
export class TokenLayoutComponent {
  selectedTabIndex = signal(0);
  tokenIsSelected = signal(false);
  containerIsSelected = signal(false);
  serial = signal('');
  active = signal(true);
  revoked = signal(true);
  refreshTokenDetails = signal(false);

  @ViewChild('tokenDetailsComponent') tokenDetailsComponent!: TokenDetailsComponent;
  @ViewChild('drawer') drawer!: MatDrawer;

  constructor(protected overflowService: OverflowService) {
    effect(() => {
      if (this.refreshTokenDetails()) {
        this.onRefreshTokenDetails();
      }
    });
  }

  onRefreshTokenDetails(): void {
    if (this.tokenDetailsComponent) {
      this.tokenDetailsComponent.showTokenDetail(this.serial()).subscribe({
        next: () => {
          this.refreshTokenDetails.set(false);
        },
        error: (error) => {
          console.error('Error refreshing token details:', error);
        }
      });
    } else {
      console.warn('TokenDetailsComponent is not yet initialized');
    }
  }
}
