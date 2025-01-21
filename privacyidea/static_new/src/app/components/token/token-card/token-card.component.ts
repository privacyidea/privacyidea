import {
  Component,
  effect,
  Input,
  signal,
  Signal,
  WritableSignal,
} from '@angular/core';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIcon } from '@angular/material/icon';
import { TokenTabComponent } from './token-tab/token-tab.component';
import { ContainerTabComponent } from './container-tab/container-tab.component';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../services/overflow/overflow.service';

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
  @Input() selectedPage!: WritableSignal<string>;
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
      if (this.selectedPage() === '') {
        this.selectedPage.set('token_overview');
      }
      if (this.selectedPage().startsWith('token')) {
        this.selectedTabIndex.set(0);
      }
      if (this.selectedPage().startsWith('container')) {
        this.selectedTabIndex.set(1);
      }
    });
  }

  onTabChange(): void {
    if (this.isProgrammaticChange()) {
      this.isProgrammaticChange.set(false);
      return;
    }
    this.containerSerial.set('');
    this.tokenSerial.set('');
    switch (this.selectedTabIndex()) {
      case 0:
        this.selectedPage.set('token_overview');
        break;
      case 1:
        this.selectedPage.set('container_overview');
        break;
    }
  }

  tokenTabActive(): boolean {
    if (this.selectedPage().startsWith('token')) {
      return true;
    }
    return false;
  }

  containerTabActive(): boolean {
    if (this.selectedPage().startsWith('container')) {
      return true;
    }
    return false;
  }

  tokenIsSelected(): boolean {
    return this.tokenSerial() !== '';
  }
}
