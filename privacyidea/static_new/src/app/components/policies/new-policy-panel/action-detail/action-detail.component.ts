import { Component, computed, EventEmitter, Input, Output, Signal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyAction } from "../../../../services/policies/policies.service";
import { BoolSelectButtonsComponent } from "../bool-select-buttons/bool-select-buttons.component";

@Component({
  selector: "app-action-detail",
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, BoolSelectButtonsComponent],
  templateUrl: "./action-detail.component.html",
  styleUrls: ["./action-detail.component.scss"]
})
export class ActionDetailComponent {
  @Input() selectedAction: PolicyAction | null = null;
  @Input() selectedActionName: string = "";

  @Output() addAction = new EventEmitter<{ actionName: string; value: string }>();

  actionValue: WritableSignal<string> = signal("");

  inputIsValid: Signal<boolean> = computed(() => {
    const action = this.selectedAction;
    const value = this.actionValue();

    if (!action) return false;
    const actionType = action.type;
    if (!actionType) return false;

    if (actionType === "bool") {
      return value.toLowerCase() === "true" || value.toLowerCase() === "false";
    } else if (actionType === "int") {
      return !isNaN(Number(value)) && Number.isInteger(Number(value));
    } else if (actionType === "str") {
      return value.trim().length > 0;
    }
    return false;
  });

  onAddAction() {
    if (!this.inputIsValid()) return;

    this.addAction.emit({ actionName: this.selectedActionName, value: this.actionValue() });
    this.actionValue.set("");
  }
}
