import {Component, effect, Input, signal, WritableSignal,} from '@angular/core';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatTabsModule} from '@angular/material/tabs';
import {MatIcon} from '@angular/material/icon';
import {TokenTabComponent} from './token-tab/token-tab.component';
import {ContainerTabComponent} from './container-tab/container-tab.component';
import {NgClass} from '@angular/common';
import {OverflowService} from '../../../services/overflow/overflow.service';

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
  @Input() selectedContent!: WritableSignal<string>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  selectedTabIndex = signal(0);

  constructor(protected overflowService: OverflowService) {
    effect(() => {
      if (this.selectedContent() === '') {
        this.selectedContent.set('token_overview');
      }
      if (this.selectedContent().startsWith('token')) {
        this.selectedTabIndex.set(0);
      }
      if (this.selectedContent().startsWith('container')) {
        this.selectedTabIndex.set(1);
      }
    });
  }

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
