import {Component} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatTab, MatTabLabel} from '@angular/material/tabs';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatTab,
    MatList,
    MatListItem,
    MatTabLabel,
    MatButton,
    MatDivider
  ],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.css'
})
export class TokenTabComponent {

}
