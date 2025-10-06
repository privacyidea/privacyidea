import { Component, computed, EventEmitter, inject, Output, Signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { PolicyActionDetail, PolicyService } from "../../../../services/policies/policies.service";
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
  inputIsValid: Signal<boolean> = computed(() => {
    const action = this.policyService.selectedActionDetail();
    const actionValue = this.policyService.selectedAction()?.value;
    if (action === null) return false;
    return this.policyService.actionValueIsValid(action, actionValue);
  });

  @Output() addAction = new EventEmitter<{ actionName: string; value: string }>();
}
