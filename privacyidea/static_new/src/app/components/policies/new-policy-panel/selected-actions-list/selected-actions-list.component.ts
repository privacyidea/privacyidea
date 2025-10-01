
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-selected-actions-list',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './selected-actions-list.component.html',
  styleUrls: ['./selected-actions-list.component.scss']
})
export class SelectedActionsListComponent {
  @Input() actions: { actionName: string; value: string }[] = [];

  @Output() editAction = new EventEmitter<string>();
  @Output() deleteAction = new EventEmitter<string>();
}
