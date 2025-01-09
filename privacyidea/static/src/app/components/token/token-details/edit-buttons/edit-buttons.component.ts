import {Component, Input, Signal, WritableSignal} from '@angular/core';
import {MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';

@Component({
  selector: 'app-edit-buttons',
  imports: [
    MatIconButton,
    MatIcon
  ],
  templateUrl: './edit-buttons.component.html',
  styleUrl: './edit-buttons.component.scss'
})
export class EditButtonsComponent {

  @Input() toggleEditMode!: (element: any, type?: string, action?: string) => void;
  @Input() shouldHideEdit!: Signal<boolean>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() element: any;
}
