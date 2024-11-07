import {Component, EventEmitter, Input, Output, WritableSignal} from '@angular/core';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatTabChangeEvent, MatTabHeader, MatTabsModule} from '@angular/material/tabs';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton, MatFabButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
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
    MatList,
    MatListItem,
    MatFabButton,
    MatButton,
    MatDivider,
    MatTabHeader,
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
  @Output() tabChange: EventEmitter<number> = new EventEmitter<number>();

  onTabChange(event: MatTabChangeEvent): void {
    this.selectedTabIndex = event.index;
    this.tokenIsSelected.set(false);
    this.containerIsSelected.set(false);
    this.tabChange.emit(this.selectedTabIndex);
  }
}
