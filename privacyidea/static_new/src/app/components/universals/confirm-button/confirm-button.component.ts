import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, Signal } from '@angular/core';
import { MatFabButton } from '@angular/material/button';

@Component({
  selector: 'confirm-button',
  imports: [MatFabButton, CommonModule],
  templateUrl: './confirm-button.component.html',
  styleUrl: './confirm-button.component.scss',
})
export class ConfirmButton {
  @Input() isEnabled: boolean = true;
  @Input() text!: string;
  @Output() onClick: EventEmitter<void> = new EventEmitter<void>();
}
