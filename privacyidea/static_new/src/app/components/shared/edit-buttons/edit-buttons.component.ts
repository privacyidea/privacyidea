import { Component, Input, Signal, WritableSignal } from '@angular/core';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';

export interface EditableElement<V = unknown> {
  keyMap: { key: string };
  isEditing: WritableSignal<boolean>;
  value: V;
}

@Component({
  selector: 'app-edit-buttons',
  imports: [MatIconButton, MatIcon],
  templateUrl: './edit-buttons.component.html',
  styleUrl: './edit-buttons.component.scss',
})
export class EditButtonsComponent<T extends EditableElement> {
  @Input() toggleEdit!: (element: T) => void;
  @Input() saveEdit!: (element: T) => void;
  @Input() cancelEdit!: (element: T) => void;
  @Input() shouldHideEdit!: Signal<boolean>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() element!: T;
}
