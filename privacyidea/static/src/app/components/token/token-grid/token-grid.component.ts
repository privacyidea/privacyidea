import {Component, effect, signal, ViewChild, WritableSignal} from '@angular/core';
import {TokenTableComponent} from '../token-table/token-table.component';
import {CommonModule} from '@angular/common';
import {MatGridList, MatGridTile} from '@angular/material/grid-list';
import {TokenCardComponent} from '../token-card/token-card.component';
import {ContainerTableComponent} from '../container-table/container-table.component';
import {TokenDetailsComponent} from '../token-details/token-details.component';
import {ContainerDetailsComponent} from '../container-details/container-details.component';

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
    TokenTableComponent,
    MatGridList,
    MatGridTile,
    TokenCardComponent,
    ContainerTableComponent,
    TokenDetailsComponent,
    ContainerDetailsComponent,
  ],
  templateUrl: './token-grid.component.html',
  styleUrl: './token-grid.component.css'
})
export class TokenGridComponent {
  selectedTabIndex = signal(0);
  tokenIsSelected = signal(false);
  containerIsSelected = signal(false);
  serial = signal('');
  active = signal(true);
  revoked = signal(true);
  refreshTokenDetails = signal(false);
  @ViewChild('tokenDetailsComponent') tokenDetailsComponent!: TokenDetailsComponent;

  constructor() {
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
