
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-action-selector',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: './action-selector.component.html',
  styleUrls: ['./action-selector.component.scss']
})
export class ActionSelectorComponent {
  @Input() policyActionGroupNames: string[] = [];
  @Input() selectedActionGroup: string = "";
  @Input() actionFilter: string = "";
  @Input() getActionNamesOfGroup: (group: string) => string[] = () => [];
  @Input() selectedActionName: string = "";

  @Output() actionFilterChange = new EventEmitter<string>();
  @Output() selectedActionGroupChange = new EventEmitter<string>();
  @Output() selectedActionNameChange = new EventEmitter<string>();
}
