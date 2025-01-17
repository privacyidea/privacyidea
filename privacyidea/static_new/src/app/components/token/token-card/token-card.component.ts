import {Component, Input, WritableSignal} from '@angular/core';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatTabsModule} from '@angular/material/tabs';
import {MatIcon} from '@angular/material/icon';
import {TokenTabComponent} from './token-tab/token-tab.component';
import {ContainerTabComponent} from './container-tab/container-tab.component';
import {NgClass} from '@angular/common';
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
  styleUrls: ['./token-card.component.scss']
})
export class TokenCardComponent {
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() containerIsSelected!: WritableSignal<boolean>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() selectedTabIndex!: WritableSignal<number>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;

  constructor(protected overflowService: OverflowService) {}

  onTabChange(): void {
    if (this.isProgrammaticChange()) {
      this.isProgrammaticChange.set(false);
      return;
    }

    this.tokenIsSelected.set(false);
    this.containerIsSelected.set(false);
  }
}
