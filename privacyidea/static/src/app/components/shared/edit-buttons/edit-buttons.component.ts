import {Component, Input, Signal} from '@angular/core';
import {MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';

@Component({
  selector: 'app-edit-buttons',
  imports: [
    MatIconButton,
    MatIcon
  ],
  templateUrl: './edit-buttons.component.html',
  styleUrl: './edit-buttons.component.css'
})
export class EditButtonsComponent {

  @Input() toggleEditMode!: (element: any, type?: string, action?: string) => void;
  @Input() isAnyEditing!: Signal<boolean>;
  @Input() element: any;
}
