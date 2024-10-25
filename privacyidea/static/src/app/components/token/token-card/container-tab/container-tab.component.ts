import {Component} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatTab, MatTabLabel} from '@angular/material/tabs';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatTabLabel,
    MatList,
    MatTab,
    MatListItem,
    MatButton,
    MatDivider
  ],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.css'
})
export class ContainerTabComponent {

}
