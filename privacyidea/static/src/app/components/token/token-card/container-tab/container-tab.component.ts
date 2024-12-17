import {Component, Input, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {NgClass} from '@angular/common';
import {tabToggleState} from '../../../../../styles/animations/animations';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    NgClass
  ],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [tabToggleState]
})
export class ContainerTabComponent {
  @Input() containerIsSelected!: WritableSignal<boolean>;
}
