import { Component, EventEmitter, Input, Output } from "@angular/core";
import { ReactiveFormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: "app-clearable-input",
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  templateUrl: "./clearable-input.component.html",
  styleUrl: "./clearable-input.component.scss"
})
export class ClearableInputComponent {
  @Output() onClick = new EventEmitter<void>();
  @Input() showClearButton: boolean = true;

  clearInput(): void {
    this.onClick.emit();
  }
}
