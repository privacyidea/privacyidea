import {
  Component,
  computed,
  EventEmitter,
  inject,
  Input,
  Output,
  Signal,
  signal,
  WritableSignal
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyAction, PolicyService } from "../../../../services/policies/policies.service";
import { BoolSelectButtonsComponent } from "../bool-select-buttons/bool-select-buttons.component";

@Component({
  selector: "app-action-detail",
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, BoolSelectButtonsComponent],
  templateUrl: "./action-detail.component.html",
  styleUrls: ["./action-detail.component.scss"]
})
export class ActionDetailComponent {
  policyService = inject(PolicyService);

  @Output() addAction = new EventEmitter<{ actionName: string; value: string }>();

  newActionValue: WritableSignal<string> = signal("");

  inputIsValid: Signal<boolean> = computed(() => {
    const action = this.policyService.selectedAction();
    const value = this.newActionValue();

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
    this.policyService.addAction({ actionName: this.policyService.selectedActionName(), value: this.newActionValue() });
    this.newActionValue.set("");
  }
}
