import {Component} from '@angular/core';
import {MatCard, MatCardContent} from '@angular/material/card';
import {MatTabHeader, MatTabsModule} from '@angular/material/tabs';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton, MatFabButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';

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
    MatTabHeader
  ],
  templateUrl: './token-card.component.html',
  styleUrl: './token-card.component.css'
})
export class TokenCardComponent {

}
