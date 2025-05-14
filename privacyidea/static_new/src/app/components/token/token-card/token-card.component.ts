import { Component, linkedSignal } from '@angular/core';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIcon } from '@angular/material/icon';
import { TokenTabComponent } from './token-tab/token-tab.component';
import { ContainerTabComponent } from './container-tab/container-tab.component';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../services/overflow/overflow.service';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { ContentService } from '../../../services/content/content.service';

@Component({
  selector: 'app-token-card',
  standalone: true,
  imports: [
    MatCardContent,
    MatTabsModule,
    MatCard,
    MatIcon,
    TokenTabComponent,
    ContainerTabComponent,
    NgClass,
  ],
  templateUrl: './token-card.component.html',
  styleUrls: ['./token-card.component.scss'],
})
export class TokenCardComponent {
  containerSerial = this.containerService.containerSerial;
  selectedContent = this.contentService.selectedContent;
  tokenSerial = this.tokenService.tokenSerial;
  states = this.containerService.states;
  isProgrammaticChange = this.contentService.isProgrammaticTabChange;
  selectedTabIndex = linkedSignal({
    source: this.selectedContent,
    computation: (selectedContent) => {
      if (selectedContent.startsWith('container')) {
        return 1;
      } else {
        return 0;
      }
    },
  });

  constructor(
    protected overflowService: OverflowService,
    private tokenService: TokenService,
    private containerService: ContainerService,
    private contentService: ContentService,
  ) {}

  onTabChange(): void {
    if (this.isProgrammaticChange()) {
      this.isProgrammaticChange.set(false);
      return;
    }

    switch (this.selectedTabIndex()) {
      case 0:
        this.selectedContent.set('token_overview');
        break;
      case 1:
        this.selectedContent.set('container_overview');
        break;
    }

    this.containerSerial.set('');
    this.tokenSerial.set('');
  }

  tokenTabActive(): boolean {
    return this.selectedContent().startsWith('token');
  }

  containerTabActive(): boolean {
    return this.selectedContent().startsWith('container');
  }
}
