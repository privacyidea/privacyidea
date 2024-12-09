import {Component, Input, signal, WritableSignal} from '@angular/core';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatTabChangeEvent, MatTabsModule} from '@angular/material/tabs';
import {MatIcon} from '@angular/material/icon';
import {TokenTabComponent} from './token-tab/token-tab.component';
import {ContainerTabComponent} from './container-tab/container-tab.component';
import {NgClass} from '@angular/common';

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
  styleUrls: ['./token-card.component.css']
})
export class TokenCardComponent {
  @Input() selectedTabIndex: number = 0;
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() containerIsSelected!: WritableSignal<boolean>;
  @Input() serial!: WritableSignal<string>;
  @Input() active!: WritableSignal<boolean>;
  @Input() revoked!: WritableSignal<boolean>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  tabChange = signal<number>(0);

  onTabChange(event: MatTabChangeEvent): void {
    this.selectedTabIndex = event.index;
    this.tokenIsSelected.set(false);
    this.containerIsSelected.set(false);
    this.tabChange.set(this.selectedTabIndex);
  }
}
