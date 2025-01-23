import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, Signal } from '@angular/core';
import { MatFabButton } from '@angular/material/button';

@Component({
  selector: 'abort-button',
  imports: [MatFabButton, CommonModule],
  templateUrl: './abort-button.component.html',
  styleUrl: './abort-button.component.scss',
})
export class AbortButton {
  @Input() isEnabled: boolean = true;
  @Output() onClick: EventEmitter<void> = new EventEmitter<void>();
}
