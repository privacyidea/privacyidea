import { Component, inject, linkedSignal } from '@angular/core';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatTabChangeEvent, MatTabsModule } from '@angular/material/tabs';
import { MatIcon } from '@angular/material/icon';

import { OverflowService } from '../../../services/overflow/overflow.service';
import { ContentService } from '../../../services/content/content.service';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';

import { TokenTabComponent } from './token-tab/token-tab.component';
import { ContainerTabComponent } from './container-tab/container-tab.component';

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
  private router = inject(Router);
  selectedContent = this.contentService.selectedContent;
  selectedTabIndex = linkedSignal({
    source: this.selectedContent,
    computation: (c) => (c.startsWith('container') ? 1 : 0),
  });
  tokenSerial = this.tokenService.tokenSerial;
  containerSerial = this.containerService.containerSerial;
  states = this.containerService.states;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;

  constructor(
    protected overflowService: OverflowService,
    private contentService: ContentService,
    private tokenService: TokenService,
    private containerService: ContainerService,
  ) {}

  onTabChange(evt: MatTabChangeEvent): void {
    if (this.isProgrammaticTabChange()) {
      this.isProgrammaticTabChange.set(false);
      return;
    }

    if (evt.index === 0) {
      this.router.navigate(['/tokens']);
    } else {
      this.router.navigate(['/tokens', 'containers']);
    }
  }

  tokenTabActive = () => this.selectedContent().startsWith('token');
  containerTabActive = () => this.selectedContent().startsWith('container');
}
