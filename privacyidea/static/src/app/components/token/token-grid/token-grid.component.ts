import {Component} from '@angular/core';
import {TokenTableComponent} from '../token-table/token-table.component';
import {CommonModule} from '@angular/common';
import {MatCard, MatCardContent, MatCardHeader} from '@angular/material/card';
import {MatGridList, MatGridTile} from '@angular/material/grid-list';
import {MatTab, MatTabGroup} from '@angular/material/tabs';
import {TokenCardComponent} from '../token-card/token-card.component';
import {ContainerTableComponent} from '../container-table/container-table.component';

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
    TokenTableComponent,
    MatCardContent,
    MatCard,
    MatGridList,
    MatGridTile,
    MatTabGroup,
    MatTab,
    MatCardHeader,
    TokenCardComponent,
    ContainerTableComponent,
  ],
  templateUrl: './token-grid.component.html',
  styleUrl: './token-grid.component.css'
})
export class TokenGridComponent {
  selectedTabIndex: number = 0;

  onTabChange(index: number): void {
    this.selectedTabIndex = index;
  }
}
