import { NgClass } from '@angular/common';
import { Component, inject, linkedSignal } from '@angular/core';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import {
  ContainerService,
  ContainerServiceInterface,
} from '../../../services/container/container.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  OverflowService,
  OverflowServiceInterface,
} from '../../../services/overflow/overflow.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';
import { ContainerTabComponent } from './container-tab/container-tab.component';
import { TokenTabComponent } from './token-tab/token-tab.component';

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
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);

  containerSerial = this.containerService.containerSerial;
  selectedContent = this.contentService.selectedContent;
  tokenSerial = this.tokenService.tokenSerial;
  states = this.containerService.states;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
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

  onTabChange(): void {
    if (this.isProgrammaticTabChange()) {
      this.isProgrammaticTabChange.set(false);
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
